"""Transactional append-only additions in a copied JB, using spare TOC space."""
import os
import re
import shutil
import struct
import uuid
import hashlib
from pathlib import Path
from .usrdir_reader import Archive
from .hash_names import hash_name,replacement_hash
from .manifests import safe_output, OUTPUT
from .build_copy import jb_root, inventory
from ..core.paths import reject_links
from ..formats.standard_iff import StandardIFF
from ..formats.binary import Binary


class CapacityError(ValueError):
    pass


def meaningful_iff(data):
    end=Binary(data).u32(4) if data[:4]==bytes.fromhex("f0985030") else StandardIFF(data).file_length
    trailer=data[end:]
    if trailer[:4]==bytes.fromhex('aa171516'):
        end=end+8+Binary(trailer).u32(4,'<')
        if end>len(data) or any(data[end:]):raise ValueError('Unknown IFF trailer bytes')
    elif any(trailer):raise ValueError('Unknown IFF trailer')
    else:pass
    return data[:end]


def validate_payload(data):
    from ..formats.compression import decode
    iff=StandardIFF(data)
    for block in iff.blocks:
        if block['logical_size']>128*1024*1024:raise ValueError('Logical asset block exceeds insertion limit')
        decode(data[block['start']:block['start']+block['size']],block['logical_size'])


def asset_payload(name,data,changes):
    if name.lower().endswith('.cdf') or data[:4]==bytes.fromhex('f0985030'):
        from ..formats.cdf_backed_iff import CDFPair
        from ..formats.compression import decode
        iff_name=name[:-4]+'.iff' if name.lower().endswith('.cdf') else name
        cdf_name=iff_name[:-4]+'.cdf'
        if iff_name not in changes or cdf_name not in changes:raise ValueError('CDF changes require both matching IFF and CDF assets')
        iff=meaningful_iff(changes[iff_name]);cdf=changes[cdf_name]
        pair=CDFPair(iff,cdf)
        if pair.cdf_name.lower()!=cdf_name.lower():raise ValueError('CDF filename link differs from asset name')
        b=Binary(iff)
        if b.u32(16)!=2 or b.relative(20)!=40:raise ValueError('Unsupported CDF block layout')
        sizes=(b.u32(52),b.u32(84))
        if any(not 0<n<=128*1024*1024 for n in sizes):raise ValueError('CDF logical block exceeds limit')
        for r in pair.records:
            for prefix,size in zip(('header','payload'),sizes):
                offset=r[prefix+'_offset'];length=r[prefix+'_length']
                decode(cdf[offset:offset+length],size)
        return cdf if name.lower().endswith('.cdf') else iff
    result=meaningful_iff(data);validate_payload(result);return result


