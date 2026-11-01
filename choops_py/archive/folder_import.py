"""Automatically recognize Python exports and nested binary/DDS overrides."""
from pathlib import Path
import json
import re
import struct
from collections import defaultdict
from .hash_names import replacement_hash as hash_name

RECORD_TYPES={'.txtr':'TXTR','.scne':'SCNE','.name':'NAME','.cdan':'CDAN','.layt':'LAYT','.rost':'ROST'}
LEGACY_RECORD_ALIASES={'icon_tatoo':'icon_tattoo'}


def legacy_record_name(name):
    return LEGACY_RECORD_ALIASES.get(name.casefold(),name)


def discover(archive,folder,job=None):
    folder=Path(folder)
    def linked(p):return p.is_symlink() or (hasattr(p,'is_junction') and p.is_junction())
    if linked(folder):raise ValueError('Linked override folders are blocked')
    folder=folder.resolve();files=[];pending=[folder]
    while pending:
        parent=pending.pop()
        for p in sorted(parent.iterdir(),key=lambda p:p.name.casefold()):
            if job:job.check()
            if linked(p):raise ValueError('Linked replacement path: '+str(p.relative_to(folder)))
            if p.is_dir():pending.append(p)
            elif p.is_file():files.append(p)
    hashes={e['hash']:e for e in archive.entries};groups=defaultdict(lambda:{'whole':None,'records':{},'dds':{},'dds_rank':{},'package_records':{}})
    ignored=0;issues=[];shadowed=[]
    def identity_name(entry,fallback):
        if entry['name']:return entry['name']
        if next(archive.chunks(entry,4),b'')==bytes.fromhex('ff3bef94'):return f"hash_{entry['hash']:08x}.iff"
        return fallback
    def owner(file):
        for parent in file.parents:
            parent_name=parent.name.removesuffix('.subfiles')
            name=parent_name if Path(parent_name).suffix.lower() in ('.iff','.bin') else parent_name+'.iff'
            e=hashes.get(hash_name(name)) if name.isascii() else None
            if e:return e,identity_name(e,name)
            # Some legacy exports use the source JB's TOC index as the top
            # folder (for example, 1004/shoe_sole.txtr). Resolve only a direct
            # numeric child of this selected override root.
            if parent.parent==folder and parent.name.isdecimal():
                index=int(parent.name)
                if index<len(archive.entries):
                    e=archive.entries[index]
                    resolved=identity_name(e,'')
                    if resolved:return e,resolved
            if parent==folder:break
        return None,None
    def add(group,kind,key,file):
        if key in group[kind]:issues.append('Duplicate target: '+str(file.relative_to(folder)))
        else:group[kind][key]=file
    consumed=set();formats=set()
    for marker in files:
        if marker.name in ('rip_report.json','extraction_manifest.json'):
            formats.add('python-archive-export');consumed.add(marker)
    def local_file(manifest,value):
        if not isinstance(value,str):return None
        candidate=manifest.parent/Path(value.replace('\\','/')).name
        return candidate if candidate in files else None
    for manifest in [p for p in files if p.name=='manifest.json']:
        if manifest.stat().st_size>16*1024*1024:continue
        try:metadata=json.loads(manifest.read_text(encoding='utf-8-sig'))
        except (ValueError,OSError):continue
        if not isinstance(metadata,dict):continue
        if isinstance(metadata.get('textures'),list) and isinstance(metadata.get('source'),str):
            source_name=Path(metadata['source'].replace('\\','/')).name
            entry=hashes.get(hash_name(source_name)) if source_name.isascii() else None
            if entry is None:entry,source_name=owner(manifest)
            if entry is None:issues.append('Unresolved Python export source: '+manifest.name);continue
            group=groups[entry['hash']];group['entry']=entry;group['name']=identity_name(entry,source_name)
            formats.add('python-texture-manifest');consumed.add(manifest)
            for ref in manifest.parent.glob('source_*'):
                if ref in files:consumed.add(ref)
            for texture in metadata['textures']:
                if not isinstance(texture,dict):raise ValueError('Invalid Python texture manifest entry')
                selector=texture.get('texture_name')
                if not isinstance(selector,str):continue
                raw=local_file(manifest,texture.get('raw_output_path'));dds_file=local_file(manifest,texture.get('dds_output_path'))
                if raw:
                    consumed.add(raw)
                    if '/texture_' in selector:add(group,'package_records',selector,raw)
                    else:
                        with raw.open('rb') as stream:prefix=stream.read(12)
                        typ='SCNE' if prefix[:4]==b'2kTl' and struct.unpack_from('>H',prefix,8)[0]==2 else 'TXTR'
                        add(group,'records',(selector,typ),raw)
                if dds_file:
                    consumed.add(dds_file)
                    if selector in group['dds']:issues.append('Duplicate manifest DDS: '+selector)
                    group['dds'][selector]=dds_file;group['dds_rank'][selector]=3
                ref=local_file(manifest,texture.get('gtf_output_path'))
                if ref:consumed.add(ref)
        elif metadata.get('family')=='standard-iff' and isinstance(metadata.get('records'),list):
            name=manifest.parent.name.removesuffix('.subfiles')
            entry=hashes.get(hash_name(name)) if name.isascii() else None
            if entry is None:continue
            group=groups[entry['hash']];group['entry']=entry;group['name']=identity_name(entry,name)
            formats.add('python-record-manifest');consumed.add(manifest)
            for record in metadata['records']:
                paths=sorted(manifest.parent.glob(str(record['index']).zfill(4)+'_*.'+record['type'].lower()+'.block*'),key=lambda p:int(p.suffix.removeprefix('.block')))
                if paths:
                    add(group,'records',(record['name'],record['type']),paths);consumed.update(paths)
    for i,file in enumerate(sorted(files,key=lambda p:str(p.relative_to(folder)).casefold())):
        if file in consumed:continue
        if job and i%100==0:job.check();job.progress(i,len(files),'Scanning nested overrides')
        ext=file.suffix.lower()
        if ext in ('.iff','.cdf','.bin'):
            e=hashes.get(hash_name(file.name)) if file.name.isascii() else None
            name=file.name
            if e is None:e,name=owner(file)
            if not e:issues.append('Unknown archive filename: '+str(file.relative_to(folder)));continue
            group=groups[e['hash']];group['entry']=e;group['name']=identity_name(e,name)
            if group['whole']:issues.append('Duplicate archive replacement: '+file.name)
            group['whole']=file;continue
        if ext not in RECORD_TYPES and ext!='.dds':ignored+=1;continue
        e,name=owner(file)
        if e is None:issues.append('No archive folder for '+str(file.relative_to(folder)));continue
        group=groups[e['hash']];group['entry']=e;group['name']=name
        if ext in RECORD_TYPES:
            formats.add('legacy-record-folders')
            add(group,'records',(legacy_record_name(file.stem),RECORD_TYPES[ext]),file)
        else:
            formats.add('legacy-record-folders')
            duplicate=re.fullmatch(r'(.+?)\s*\([0-9]+\)',file.stem)
            texture_stem=duplicate[1].rstrip() if duplicate else file.stem
            context=next((p for p in file.parents if p.suffix.lower() in RECORD_TYPES),None)
            category=next((p for p in file.parents if p.parent.name.upper() in ('TXTR','SCNE') and p.is_relative_to(folder)),None)
            if context:
                record_name=legacy_record_name(context.stem.removeprefix('_'));typ=RECORD_TYPES[context.suffix.lower()]
                if typ=='SCNE':selector=record_name+'/'+texture_stem
                elif typ=='TXTR':selector=record_name
                else:ignored+=1;continue
            elif category:
                # Older exports use TXTR/record/artwork.dds rather than a
                # record.txtr directory. The record folder is authoritative;
                # artwork may have a generic name such as logo.dds.
                record_name=legacy_record_name(category.name.removeprefix('_'))
                selector=record_name+'/'+texture_stem if category.parent.name.upper()=='SCNE' else record_name
            else:selector=texture_stem
            rank=(2 if context or category else 1)-(1 if duplicate else 0)
            previous=group['dds'].get(selector)
            if previous:
                old_rank=group['dds_rank'][selector]
                if rank==old_rank:issues.append('Duplicate DDS target: '+str(file.relative_to(folder)))
                elif rank>old_rank:
                    shadowed.append(str(previous.relative_to(folder)));group['dds'][selector]=file;group['dds_rank'][selector]=rank
                else:shadowed.append(str(file.relative_to(folder)))
            else:group['dds'][selector]=file;group['dds_rank'][selector]=rank
    if issues:raise ValueError('Override discovery failed: '+'; '.join(issues[:8]))
    if not groups:raise ValueError('Folder and subfolders contain no supported replacements or DDS textures')
    result=dict(groups=list(groups.values()),detected_formats=sorted(formats),scanned_files=len(files),ignored_files=ignored,shadowed_dds=shadowed,
                dds_files=sum(len(g['dds']) for g in groups.values()),binary_records=sum(len(g['records'])+len(g['package_records']) for g in groups.values()))
    resolve_legacy_targets(archive,result,folder,job)
    return result


