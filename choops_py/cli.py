"""Argparse entry point for texture, roster and JB-copy workflows."""
import argparse
import json
import sys
from pathlib import Path
from .commands import COMMANDS,SPECS
from .archive.manifests import safe_output,build_destination,write_bytes
from .core.errors import ToolError
from .core.reports import save_json

def parser():
    p=argparse.ArgumentParser(description='PS3 College Hoops 2K8 texture/roster modding; build a separate JB copy')
    sub=p.add_subparsers(dest='command',required=True);sub.add_parser('gui')
    for name,spec in COMMANDS.items():
        s=sub.add_parser(name)
        for field in spec.fields:s.add_argument(field)
        for group in spec.options:
            if group=='recruit-pool':
                dependency=s.add_mutually_exclusive_group()
                dependency.add_argument('--interest-nodes')
                dependency.add_argument('--recruiting-state')
                s.add_argument('--free-head',type=lambda value:int(value,0))
            elif group=='motion-events':
                s.add_argument('--native-elf',action='store_true')
                s.add_argument('--auxiliary-start')
                s.add_argument('--payload-consumers',action='store_true')
            elif group=='motion-sampler':
                s.add_argument('--cache-bytes',type=int,default=256*1024)
            elif group=='related-banks':
                s.add_argument('--related-bank',action='append',default=[])
            elif group=='motion-extents':
                s.add_argument('--motion-extents',action='store_true')
            elif group=='motion-root':
                s.add_argument('--root-track');s.add_argument('--root-output')
                s.add_argument('--root-without-heading',action='store_true')
            elif group=='audio-category':
                s.add_argument('--category',choices=['soundtrack','fight-songs','all'],default='soundtrack')
            elif group=='selection':
                s.add_argument('--index',type=int);s.add_argument('--file')
            elif group=='export':
                s.add_argument('--raw',action='store_true');s.add_argument('--dds',action='store_true');s.add_argument('--gtf2dds');s.add_argument('--strict',action='store_true')
            elif group=='import-format':s.add_argument('--same-format-only',action='store_true',required=True);s.add_argument('--dds2gtf')
            elif group=='import-size':s.add_argument('--same-size-only',action='store_true',required=True);s.add_argument('--dds2gtf')
            elif group=='converter-config':s.add_argument('--gtf2dds');s.add_argument('--dds2gtf')
            elif group=='copy-tools':s.add_argument('--copy-from-old-sources',action='store_true',required=True)
            elif group=='staging':s.add_argument('--iff',required=True);s.add_argument('--sub')
            elif group=='build':s.add_argument('--overwrite',action='store_true');s.add_argument('--dry-run',action='store_true')
            elif group=='safe-roster':s.add_argument('--safe-only',action='store_true',required=True)
            elif group=='compare':s.add_argument('--compare',action='store_true')
            elif group=='inspect-iff':s.add_argument('--dump-subfiles',action='store_true')
            elif group=='rip':
                flags=s.add_mutually_exclusive_group();flags.add_argument('--cache',action='store_true');flags.add_argument('--build-cache',action='store_true')
                s.add_argument('--index',type=int);s.add_argument('--file');s.add_argument('--iff-only',action='store_true');s.add_argument('--raw-iff',action='store_true');s.add_argument('--type',nargs='+',default=[]);s.add_argument('--log-output');s.add_argument('--strict',action='store_true')
        if name in ('rip','build-cache'):s.add_argument('--game-name',choices=['choops2k8'],default='choops2k8')
    return p

