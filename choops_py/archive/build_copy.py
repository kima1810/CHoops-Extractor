"""Transactional modded JB folder builds. Vanilla is always read-only."""
import json
import os
import shutil
import uuid
import hashlib
from pathlib import Path
from .importer import validate
from .usrdir_reader import Archive,usrdir
from .manifests import OUTPUT,build_destination as safe_output,digest
from ..core.reports import save_build_json
from ..core.paths import reject_links
from ..core.errors import ToolError
from .iff_validation import standard_iff
from ..formats.standard_iff_writer import record,record_blocks,replace_records
from ..formats.tool_wrapper import unwrap
from ..formats.cdf_backed_iff import CDFPair
from ..texture_tools.pipeline import Container,imported_image

def jb_root(source):
    source=Path(source).resolve()
    for p in [source,*source.parents]:
        if any((p/'PS3_GAME'/'USRDIR'/n).is_file() for n in ('0A','0A.SDAT')):return p
    raise ToolError('jb_folder_required','Select a vanilla JB folder containing PS3_GAME/USRDIR/0A')

def inventory(source):
    return {str(p.relative_to(source)):{'size':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns} for p in source.rglob('*') if p.is_file()}


def import_summary(mod):
    path=Path(mod)/'folder_import_report.json'
    if not path.is_file():return {}
    report=json.loads(path.read_text(encoding='utf-8'))
    unapplied=report.get('unapplied_overrides',[])
    return {'staged_archives':report.get('staged'),'applied_dds':sum('width' in item and not item.get('policy') for group in report.get('imports',[]) for item in group['dds_imports']),
            'unapplied_count':len(unapplied),'unapplied_overrides':unapplied,'report':str(path.resolve())}

def preflight(source,mod,job=None,*,for_build=True):
    archive=Archive(source)
    if for_build:archive.require_writable()
    rows=validate(mod);grouped={};patches=[]
    options=Path(mod)/'import_options.json'
    allow_growth=False
    if options.exists():
        policy=json.loads(options.read_text(encoding='utf8'))
        if policy.get('schema')!=1:raise ToolError('invalid_import_options','Unsupported import options')
        allow_growth=policy.get('allow_archive_growth') is True
    expected_sources={}
    conditions=Path(mod)/'source_preconditions.json'
    if conditions.exists():
        document=json.loads(conditions.read_text(encoding='utf-8'))
        if document.get('schema')!=1:raise ToolError('invalid_source_preconditions','Unsupported schema')
        for i,expected in enumerate(document['entries']):
            if job:job.check();job.progress(i,len(document['entries']),'Validating original asset '+str(expected['index']))
            index=expected['index']
            if not isinstance(index,int) or not 0<=index<len(archive.entries):raise ToolError('source_version_mismatch','TOC index differs')
            entry=archive.entries[index]
            if entry['hash']!=expected['hash']:
                raise ToolError('source_version_mismatch','Original archive asset changed since staging')
            if index in expected_sources and expected_sources[index]!=expected['sha256']:
                raise ToolError('source_version_mismatch','Conflicting source fingerprints')
            expected_sources[index]=expected['sha256']
    for row in rows:grouped.setdefault(row['archive'].lower(),[]).append(row)
    for i,(name,group) in enumerate(grouped.items()):
        if job:job.check();job.progress(i,len(grouped),'Preflight staged archive '+name)
        matches=[e for e in archive.entries if e['name'] and e['name'].lower()==name]
        if not matches:
            from .hash_names import replacement_hash as hash_name
            matches=[e for e in archive.entries if e['hash']==hash_name(name) and e['name'] is None]
            if len(matches)==1:matches[0]={**matches[0],'name':name}
        if len(matches)!=1:raise ToolError('unresolved_archive_identity',name)
        entry=matches[0];original=archive.read(entry);data=original
        expected=expected_sources.pop(entry['index'],None)
        if expected is not None and digest(original)!=expected:
            raise ToolError('source_version_mismatch','Original archive asset changed since staging')
        for row in group:
            path=Path(mod)/row['path'];replacement=path.read_bytes()
            if row.get('kind')=='dds':
                # Reuse the same import pipeline, using an output/temp copy as the
                # evolving source. Nothing is written into vanilla.
                work=safe_output(OUTPUT/'temp'/('build_preflight_'+uuid.uuid4().hex));work.mkdir()
                try:
                    input_file=work/entry['name'];input_file.write_bytes(data)
                    c=Container(input_file)
                    asset=c.select(row['subfile']);image,_=imported_image(asset,path);data=c.replacement(asset,image)
                finally:
                    shutil.rmtree(work)
            elif row['subfile'] is not None:
                iff=standard_iff(data,name,'subfile destination');rec=record(iff,row['subfile'])
                parts=unwrap(replacement)[1] if replacement[:4]==b'2kTl' else [replacement]
                data=replace_records(iff,{rec['index']:parts})
            else:data=replacement
        if data[:4]==bytes.fromhex('ff3bef94'):
            from ..formats.standard_iff_writer import repair_compression
            data,_=repair_compression(standard_iff(data,name,'replacement'))
        if len(data)>len(original) and not allow_growth:raise ToolError('archive_extent_capacity_exceeded',f'{name} needs {len(data)} bytes; allocation {len(original)}')
        if len(data)<len(original):
            if data[:4] not in (bytes.fromhex('ff3bef94'),bytes.fromhex('f0985030')) and not name.endswith('.cdf'):raise ToolError('archive_size_change_blocked',name)
            if data[:4]==bytes.fromhex('ff3bef94'):standard_iff(data,name,'replacement')
            data+=b'\0'*(len(original)-len(data))
        if data[:4]==bytes.fromhex('ff3bef94'):standard_iff(data,name,'replacement')
        patches.append((entry,data))
    # Preconditions for assets not being replaced are still checked, but streamed.
    for index,expected in expected_sources.items():
        checksum=hashlib.sha256()
        for chunk in archive.chunks(archive.entries[index]):
            if job:job.check()
            checksum.update(chunk)
        if checksum.hexdigest()!=expected:
            raise ToolError('source_version_mismatch','Original archive asset changed since staging')
    final={e['name'].lower():data for e,data in patches if e['name']}
    for entry,data in patches:
        if data[:4]==bytes.fromhex('f0985030'):
            partner=entry['name'][:-4]+'.cdf';matches=[e for e in archive.entries if e['name'] and e['name'].lower()==partner.lower()]
            if len(matches)!=1:raise ToolError('cdf_pair_required',partner)
            payload=final[partner.lower()] if partner.lower() in final else archive.read(matches[0])
            CDFPair(data,payload)
        elif entry['name'].lower().endswith('.cdf'):
            partner=entry['name'][:-4]+'.iff';matches=[e for e in archive.entries if e['name'] and e['name'].lower()==partner.lower()]
            if len(matches)!=1:raise ToolError('cdf_pair_required',partner)
            header=final[partner.lower()] if partner.lower() in final else archive.read(matches[0])
            CDFPair(header,data)
    from ..modding.addition_manifest import load as load_additions
    additions=load_additions(mod,archive)
    from ..modding.team_assets import build_alternates
    additions,_=build_alternates(archive,patches,additions)
    if additions:
        from .add_assets import validate_plan
        validate_plan(source,additions,{e['name']:data for e,data in patches})
    return archive,patches

