"""Argparse entry point for texture, roster and JB-copy workflows."""
import argparse
import json
import sys
from pathlib import Path
from .commands import COMMANDS,SPECS
from .archive.manifests import safe_output,write_bytes
from .core.errors import ToolError
from .core.reports import save_json

def parser():
    p=argparse.ArgumentParser(description='PS3 College Hoops 2K8 texture/roster modding; build a separate JB copy')
    sub=p.add_subparsers(dest='command',required=True);sub.add_parser('gui')
    for name,spec in COMMANDS.items():
        s=sub.add_parser(name)
        for field in spec.fields:s.add_argument(field)
        for group in spec.options:
            if group=='audio-category':
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
    sources=[getattr(a,key) for key in ('source','input','cdf','dds_file','wav_file','image','mod','modded','edited','patch') if getattr(a,key,None)]
    if hasattr(a,'output'):a.output=safe_output(a.output,sources)
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
    if c=='fill-five-uniforms':
        from .modding.add_alternate import fill_five
        return fill_five(a.source,a.output)
    if c=='add-archive-assets':
        from .archive.add_assets import build
        from .core.paths import reject_links
        folder=Path(a.input);reject_links(folder)
        additions={p.name:p.read_bytes() for p in folder.glob('*.iff') if p.is_file()}
        return build(a.source,additions,a.output)
    if c=='add-uniform-alternate':
        from .modding.add_alternate import add
        return add(a.source,int(a.template),int(a.asset),int(a.variant),a.output)
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