def resolve_legacy_targets(archive,discovery,folder,job=None):
    """Resolve old record ordinals and uniquely misplaced named scene folders.

    Canonical archive folders win over relocated duplicate artwork. Explicit
    Python manifest selectors remain authoritative and are never guessed.
    """
    from ..formats.standard_iff import names,TYPES,StandardIFF
    from ..formats.record_labels import label
    from ..formats.binary import Binary
    groups={g['entry']['hash']:g for g in discovery['groups']};labels={};catalog=None
    discovery['resolved_targets']=[]
    def cdf_records(entry,data):
        from ..formats.cdf_backed_iff import CDFPair
        metadata=Binary(data)
        partner=hash_name(Path(metadata.utf16(metadata.relative(36),'be')).name)
        match=next((e for e in archive.entries if e['hash']==partner),None)
        if match is None:raise ValueError('CDF companion is missing')
        replacement=groups.get(partner,{}).get('whole')
        pair=CDFPair(data,replacement.read_bytes() if replacement else archive.read(match))
        return [(r['name'],r['type']) for r in pair.records]
    def records(entry):
        key=entry['hash']
        if key in labels:return labels[key]
        group=groups.get(key)
        if group and group['whole']:
            data=group['whole'].read_bytes()
            result=[(r['name'],r['type']) for r in StandardIFF(data).records] if data[:4]==bytes.fromhex('ff3bef94') else cdf_records(entry,data) if data[:4]==bytes.fromhex('f0985030') else []
        else:
            head=archive.read({**entry,'size':32});b=Binary(head);result=[]
            if head[:4]==bytes.fromhex('ff3bef94'):
                end,count=b.u32(8),b.u32(24)
                if end>entry['size']:raise ValueError('Invalid archive metadata: '+str(entry['name']))
                result=names(archive.read({**entry,'offset':entry['offset']+end,'size':entry['size']-end}),0,count)
                if len(result)<count:
                    header=Binary(archive.read({**entry,'size':b.u32(4)}));start=header.relative(28)
                    result += [(label(header.u32(header.relative(start+i*4)),str(i)),TYPES.get(header.u32(header.relative(start+i*4)+4),'UNKNOWN')) for i in range(len(result),count)]
            elif head[:4]==bytes.fromhex('f0985030'):
                result=cdf_records(entry,archive.read(entry))
        labels[key]=result;return result
    def global_matches(name,typ):
        nonlocal catalog
        if catalog is None:
            catalog=defaultdict(list)
            for entry in archive.entries:
                if job:job.check()
                for index,(label,kind) in enumerate(records(entry)):catalog[label.casefold(),kind].append((entry,index))
        return catalog.get((name.casefold(),typ),[])
    errors=[]
    for group in list(groups.values()):
        local=records(group['entry'])
        for selector,file in list(group['dds'].items()):
            if group['dds_rank'][selector]>=3:continue
            name,_,texture=selector.partition('/');typ='SCNE' if texture else 'TXTR'
            matches=[i for i,(label,kind) in enumerate(local) if label.casefold()==name.casefold() and kind==typ]
            target=group;canonical=name
            if not matches and name.isdigit() and int(name)<len(local) and local[int(name)][1]==typ:
                canonical=local[int(name)][0];matches=[int(name)]
            if not matches:
                candidates=global_matches(name,typ)
                if len(candidates)!=1:
                    errors.append(group['name']+'/'+selector+' has no unique archive record');continue
                entry,index=candidates[0]
                target=groups.get(entry['hash'])
                if target is None:
                    target={'whole':None,'records':{},'dds':{},'dds_rank':{},'package_records':{},'entry':entry,'name':entry['name'] or f"hash_{entry['hash']:08x}.iff"}
                    groups[entry['hash']]=target
                canonical=records(entry)[index][0]
            normalized=canonical+('/'+texture if texture else '')
            if target is group and normalized==selector:continue
            group['dds'].pop(selector);rank=group['dds_rank'].pop(selector)
            if target is not group:rank=0
            if normalized in target['dds']:
                previous_rank=target['dds_rank'][normalized]
                if rank==previous_rank:errors.append('Duplicate resolved DDS: '+normalized);continue
                if rank<previous_rank:discovery['shadowed_dds'].append(str(file.relative_to(folder)))
                else:
                    discovery['shadowed_dds'].append(str(target['dds'][normalized].relative_to(folder)))
                    target['dds'][normalized]=file;target['dds_rank'][normalized]=rank
            else:target['dds'][normalized]=file;target['dds_rank'][normalized]=rank
            discovery['resolved_targets'].append({'input':str(file.relative_to(folder)),'archive':target['name'],'selector':normalized})
    if errors:raise ValueError('Override target validation failed: '+'; '.join(errors[:12]))
    for group in list(groups.values()):
        if not (group['records'] or group['dds'] or group['package_records']):continue
        partner=groups.get(hash_name(group['name'][:-4]+'.cdf'))
        if partner and partner['whole'] and not (partner['records'] or partner['dds'] or partner['package_records']):
            group['cdf_whole']=partner['whole'];partner['whole']=None
    # A complete CDF replacement alone still needs its IFF metadata validated
    # and normalized. Route it through the paired importer automatically.
    for group in list(groups.values()):
        if not group['whole'] or not group['name'].lower().endswith('.cdf'):continue
        identity=hash_name(group['name'][:-4]+'.iff')
        entry=next((e for e in archive.entries if e['hash']==identity),None)
        if entry is None or archive.read({**entry,'size':4})!=bytes.fromhex('f0985030'):continue
        target=groups.get(identity)
        if target is None:
            target=dict(whole=None,records={},dds={},dds_rank={},package_records={},entry=entry,name=group['name'][:-4]+'.iff')
            groups[identity]=target
        if target.get('cdf_whole'):raise ValueError('Duplicate CDF companion replacement')
        target['cdf_whole']=group['whole'];group['whole']=None
    discovery['groups']=[g for g in groups.values() if g['whole'] or g['records'] or g['dds'] or g['package_records'] or g.get('cdf_whole')]