def patch_parts(archive,directory,entry,data):
    start=entry['offset'];remaining=len(data);position=0;base=0
    for part in archive.parts:
        end=base+part['size']
        if base<=start<end and remaining:
            n=min(remaining,end-start);path=directory/part['name']
            with path.open('r+b') as stream:stream.seek(start-base);stream.write(data[position:position+n])
            remaining-=n;position+=n;start+=n
        base=end
    if remaining:raise ToolError('incomplete_archive_patch','Split archive write did not consume all data')

def verify_preserved_ranges(source, copied, archive, patches, job=None):
    """Prove every byte outside staged logical extents equals the source."""
    source=Path(source);copied=Path(copied)
    ranges={};base=0;verified=0;total=sum(item['size'] for item in inventory(source).values())
    for part in archive.parts:
        intervals=[]
        for entry,data in patches:
            lo=max(base,entry['offset']);hi=min(base+part['size'],entry['offset']+len(data))
            if lo<hi:intervals.append((lo-base,hi-base))
        ranges[str((archive.path/part['name']).relative_to(source))]=intervals
        base+=part['size']
    for relative in inventory(source):
        excluded=ranges.get(relative,[]);position=0
        with (source/relative).open('rb') as left,(copied/relative).open('rb') as right:
            while True:
                if job:job.check()
                old=left.read(1024*1024);new=right.read(1024*1024)
                if not old:
                    if new:raise ToolError('build_validation_failed','Copied file grew')
                    break
                if len(old)!=len(new):raise ToolError('build_validation_failed','Copied file resized')
                cursor=0
                for lo,hi in sorted(excluded):
                    if lo>=position+len(old) or hi<=position:continue
                    start=max(0,lo-position);end=min(len(old),hi-position)
                    if old[cursor:start]!=new[cursor:start]:raise ToolError('build_validation_failed','Untouched bytes changed')
                    cursor=end
                if old[cursor:]!=new[cursor:]:raise ToolError('build_validation_failed','Untouched bytes changed')
                position+=len(old);verified+=len(old)
                if job:job.progress(total+verified,2*total,'Verifying untouched bytes')


