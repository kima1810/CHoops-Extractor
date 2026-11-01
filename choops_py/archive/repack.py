"""Relocate the complete archive body and rebuild sorted TOC/split-bank metadata."""
import hashlib
import json
import os
import re
import shutil
import struct
import uuid
from contextlib import ExitStack
from pathlib import Path
from .usrdir_reader import Archive
from .hash_names import hash_name,replacement_hash
from .manifests import build_destination as safe_output
from .build_copy import jb_root,inventory
from .build_io import BankWriter,CHUNK,verify_body,verify_files
from .layouts import pack_row
from .add_assets import meaningful_iff,validate_payload,asset_payload
from ..core.paths import reject_links


def plan(source, additions, replacements=None, job=None):
    archive=Archive(source);archive.require_writable();replacements=replacements or {}
    if not additions and not replacements:raise ValueError('No asset changes supplied')
    by_hash={e['hash']:e for e in archive.entries}
    if len(by_hash)!=len(archive.entries) or any(e['toc_flags'] or e['content_size'] is None for e in archive.entries):
        raise ValueError('Unclassified/duplicate source TOC fields block repacking')
    first=min(e['offset'] for e in archive.entries);old_total=sum(p['size'] for p in archive.parts)
    end=24+len(archive.parts)*16+len(archive.entries)*16
    from .build_io import archive_header
    old_header=archive_header(archive)
    if any(struct.unpack_from('>I',old_header,24+i*16+4)[0] for i in range(len(archive.parts))):raise ValueError('Unclassified bank descriptor flags block repacking')
    contents={};trimmed={}
    supplied={**additions,**replacements}
    for position,(name,data) in enumerate(supplied.items()):
        if job:job.check();job.progress(position,len(supplied),"Validating added archive assets")
        allowed_ext=r'iff|cdf|bin' if name in replacements else r'iff|cdf'
        if not re.fullmatch(r'[A-Za-z0-9_-]+\.(?:'+allowed_ext+r')',name,re.IGNORECASE):raise ValueError('Unsupported asset name')
        h=replacement_hash(name) if name in replacements else hash_name(name)
        if (name in additions and h in by_hash) or (name in replacements and h not in by_hash):raise ValueError('New/replacement asset identity conflict')
        if h in contents:raise ValueError('Duplicate asset hash')
        cache=trimmed.get(id(data))
        if cache is None:
            cache=asset_payload(name,data,supplied);trimmed[id(data)]=cache
        if len(cache)>128*1024*1024:raise ValueError('Asset exceeds insertion limit')
        contents[h]=(name,cache)
    alignment=archive.alignment
    bank_limit=max(p['size'] for p in archive.parts)
    extra=sum((len(data)+alignment-1)//alignment*alignment for _,data in contents.values())
    bank_count=len(archive.parts)
    for _ in range(16):
        start=max(first,(24+bank_count*16+(len(archive.entries)+len(additions))*16+alignment-1)//alignment*alignment)
        total=(start+old_total-first+extra+2047)//2048*2048
        count=(total+bank_limit-1)//bank_limit
        if count==bank_count:break
        bank_count=count
    else:raise ValueError('Bank layout did not converge')
    if not 1<=bank_count<=256:raise ValueError('Too many archive banks')
    new_toc_end=24+bank_count*16+(len(archive.entries)+len(additions))*16
    if start!=first and any(old_header[end:first]):
        raise ValueError('Cannot relocate unclassified header bytes; header growth requires verified zero padding')
    if any(old_header[end:min(first,max(end,new_toc_end))]):
        raise ValueError('Expanded TOC overlaps unclassified header bytes')
    bank_names=[p['name'] for p in archive.parts]
    if any(name!=f"{i//26}{chr(65+i%26)}" for i,name in enumerate(bank_names)):
        raise ValueError('Unknown source bank naming sequence')
    bank_names += [f"{i//26}{chr(65+i%26)}" for i in range(len(bank_names),bank_count)]
    sizes=[min(bank_limit,total-i*bank_limit) for i in range(bank_count)]
    delta=start-first;records=[]
    for e in archive.entries:records.append([e['hash'],(e['offset']+delta)//alignment,e['toc_flags'],e['stored_size']])
    cursor=start+old_total-first;appended=[]
    for h,(name,data) in contents.items():
        if name in replacements:next(r for r in records if r[0]==h)[1:]=[cursor//alignment,0,len(data)]
        else:records.append([h,cursor//alignment,0,len(data)])
        appended.append((cursor,data,name));cursor=(cursor+len(data)+alignment-1)//alignment*alignment
    records.sort(key=lambda r:r[0]);header=bytearray(start);header[:24]=old_header[:24]
    if start==first:header[end:first]=old_header[end:first]
    struct.pack_into('>I',header,8,bank_count);struct.pack_into('>I',header,16,len(records))
    for i,(name,size) in enumerate(zip(bank_names,sizes)):
        if size%2048 or len(name)>4:raise ValueError('Unsupported bank dimensions')
        reserved=struct.unpack_from('>I',old_header,24+i*16+4)[0] if i<len(archive.parts) else 0
        struct.pack_into('>II8s',header,24+i*16,size//2048,reserved,name.ljust(4,'\0').encode('utf-16-be'))
    for i,row in enumerate(records):pack_row(header,24+bank_count*16+i*16,row,archive.toc_layout)
    return archive,bytes(header),bank_names,sizes,delta,appended,total


def build(source, additions, output, replacements=None, job=None):
    root=jb_root(source);reject_links(root)
    before=inventory(root)
    arc,header,names,sizes,delta,appended,total=plan(root,additions,replacements,job)
    output=safe_output(output,[root])
    if output.exists():raise ValueError('Output already exists')
    output.parent.mkdir(parents=True,exist_ok=True)
    needed=sum(p['size'] for p in before.values())+total-sum(p['size'] for p in arc.parts)
    if shutil.disk_usage(output.parent).free<needed:raise ValueError('Insufficient disk space')
    pending=output.parent/('.archive_repack_'+uuid.uuid4().hex)
    safe_output(pending,[root])
    try:
        bank_set=set(p['name'] for p in arc.parts)
        def ignore(path,files):return bank_set if Path(path).resolve()==arc.path else set()
        def copy_file(src,dst):
            with open(src,'rb') as incoming,open(dst,'xb') as outgoing:
                while True:
                    if job:job.check()
                    data=incoming.read(2*1024*1024)
                    if not data:break
                    outgoing.write(data)
            shutil.copystat(src,dst);return dst
        shutil.copytree(root,pending,ignore=ignore,copy_function=copy_file)
        usr=pending/arc.path.relative_to(root)
        for name,size in zip(names,sizes):
            with (usr/name).open('xb') as f:f.truncate(size)
        with ExitStack() as handles:
            writer=BankWriter(usr,names,sizes,handles)
            writer.write(0,header)
            first=min(e['offset'] for e in arc.entries);entry={'offset':first,'size':sum(p['size'] for p in arc.parts)-first}
            cursor=first+delta;done=0
            for data in arc.chunks(entry,CHUNK):
                if job:job.check();job.progress(done,entry['size'],'Repacking preserved archive body')
                writer.write(cursor,data);cursor+=len(data);done+=len(data)
            for offset,data,name in appended:
                if job:job.check()
                writer.write(offset,data)
        result=Archive(usr);new_hash={e['hash']:e for e in result.entries}
        if result.read({'offset':0,'size':len(header)})!=header:raise ValueError('Rebuilt archive header differs')
        replaced_hashes={replacement_hash(name) for name in (replacements or {})}
        for i,e in enumerate(arc.entries):
            if job:job.check();job.progress(i,len(arc.entries),'Verifying repacked archive entries')
            new=new_hash[e['hash']]
            if e['hash'] not in replaced_hashes:
                if new['offset']!=e['offset']+delta or new['size']!=e['size']:
                    raise ValueError('Repacked entry preservation failed')
        for offset,data,name in appended:
            new=new_hash[replacement_hash(name) if name in (replacements or {}) else hash_name(name)]
            if new['content_size']!=len(data) or result.read(new)[:len(data)]!=data:raise ValueError('Added/replaced entry verification failed')
        verify_body(arc,result,delta=delta,job=job)
        verify_files(root,pending,arc,before,job)
        if inventory(root)!=before:raise ValueError('Source changed during repack')
        report={'schema':1,'method':'repack','added_assets':list(additions),'replaced_assets':list(replacements or {}),
                'verified_existing_entry_count':len(arc.entries),'unchanged_entry_count':len(arc.entries)-len(replacements or {}),
                'bank_count':len(names),'source_unchanged':True,'runtime_verified':False,
                'archive_growth_bytes':total-sum(p['size'] for p in arc.parts)}
        (pending/'asset_build_report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
        os.rename(pending,output);return report
    except BaseException:
        if pending.exists():shutil.rmtree(pending)
        raise