def compile_group(archive,group,job=None):
    from ..formats.standard_iff import StandardIFF
    from ..formats.standard_iff_writer import replace_records_expanding
    from ..formats.compression import decode
    from ..formats.tool_wrapper import unwrap
    from ..texture_tools.override_import import apply_dds
    original=archive.read(group['entry'])
    data=group['whole'].read_bytes() if group['whole'] else original
    from ..texture_tools.archive_layout import stadium_archive,normalize_record
    preserve=not stadium_archive(group)
    if not group['records'] and not group['dds'] and not group['package_records'] and not group.get('cdf_whole') and (not preserve or data[:4] not in (bytes.fromhex('ff3bef94'),bytes.fromhex('f0985030'))):return data,[]
    if data[:4]==bytes.fromhex('f0985030'):return compile_cdf_group(archive,group,data,job)
    from .iff_validation import standard_iff
    iff=standard_iff(data,group['name'],'replacement');decoded={};changes={};details=[];scene_baselines={}
    base=standard_iff(original,group['name'],'source') if preserve else None;base_decoded={}
    def base_parts(rec):
        matches=[r for r in base.records if r['name'].casefold()==rec['name'].casefold() and r['type']==rec['type']]
        if len(matches)!=1:raise ValueError('Texture record has no unique base-JB reference: '+rec['name'])
        reference=[]
        for block,start,end in base.spans(matches[0]):
            if block not in base_decoded:
                b=base.blocks[block];base_decoded[block]=decode(base.raw[b['start']:b['start']+b['size']],b['logical_size'])
            reference.append(base_decoded[block][start:end])
        return reference
    def find(name,typ=None):
        matches=[r for r in iff.records if r['name'].casefold()==name.casefold() and (typ is None or r['type']==typ)]
        if len(matches)!=1:raise ValueError('Unknown/ambiguous record '+name+' in '+group['name'])
        return matches[0]
    def parts(rec):
        if rec['index'] in changes:return changes[rec['index']]
        result=[]
        for block,start,end in iff.spans(rec):
            if block not in decoded:
                b=iff.blocks[block];decoded[block]=decode(iff.raw[b['start']:b['start']+b['size']],b['logical_size'])
            result.append(decoded[block][start:end])
        return result
    dds_records={name.casefold() for name in group['dds'] if '/' not in name}
    for (name,typ),file in group['records'].items():
        if typ=='TXTR' and name.casefold() in dds_records:continue
        if job:job.check()
        rec=find(name,typ)
        if isinstance(file,list):changes[rec['index']]=[p.read_bytes() for p in file]
        else:
            raw=file.read_bytes();changes[rec['index']]=unwrap(raw)[1] if raw[:4]==b'2kTl' else [raw]
    from ..texture_tools.override_import import apply_raw_texture
    from ..modding.court_template import active_slots
    dds_selectors={selector.casefold() for selector in group['dds']}
    for selector,file in group['package_records'].items():
        if selector.casefold() in dds_selectors:continue
        name,texture=selector.split('/',1);rec=find(name,'SCNE')
        if preserve:scene_baselines.setdefault(rec['index'],parts(rec))
        allowed=active_slots(parts(rec))
        if allowed is not None and int(texture.removeprefix('texture_')) not in allowed:
            details.append(dict(selector=selector,status='inactive',reason='Single-surface court has disabled this texture slot'));continue
        raw=file.read_bytes();replacement=unwrap(raw)[1] if raw[:4]==b'2kTl' else [raw]
        changes[rec['index']]=apply_raw_texture(parts(rec),texture,replacement)
    for i,(selector,file) in enumerate(group['dds'].items()):
        if job:job.check();job.progress(i,len(group['dds']),'DDS priority: '+group['name']+'/'+selector)
        if '/' in selector:
            name,texture=selector.split('/',1);rec=find(name,'SCNE')
            if preserve:scene_baselines.setdefault(rec['index'],parts(rec))
            from ..formats.package import textures as package_textures
            items=package_textures(parts(rec))
            if texture.startswith('texture_') and texture[8:].isdigit() and int(texture[8:])>=len(items):
                from ..texture_tools import dds
                dds.inspect(file.read_bytes())
                details.append(dict(selector=selector,status='unmatched',input_file=str(file),reason=f'Scene has {len(items)} texture slots; supply the matching replacement SCNE to import this texture'))
                continue
            if not texture.startswith('texture_'):
                used={int(s.split('/texture_',1)[1]) for s in group['dds'] if s.startswith(name+'/texture_') and s.split('/texture_',1)[1].isdigit()}
                available=[t.index for t in items if t.index not in used]
                if len(items)==1:index=0
                elif texture.isdigit() and int(texture)<len(items):index=int(texture)
                elif len(available)==1:
                    from ..formats.txtr import TXTR
                    from ..texture_tools import dds
                    candidate=items[available[0]];layout=TXTR([candidate.header,candidate.payload]).info();incoming=dds.inspect(file.read_bytes())
                    if any(layout[key]!=incoming[key] for key in ('width','height','format')):raise ValueError('Unmatched legacy scene texture '+selector)
                    index=available[0]
                else:raise ValueError('Ambiguous legacy scene texture '+selector)
                texture='texture_'+str(index)
                if name+'/'+texture in group['dds']:
                    details.append(dict(selector=selector,status='shadowed',reason='canonical scene texture filename has priority'));continue
            allowed=active_slots(parts(rec))
            if allowed is not None and int(texture.removeprefix('texture_')) not in allowed:
                details.append(dict(selector=selector,status='inactive',reason='Single-surface court has disabled this texture slot'));continue
        else:texture=selector;rec=find(selector,'TXTR')
        options={}
        if preserve:
            from ..formats.txtr import TXTR
            reference=base_parts(rec)
            if rec['type']=='TXTR':target=TXTR(reference)
            else:
                current=items[int(texture.removeprefix('texture_'))]
                matches=[t for t in package_textures(reference) if t.header[:4]==current.header[:4]]
                if len(matches)!=1:raise ValueError('Scene texture has no unique base-JB identity: '+selector)
                target=TXTR([matches[0].header,matches[0].payload])
            options=dict(preserve_layout=True,reference=target,allow_single_cube_face=True)
        try:changed,info=apply_dds(parts(rec),rec['type'],texture,file,job,**options)
        except (ValueError,OSError) as error:raise ValueError(selector+': '+str(error)) from error
        changes[rec['index']]=changed
        details.append(dict(selector=(name+'/'+texture if '/' in selector else selector),input_selector=selector,**info))
    if preserve:
        for rec in iff.records:
            if rec['type'] not in ('TXTR','SCNE') or (rec['index'] not in changes and not group['whole']):continue
            reference=base_parts(rec)
            if job:job.check();job.progress(0,1,'Base resolution: '+group['name']+'/'+rec['name'])
            before=scene_baselines.get(rec['index'],parts(rec))
            normalized,reports=normalize_record(parts(rec),reference,rec['type'],job,compact=False)
            if rec['type']=='SCNE' and len(before)==2:
                from ..formats.package import repack_images
                normalized=repack_images(before,normalized)
            changes[rec['index']]=normalized
            details.extend(dict(selector=rec['name'],policy='base-JB texture layout',**info) for info in reports)
    if not changes:return data,details
    if job:job.check();job.progress(0,1,'Rebuilding and compressing '+group['name'])
    return replace_records_expanding(iff,changes),details