def build(source,mod,output,overwrite=False,dry_run=False,job=None):
    if job:job.check()
    src=jb_root(source);out=safe_output(output,[src,mod])
    reject_links(src)
    if out.exists() and not out.is_dir():raise ToolError('unsafe_build_output','Choose a folder, not an existing file')
    if out.exists() and any(out.iterdir()):
        marker=out/'build_manifest.json'
        if not overwrite:raise ToolError('output_exists','Use --overwrite for an existing generated JB build')
        if not marker.is_file() or json.loads(marker.read_text(encoding='utf-8')).get('project_kind')!='choops-jb-copy':raise ToolError('unowned_build_output',"Refusing to overwrite a folder without this tool's build manifest")
        reject_links(out)
    before=inventory(src)
    archive,patches=preflight(src,mod,job);plan=[{'archive':e['name'],'index':e['index'],'size':len(data),'sha256':digest(data)} for e,data in patches]
    from ..modding.addition_manifest import load as load_additions
    additions=load_additions(mod,archive)
    from ..modding.team_assets import build_alternates
    additions,warnings=build_alternates(archive,patches,additions)
    fallback_file=Path(mod)/'alternate_fallbacks.json'
    if fallback_file.is_file():warnings.extend(item['message'] for item in json.loads(fallback_file.read_text(encoding='utf8')))
    growing=bool(additions) or any(len(data)>e['size'] for e,data in patches)
    summary=import_summary(mod)
    if dry_run:return {'dry_run':True,'source':str(src),'output':str(out),'import_summary':summary,'patches':plan,'added_assets':list(additions),'warnings':warnings,'archive_relocation_required':growing}
    if growing:
        from .add_assets import build as relocated_build
        staging=safe_output(out.parent/('.jb_build_'+uuid.uuid4().hex),[src,mod]);backup=None
        try:
            result=relocated_build(src,additions,staging,{e['name']:data for e,data in patches},job)
            if inventory(src)!=before:raise ToolError('vanilla_changed_during_build','Source changed during rebuild; retry')
            manifest={'project_kind':'choops-jb-copy','source':str(src),'mod':str(Path(mod).resolve()),'output':str(out),'import_summary':summary,'patches':plan,'added_assets':list(additions),'warnings':warnings,'archive_relocation_required':True,'validation':result}
            save_build_json(staging/'build_manifest.json',manifest,[src,mod])
            if out.exists():
                backup=safe_output(out.parent/('.jb_previous_'+uuid.uuid4().hex));out.rename(backup)
            staging.rename(out)
            if backup:shutil.rmtree(backup)
            return manifest
        except BaseException:
            if staging.exists():shutil.rmtree(safe_output(staging))
            if backup and backup.exists() and not out.exists():backup.rename(out)
            raise
    out.parent.mkdir(parents=True,exist_ok=True)
    if shutil.disk_usage(out.parent).free<sum(item['size'] for item in before.values()):
        raise ToolError('insufficient_disk_space','Insufficient disk space for copied JB')
    staging=safe_output(out.parent/('.jb_build_'+uuid.uuid4().hex),[src,mod]);backup=None
    print('Copying vanilla JB into a separate output build...',flush=True)
    try:
        total=sum(item['size'] for item in before.values());copied_bytes=0
        def copy_file(left,right):
            nonlocal copied_bytes
            if job:job.check()
            with Path(left).open('rb') as original,Path(right).open('xb') as destination:
                while True:
                    if job:job.check()
                    data=original.read(1024*1024)
                    if not data:break
                    destination.write(data);copied_bytes+=len(data)
                    if job:job.progress(copied_bytes,2*total,'Copying original JB')
            shutil.copystat(left,right)
            return right
        shutil.copytree(src,staging,copy_function=copy_file)
        copied_usrdir=staging/archive.path.relative_to(src)
        for entry,data in patches:
            if job:job.check()
            patch_parts(archive,copied_usrdir,entry,data)
        copied=Archive(copied_usrdir)
        for entry,data in patches:
            if copied.read(copied.entries[entry['index']])!=data:raise ToolError('build_validation_failed',f"Written archive differs: {entry['name']}")
        for relative,metadata in before.items():
            path=staging/relative
            if not path.is_file() or path.stat().st_size!=metadata['size']:raise ToolError('build_validation_failed',f'Copied file missing or resized: {relative}')
        verify_preserved_ranges(src,staging,archive,patches,job)
        if inventory(src)!=before:raise ToolError('vanilla_changed_during_build','Vanilla source inventory changed during copying; discard build and retry')
        manifest={'project_kind':'choops-jb-copy','source':str(src),'mod':str(Path(mod).resolve()),'output':str(out),'import_summary':summary,'patches':plan,'file_count':len(before),'vanilla_inventory_unchanged':True,'validation':{'inventory_and_sizes':True,'patched_extents_byte_exact':True,'all_unpatched_bytes_exact':True,'console_gameplay':'not tested'}}
        save_build_json(staging/'build_manifest.json',manifest,[src,mod])
        if out.exists():
            backup=safe_output(out.parent/('.jb_previous_'+uuid.uuid4().hex));out.rename(backup)
        staging.rename(out)
        if backup:shutil.rmtree(backup)
        return manifest
    except BaseException:
        # Cleanup also applies to CLI Ctrl+C/SystemExit before publication.
        if staging.exists():shutil.rmtree(safe_output(staging))
        if backup and backup.exists() and not out.exists():backup.rename(out)
        raise