def plan(source, additions, replacements=None):
    archive=Archive(source);replacements=replacements or {}
    if not additions and not replacements:raise ValueError('No asset changes supplied')
    if any(e['toc_flags'] for e in archive.entries):raise ValueError('Unclassified nonzero TOC flags block insertion')
    by_hash={e['hash']:e for e in archive.entries}
    if len(by_hash)!=len(archive.entries):raise ValueError('Source has duplicate hashes')
    first=min(e['offset'] for e in archive.entries)
    head_end=24+len(archive.parts)*16+len(archive.entries)*16
    with (archive.path/'0A').open('rb') as f:header=bytearray(f.read(first))
    if any(header[head_end:first]):raise ValueError('Unclassified nonzero header padding')
    if len(additions)*16>first-head_end:
        raise CapacityError('Insufficient verified zero TOC padding')
    records=[];toc_start=24+len(archive.parts)*16
    for i,e in enumerate(archive.entries):records.append(list(struct.unpack_from('>4I',header,toc_start+i*16)))
    cursor=sum(p['size'] for p in archive.parts);appended=[];patches=[]
    for name,data in additions.items():
        if not re.fullmatch(r'[A-Za-z0-9_-]+\.(?:iff|cdf)',name,re.IGNORECASE):raise ValueError('Unsafe or unsupported new asset name')
        h=hash_name(name)
        if h in by_hash:raise ValueError('Asset name/hash already exists: '+name)
        by_hash[h]=None
        data=asset_payload(name,data,{**additions,**replacements})
        if len(data)>128*1024*1024:raise ValueError('Asset exceeds insertion limit')
        records.append([h,cursor//archive.alignment,0,len(data)])
        appended.append((cursor,data,name));cursor=(cursor+len(data)+archive.alignment-1)//archive.alignment*archive.alignment
    for name,data in replacements.items():
        h=replacement_hash(name);e=by_hash.get(h)
        if e is None:raise ValueError('Replacement asset missing: '+name)
        data=asset_payload(name,data,{**additions,**replacements})
        row=next(row for row in records if row[0]==h)
        row[3]=len(data)
        if len(data)<=e['size']:
            patches.append((e['offset'],data+b'\0'*(e['size']-len(data))))
        else:
            row[1]=cursor//archive.alignment
            appended.append((cursor,data,name))
            cursor=(cursor+len(data)+archive.alignment-1)//archive.alignment*archive.alignment
    final_total=(cursor+2047)//2048*2048
    growth=final_total-sum(p['size'] for p in archive.parts)
    max_bank=max(p['size'] for p in archive.parts)
    if archive.parts[-1]['size']+growth>max(max_bank,16*1024*1024):
        raise CapacityError('Addition exceeds the bounded final-bank limit')
    records.sort(key=lambda row:row[0])
    struct.pack_into('>I',header,16,len(records))
    struct.pack_into('>I',header,24+(len(archive.parts)-1)*16,(archive.parts[-1]['size']+growth)//2048)
    for i,row in enumerate(records):struct.pack_into('>4I',header,toc_start+i*16,*row)
    return archive,bytes(header),appended,patches,final_total


def checksum(chunks):
    h=hashlib.sha256()
    for data in chunks:h.update(data)
    return h.hexdigest()


def build(source, additions, output, replacements=None, job=None):
    root=jb_root(source);reject_links(root)
    try:
        archive,header,appended,patches,total=plan(root,additions,replacements)
    except CapacityError:
        from .repack import build as rebuild
        return rebuild(root,additions,output,replacements,job)
    output=safe_output(output,[root])
    if output.exists():raise ValueError('Output already exists')
    output.parent.mkdir(parents=True,exist_ok=True)
    required=sum(p.stat().st_size for p in root.rglob('*') if p.is_file())+total-sum(p['size'] for p in archive.parts)
    if shutil.disk_usage(output.parent).free<required:raise ValueError('Insufficient disk space for copied JB')
    before=inventory(root)
    pending=output.parent/('.asset_build_'+uuid.uuid4().hex)
    if not pending.resolve().is_relative_to(OUTPUT.resolve()):raise ValueError('Unsafe temporary output')
    try:
        copied=0
        def copy_file(src,dst):
            nonlocal copied
            with open(src,'rb') as incoming,open(dst,'xb') as outgoing:
                while True:
                    if job:job.check()
                    chunk=incoming.read(2*1024*1024)
                    if not chunk:break
                    outgoing.write(chunk);copied+=len(chunk)
                    if job:job.progress(copied,required,'Copying JB files')
            shutil.copystat(src,dst)
            return dst
        shutil.copytree(root,pending,copy_function=copy_file)
        destination=pending/archive.path.relative_to(root)
        with (destination/'0A').open('r+b') as f:f.write(header)
        last=destination/archive.parts[-1]['name'];base=sum(p['size'] for p in archive.parts[:-1])
        with last.open('r+b') as f:
            for offset,data,name in appended:
                if job:job.check()
                f.seek(offset-base);f.write(data)
            f.truncate(total-base)
        # Existing replacements can span banks.
        for offset,data in patches:
            remaining=len(data);position=0;part_base=0
            for part in archive.parts:
                end=part_base+part['size']
                if part_base<=offset<end and remaining:
                    n=min(remaining,end-offset)
                    with (destination/part['name']).open('r+b') as f:f.seek(offset-part_base);f.write(data[position:position+n])
                    offset+=n;position+=n;remaining-=n
                part_base=end
            if remaining:raise ValueError('Incomplete replacement write')
        result=Archive(destination);new_by_hash={e['hash']:e for e in result.entries}
        for i,e in enumerate(archive.entries):
            if job:job.check();job.progress(i,len(archive.entries),'Verifying preserved archive entries')
            new=new_by_hash[e['hash']]
            replacement=next((v for n,v in (replacements or {}).items() if replacement_hash(n)==e['hash']),None)
            if replacement is None:
                if new['offset']!=e['offset'] or new['size']!=e['size'] or checksum(result.chunks(new))!=checksum(archive.chunks(e)):
                    raise ValueError('Existing entry verification failed')
            else:
                replacement_name=next(n for n in replacements if replacement_hash(n)==e['hash'])
                content=replacement if replacement_name.lower().endswith('.cdf') else meaningful_iff(replacement)
                span=e['size'] if new['offset']==e['offset'] else new['size']
                expected=hashlib.sha256(content+b'\0'*(span-len(content))).hexdigest()
                if checksum(result.chunks({**new,'size':span}))!=expected:
                    raise ValueError('Replacement verification failed')
        for offset,data,name in appended:
            e=new_by_hash[replacement_hash(name) if name in (replacements or {}) else hash_name(name)]
            if e['content_size']!=len(data) or result.read(e)[:len(data)]!=data:raise ValueError('New asset verification failed')
        if inventory(root)!=before:raise ValueError('Source changed during build')
        report={'schema':1,'added_assets':list(additions),'replaced_assets':list(replacements or {}),
                'verified_existing_entry_count':len(archive.entries),
                'unchanged_entry_count':len(archive.entries)-len(replacements or {}),'source_unchanged':True,
                'runtime_verified':False,'archive_growth_bytes':total-sum(p['size'] for p in archive.parts)}
        import json
        (pending/'asset_build_report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
        os.rename(pending,output)
        return report
    except BaseException:
        if pending.exists():shutil.rmtree(pending)
        raise


def validate_plan(source, additions, replacements=None):
    try:
        plan(source,additions,replacements)
        return 'append'
    except CapacityError:
        from .repack import plan as rebuild_plan
        rebuild_plan(source,additions,replacements)
        return 'repack'