def execute(a):
    c=a.command
    if c=='gui':
        from .studio import main as launch
        return launch([])
    sources=[getattr(a,key) for key in ('source','input','cdf','dds_file','wav_file','image','mod','modded','edited','patch','timing','root_track','contract','target_elf','interest_nodes','recruiting_state') if getattr(a,key,None)]
    sources.extend(getattr(a,'related_bank',[]))
    if hasattr(a,'output'):
        validator=build_destination if c=='build-copy' else safe_output
        a.output=validator(a.output,sources)
    if c == 'inspect-recruit-pool':
        from .research.recruit_pool import MAX_INPUT, INTEREST_CAPACITY, INTEREST_STRIDE, RECRUITING_STATE_SIZE, inspect_recruit_pool, inspect_interest_graph, inspect_recruiting_section
        from .roster.adapters import load_bytes
        if a.free_head is not None and not a.interest_nodes:
            raise ValueError('free-head requires a separately identified interest-nodes block')
        if Path(a.input).stat().st_size > MAX_INPUT:
            raise ValueError('Recruit roster input exceeds inspection bounds')
        source = load_bytes(Path(a.input).read_bytes())
        report = inspect_recruit_pool(source.payload)
        report['source_kind'] = source.kind
        if a.interest_nodes:
            node_path = Path(a.interest_nodes)
            if node_path.stat().st_size != INTEREST_CAPACITY * INTEREST_STRIDE:
                raise ValueError('Interest block must contain exactly 16000 eight-byte nodes')
            report['interest_graph'] = inspect_interest_graph(
                node_path.read_bytes(),
                {row['slot']:row['interest_head'] for row in report['records'] if row['recruiting_filter_bit_2']},
                school_count=report['school_count'],free_head=a.free_head)
        elif a.recruiting_state:
            state_path = Path(a.recruiting_state)
            if state_path.stat().st_size != RECRUITING_STATE_SIZE:
                raise ValueError('Recruiting state must be exactly 0x415A4 bytes')
            report['recruiting_state'] = inspect_recruiting_section(state_path.read_bytes(),source.payload)
        save_json(a.output,report,sources)
        return report
    if c in ('export-uniform-models','modern-fit-uniforms','import-uniform-models',
             'export-uniform-iff','import-uniform-iff'):
        from .modding import uniform_mesh
        if c == 'export-uniform-iff':return uniform_mesh.export_iff(a.input,a.output)
        if c == 'import-uniform-iff':return uniform_mesh.import_iff(a.input,a.edited,a.output)
        if c == 'import-uniform-models':return uniform_mesh.import_folder(a.edited,a.output)
        from .archive.usrdir_reader import Archive
        return uniform_mesh.export_archive(Archive(a.source),a.output,modern=c=='modern-fit-uniforms')
    if c == 'inspect-donor-registry':
        from .research.donor_registry import MAX_BANK_BYTES, inspect_banks
        paths=[Path(a.input),*(Path(p) for p in a.related_bank)]
        if len(paths)>32 or sum(p.stat().st_size for p in paths)>MAX_BANK_BYTES:
            raise ValueError('Donor signature banks exceed inspection bounds')
        report=inspect_banks([(p.name,p.read_bytes()) for p in paths],a.profile)
        save_json(a.output,report,sources)
        return report
    if c == 'sample-native-motion':
        from .research.motion_sampling import MotionSampler
        with MotionSampler(a.input,a.target_elf,cache_bytes=a.cache_bytes) as sampler:
            pose, report = sampler.sample(int(a.address,0),float(a.seconds))
            report.update(packed_pose_hex=pose.hex(),memory=sampler.stats())
        save_json(a.output,report,sources)
        return report
    if c in ('inspect-motion-bind','inspect-shot-registration'):
        from .formats.embedded_motion import MAX_ELF
        for source in sources:
            if Path(source).stat().st_size > MAX_ELF:
                raise ValueError('Native analysis ELF exceeds inspection bounds')
        raw = Path(a.input).read_bytes()
        if c == 'inspect-motion-bind':
            from .formats.motion_bind import verify_canonical_bind
            report = verify_canonical_bind(raw,Path(a.target_elf).read_bytes())
        else:
            from .research.shot_registration import inspect_registration
            report = inspect_registration(raw,motion_extents=a.motion_extents)
        save_json(a.output,report,sources)
        return report
    if c in ('inspect-motion-events','transcode-motion-events'):
        from .formats.motion_events import MAX_INPUT, inspect_events, inspect_auxiliary_pairs, transcode_events
        if Path(a.input).stat().st_size > MAX_INPUT:
            raise ValueError('Motion event input exceeds inspection bounds')
        raw = Path(a.input).read_bytes()
        report = inspect_events(raw,a.profile,int(a.address,0),native=a.native_elf)
        if a.payload_consumers:
            if c != 'inspect-motion-events' or a.profile != 'nba-2k11':
                raise ValueError('Payload consumers require NBA 2K11 event inspection')
            from .formats.motion_events import inspect_payload_consumers
            for row in report['entries']:
                if row['payload'] is not None:
                    row['consumed_fields'] = inspect_payload_consumers(raw,row['id'],row['payload'],native=a.native_elf)
        if a.auxiliary_start is not None:
            if c != 'inspect-motion-events' or a.profile != 'nba-2k11':
                raise ValueError('Auxiliary pair inspection requires NBA 2K11 inspection')
            report['auxiliary_pairs'] = inspect_auxiliary_pairs(raw,int(a.auxiliary_start,0),native=a.native_elf)
        if c == 'inspect-motion-events':
            save_json(a.output,report,sources)
            return report
        if Path(a.contract).stat().st_size > 4*1024*1024:
            raise ValueError('Event mapping contract exceeds inspection bounds')
        data,result = transcode_events(report,json.loads(Path(a.contract).read_text(encoding='utf-8')))
        write_bytes(a.output,data,sources)
        return dict(output=str(a.output),bytes=len(data),**result)
    if c == 'resample-motion-frames':
        from .formats.motion_frames import MAX_STREAM, resample_nba11_frames, resample_nba11_root
        if Path(a.input).stat().st_size > MAX_STREAM or Path(a.timing).stat().st_size > 32767:
            raise ValueError('Motion input exceeds resampling bounds')
        data, result = resample_nba11_frames(Path(a.input).read_bytes(),
                    Path(a.timing).read_bytes(), int(a.rotations), int(a.translations))
        root_data = None
        if bool(a.root_track) != bool(a.root_output):
            raise ValueError('Provide both root-track and root-output')
        if a.root_track:
            root_output = safe_output(a.root_output, sources)
            if root_output == a.output:
                raise ValueError('Pose and root outputs must be different files')
            if Path(a.root_track).stat().st_size > MAX_STREAM:
                raise ValueError('Root track exceeds resampling bounds')
            root_data = resample_nba11_root(Path(a.root_track).read_bytes(),
                        Path(a.timing).read_bytes(), has_heading=not a.root_without_heading)
        elif a.root_without_heading:
            raise ValueError('Root heading mode requires a root track')
        if root_data is not None:
            write_bytes(root_output, root_data, sources)
            result.update(root_converted=True, root_output=str(root_output))
        write_bytes(a.output, data, sources)
        return dict(output=str(a.output), bytes=len(data), **result)
    if c == 'transcode-motion-frames':
        from .formats.motion_frames import MAX_STREAM, layout, transcode_frames
        rotations, translations, frames = map(int, (a.rotations, a.translations, a.frames))
        stride, size = layout(rotations, translations, frames)
        if Path(a.input).stat().st_size > MAX_STREAM:
            raise ValueError('Packed frame stream exceeds conversion bounds')
        data = transcode_frames(Path(a.input).read_bytes(), rotations, translations,
                                frames, a.profile, a.target_profile)
        write_bytes(a.output, data, sources)
        return dict(output=str(a.output), bytes=size, frame_stride=stride,
                    frames=frames, rotations=rotations, translations=translations,
                    source_profile=a.profile, target_profile=a.target_profile,
                    scope='packed-pose-channels-only', bone_retargeted=False,
                    gameplay_ready=False)
    if c == 'inspect-scorebug-runtime':
        from .formats.embedded_motion import MAX_ELF
        from .research.scorebug_runtime import inspect_runtime
        if Path(a.input).stat().st_size > MAX_ELF:
            raise ValueError('Native analysis ELF exceeds inspection bounds')
        result = inspect_runtime(Path(a.input).read_bytes())
        save_json(a.output, result, [a.input])
        return result
    if c == 'inspect-embedded-motion':
        from .formats.embedded_motion import inspect_embedded
        result = inspect_embedded(Path(a.input).read_bytes(), a.profile)
        save_json(a.output, result, [a.input])
        return result
    if c == 'inspect-animation-links':
        from .formats.motion_envelope import inspect_links
        result = inspect_links(Path(a.input).read_bytes(), a.profile)
        save_json(a.output, result, [a.input])
        return result
    if c in ('inspect-animations', 'export-animations'):
        from .formats.animations import inspect_animations
        raw = Path(a.input).read_bytes()
        result = inspect_animations(raw)
        if c == 'export-animations':
            from .formats.standard_iff import StandardIFF
            result['files'] = StandardIFF(raw).dump(a.output, types=('SingleMoCap',))
        save_json(a.output/'animations.json', result, sources)
        return result
    if c in ('audio-catalog','export-soundtrack','replace-song','import-audio-folder','export-audo','replace-audo','export-jukebox-art','replace-jukebox-art'):
        from .audio_tools import workflow as audio
        if c=='export-audo':return audio.export_audo(a.input,a.output)
        if c=='replace-audo':return audio.replace_audo(a.input,a.wav_file,a.output)
        from .archive.usrdir_reader import Archive
        archive=Archive(a.source)
        if c=='export-jukebox-art':return audio.export_cover(archive,a.record,a.output)
        if c=='replace-jukebox-art':return audio.replace_cover(archive,a.record,a.image,a.output)
        if c=='import-audio-folder':return audio.import_wav_folder(archive,a.input,a.output)
        catalog=audio.catalog(archive)
        if c=='audio-catalog':save_json(a.output,catalog,sources);return catalog
        if c=='export-soundtrack':
            category={'soundtrack':'Soundtrack','fight-songs':'Fight song'}.get(a.category)
            rows=[r for r in catalog['tracks'] if category is None or r['category']==category]
            return audio.export_tracks(archive,rows,a.output)
        rows=[r for r in catalog['tracks'] if r['bank']==a.bank and r['index']==int(a.index)]
        if len(rows)!=1:raise ValueError('Audio stream target is missing or ambiguous')
        return audio.replace_tracks(archive,[(rows[0],a.wav_file)],a.output)
    if c=='prepare-court-template':
        from .modding.court_template import prepare
        return prepare(a.input,a.output)
    if c in ('export-mod-patch','import-mod-patch'):
        from .modding.patch_package import export_patch,import_patch
        return export_patch(Path(a.source),Path(a.mod),Path(a.output)) if c=='export-mod-patch' else import_patch(Path(a.source),Path(a.input),Path(a.output))
    if c=='extract-raw':
        from .studio.services import extract
        from .archive.usrdir_reader import Archive
        archive=Archive(a.source);entries=archive.entries
        if a.index is not None:entries=[e for e in entries if e['index']==a.index]
        if a.file:entries=[e for e in entries if e['name'] and e['name'].casefold()==a.file.casefold()]
        return extract(archive,entries,a.output)
    if c=='stage-folder':
        from .studio.services import stage_folder
        return stage_folder(Path(a.source),Path(a.input),Path(a.output))
    if c in ('texture-tools-status','setup-texture-tools','test-texture-tools','configure-texture-tools'):
        from .texture_tools import external_converters as t
        return t.status() if c=='texture-tools-status' else t.setup() if c=='setup-texture-tools' else t.test_tools() if c=='test-texture-tools' else t.configure(a.gtf2dds,a.dds2gtf)
    if c in ('build-cache','cache-info'):
        from .archive import cache
        return str(cache.build(a.source)) if c=='build-cache' else cache.info(a.source)
    if c=='resolve-name':
        from .archive.hash_names import resolve
        return resolve(a.value)
    if c=='rip':
        from .archive import cache
        from .archive.ripper import rip
        if a.build_cache:cache.build(a.source)
        if a.cache:cache.info(a.source)
        return rip(a.source,a.output,a.index,a.file,a.iff_only,a.raw_iff,a.type,a.strict,a.log_output)
    if c.startswith('export-'):
        from .texture_tools.pipeline import export
        scope='atlas' if c=='export-uniform-atlas-dds' else 'scne' if c=='export-scne-textures' else 'all'
        requested=not a.raw or a.dds or c in ('export-dds','export-teamselectlogo-dds','export-uniform-atlas-dds')
        return export(a.input,a.output,getattr(a,'cdf',None),requested,a.gtf2dds,a.strict,scope)
    if c in ('import-dds','replace-iff-texture','replace-cdf-texture','import-uniform-atlas-dds','import-scne-texture','replace-court-texture'):
        from .texture_tools.pipeline import import_texture
        return import_texture(a.input,getattr(a,'selector','0'),a.dds_file,a.output,getattr(a,'cdf',None),a.dds2gtf)
    if c=='import-teamselectlogo-dds':
        from .texture_tools.pipeline import import_logo_batch
        return import_logo_batch(a.input,a.cdf,a.manifest,a.edited,a.output,a.dds2gtf)
    if c in ('import','list-overrides','validate-mod'):
        from .archive import importer
        return importer.stage(a.mod,a.input,a.iff,a.sub) if c=='import' else importer.listing(a.mod) if c=='list-overrides' else importer.validate(a.mod)
    if c=='build-copy':
        from .archive.build_copy import build
        return build(a.source,a.mod,a.output,a.overwrite,a.dry_run)
    if c=='validate-build':
        from .validation.build_validator import validate
        result=validate(a.source,a.modded);save_json(a.output/'build_validation.json',result,sources);return result
    if c.startswith('roster-'):
        from .roster import workflow
        from .roster.editor_model import EditorModel
        if c=='roster-detect':return workflow.detect(a.input)
        if c=='roster-validate':return EditorModel.open(a.input).validate()
        if c=='roster-save':return workflow.save(a.input,a.patch,a.output)
        return workflow.decode(a.input,a.output)
    if c=='inspect-txtr':
        from .formats.txtr import TXTR
        result=TXTR.from_bytes(Path(a.input).read_bytes()).info();save_json(a.output/'inspection.json',result,sources);return result
    if c in ('inspect-iff','validate-iff','round-trip-iff'):
        from .formats.standard_iff import StandardIFF
        iff=StandardIFF(Path(a.input).read_bytes())
        if c=='round-trip-iff':write_bytes(a.output,iff.raw,sources);return {'equal':a.output.read_bytes()==iff.raw}
        if c=='validate-iff':
            from .validation.standard_iff_validator import validate
            result=validate(iff.raw);save_json(a.output,result,sources);return result
        if a.dump_subfiles:iff.dump(a.output)
        else:save_json(a.output/'inspection.json',iff.manifest(),sources)
        return iff.manifest()
    if c in ('inspect-cdf-pair','validate-cdf-pair'):
        from .formats.cdf_backed_iff import CDFPair
        pair=CDFPair(Path(a.input).read_bytes(),Path(a.cdf).read_bytes());result=pair.manifest()
        result['valid']=True;save_json(a.output if c=='validate-cdf-pair' else a.output/'inspection.json',result,sources);return result
    if c=='inspect-tool-wrapper':
        from .formats.tool_wrapper import unwrap
        typ,blocks=unwrap(Path(a.input).read_bytes());return {'type':typ,'block_sizes':[len(b) for b in blocks]}
    raise ToolError('unknown_command',c)

def main(argv=None):
    args=parser().parse_args(argv)
    try:
        result=execute(args)
        if result is not None:print(json.dumps(result,indent=2,ensure_ascii=True))
        if isinstance(result,dict) and (result.get('valid') is False or result.get('status')=='failed'):return 1
        return 0
    except KeyboardInterrupt:
        print('Cancelled',file=sys.stderr);return 130
    except (ValueError,OSError,KeyError) as error:
        print(f'Error: {error}',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