def compile_cdf_group(archive,group,data,job=None):
    from ..formats.cdf_backed_iff import CDFPair
    from ..formats.cdf_backed_iff_writer import replace_texture_records
    from ..formats.compression import decode
    from ..formats.tool_wrapper import unwrap
    from ..texture_tools.override_import import apply_dds
    companion=group['name'][:-4]+'.cdf'
    entry=next((e for e in archive.entries if e['hash']==hash_name(companion)),None)
    if entry is None:raise ValueError('CDF companion is missing: '+companion)
    cdf=group['cdf_whole'].read_bytes() if group.get('cdf_whole') else archive.read(entry)
    pair=CDFPair(data,cdf);changes={};details=[]
    from ..texture_tools.archive_layout import stadium_archive,normalize_record
    preserve=not stadium_archive(group)
    base_cdf=archive.read(entry);base_pair=CDFPair(archive.read(group['entry']),base_cdf) if preserve else None
    def base_parts(rec):
        matches=[r for r in base_pair.records if r['name'].casefold()==rec['name'].casefold() and r['type']=='TXTR']
        if not matches and group.get('logo_templates') and group['name'].casefold()=='teamselectlogo.iff':
            donor=group['logo_templates'].get(rec['name'])
            matches=[r for r in base_pair.records if r['name']==donor and r['type']=='TXTR']
        if len(matches)!=1:raise ValueError('CDF texture has no unique base-JB reference: '+rec['name'])
        return [decode(base_cdf[matches[0][k+'_offset']:matches[0][k+'_offset']+matches[0][k+'_length']]) for k in ('header','payload')]
    def find(name):
        matches=[r for r in pair.records if r['name'].casefold()==name.casefold() and r['type']=='TXTR']
        if len(matches)!=1:raise ValueError('Unknown/ambiguous CDF texture '+name)
        return matches[0]
    def parts(rec):
        return changes.get(rec['index']) or [decode(cdf[rec[k+'_offset']:rec[k+'_offset']+rec[k+'_length']]) for k in ('header','payload')]
    if group['package_records']:raise ValueError('CDF logo banks do not contain SCNE textures')
    dds_records={name.casefold() for name in group['dds']}
    for (name,kind),file in group['records'].items():
        if kind=='TXTR' and name.casefold() in dds_records:continue
        if kind!='TXTR':raise ValueError('CDF logo banks require TXTR records')
        rec=find(name);raw=file.read_bytes();changes[rec['index']]=unwrap(raw)[1] if raw[:4]==b'2kTl' else [raw]
    for name,file in group['dds'].items():
        if job:job.check()
        rec=find(name);options={}
        if preserve:
            from ..formats.txtr import TXTR
            options=dict(preserve_layout=True,reference=TXTR(base_parts(rec)),allow_single_cube_face=True)
        changed,info=apply_dds(parts(rec),'TXTR',name,file,job,**options)
        changes[rec['index']]=changed;details.append(dict(selector=name,**info))
    if preserve:
        for rec in pair.records:
            if rec['type']!='TXTR' or (rec['index'] not in changes and not group['whole'] and not group.get('cdf_whole')):continue
            reference=base_parts(rec)
            normalized,reports=normalize_record(parts(rec),reference,'TXTR',job)
            if normalized!=parts(rec):changes[rec['index']]=normalized
            details.extend(dict(selector=rec['name'],policy='base-JB texture layout',**info) for info in reports)
    if job:job.check();job.progress(0,1,'Rebuilding paired texture bank '+group['name'])
    if not changes:
        from ..formats.compression import game_compatible
        if all(game_compatible(cdf[r[k+'_offset']:r[k+'_offset']+r[k+'_length']]) for r in pair.records for k in ('header','payload')):
            group['compiled_companion']=(entry,companion,cdf)
            return data,details
    rebuilt,payload=replace_texture_records(data,cdf,changes)
    group['compiled_companion']=(entry,companion,payload)
    return rebuilt,details
