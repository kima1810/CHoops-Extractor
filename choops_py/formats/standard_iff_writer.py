"""Preserve all logical offsets; rebuild only changed stored blocks."""
import struct
from .standard_iff import StandardIFF
from .compression import decode, encode_like
from .binary import Binary
from ..core.errors import ToolError

def record(iff, selector, expected_type=None):
    if isinstance(selector,int):
        candidates=[r for r in iff.records if r['index']==selector and (not expected_type or r['type']==expected_type)]
        if len(candidates)!=1:raise ToolError('ambiguous_subfile','Select a unique record index and type')
        return candidates[0]
    selector = str(selector)
    candidates = [r for r in iff.records if (str(r['index'])==selector or r['name']==selector or f"{r['name']}.{r['type'].lower()}"==selector) and (not expected_type or r['type']==expected_type)]
    if len(candidates)!=1: raise ToolError('ambiguous_subfile','Select a unique name/index and type')
    return candidates[0]

def record_blocks(iff, rec):
    blocks = []
    for index,start,end in iff.spans(rec):
        block=iff.blocks[index]
        logical=decode(iff.raw[block['start']:block['start']+block['size']],block['logical_size'])
        blocks.append((index,start,end,logical[start:end]))
    return blocks

def replace_records(iff, changes):
    if iff.record_table != 32+len(iff.blocks)*32:
        raise ToolError('extended_iff_read_only','Extended IFF header metadata is not yet safe to rewrite')
    """changes maps record index to complete block slices (same logical size).

    Physical block positions/lengths, fileLength and H7A lengths are recomputed.
    Internal record offsets stay unchanged. The name table is moved byte-exactly.
    Only identified trailing zero padding may absorb compressed growth.
    """
    changed = {}; touched = []
    for index, replacements in changes.items():
        rec=record(iff,index); spans=record_blocks(iff,rec)
        if len(spans)!=len(replacements): raise ToolError('block_count_mismatch','Replacement must preserve each subfile block')
        for (block_index,start,end,old),new in zip(spans,replacements):
            if len(old)!=len(new): raise ToolError('payload_size_mismatch','Replacement changes logical subfile size')
            if old==new: continue
            for other in iff.records:
                if other['index']==rec['index']: continue
                for bj,bs,be in iff.spans(other):
                    if bj==block_index and start<be and bs<end: raise ToolError('aliased_subfile','Replacement overlaps another subfile')
            for bj,bs,be in touched:
                if bj==block_index and start<be and bs<end: raise ToolError('overlapping_edits','Changes overlap')
            touched.append((block_index,start,end))
            if block_index not in changed:
                block=iff.blocks[block_index];changed[block_index]=bytearray(decode(iff.raw[block['start']:block['start']+block['size']],block['logical_size']))
            changed[block_index][start:end]=new
    if not changed: return iff.raw
    header=bytearray(iff.raw[:iff.header_size]);payload=bytearray();cursor=iff.header_size
    for block in sorted(iff.blocks,key=lambda b:b['start']):
        if block['start']<cursor: raise ToolError('overlapping_blocks','Stored block ranges overlap')
        payload.extend(iff.raw[cursor:block['start']])
        original=iff.raw[block['start']:block['start']+block['size']]
        replacement=bytes(changed[block['index']]) if block['index'] in changed else None
        stored=encode_like(original,replacement) if replacement is not None and block['compressed'] else replacement if replacement is not None else original
        new_start=iff.header_size+len(payload)
        entry=32+block['index']*32
        struct.pack_into('>I',header,entry+20,new_start);struct.pack_into('>I',header,entry+24,len(stored))
        payload.extend(stored);cursor=block['start']+block['size']
    payload.extend(iff.raw[cursor:iff.file_length]);new_end=len(header)+len(payload)
    struct.pack_into('>I',header,8,new_end)
    trailer=iff.raw[iff.file_length:];meaningful=0
    if trailer[:4]==bytes.fromhex('aa171516'):
        meaningful=8+Binary(trailer).u32(4,'<')
        if meaningful>len(trailer):raise ToolError('invalid_name_table','Name table exceeds trailer')
    elif any(trailer):meaningful=len(trailer)
    core=bytes(header)+bytes(payload)+trailer[:meaningful]
    if len(core)>len(iff.raw):
        raise ToolError('archive_extent_capacity_exceeded',f'Rebuilt IFF needs {len(core)} bytes; original extent is {len(iff.raw)}. Size-changing archive relocation is blocked.')
    padding=trailer[meaningful:]
    if any(padding):raise ToolError('unknown_trailer','Cannot resize unknown trailing bytes')
    result=core+b'\0'*(len(iff.raw)-len(core))
    rebuilt=StandardIFF(result)
    for index,logical in changed.items():
        b=rebuilt.blocks[index]
        if decode(result[b['start']:b['start']+b['size']],b['logical_size'])!=bytes(logical):raise ToolError('writer_validation_failed','Rebuilt logical block mismatch')
    return result



def replace_records_expanding(iff,changes):
    if iff.record_table != 32+len(iff.blocks)*32:
        raise ToolError('extended_iff_read_only','Extended IFF header metadata is not yet safe to rewrite')
    localization=[index for index in changes if record(iff,index)['type_hash']==0xa423b39e]
    if localization:
        # Localization is loaded during startup. Do not append another complete
        # table to its compressed heap: that experimental representation is
        # implicated by the native startup failure despite Python round trips.
        return _replace_localization(iff,changes)
    """Keep original logical addresses; append only enlarged or aliased slices.

    Complete TXTR/SCNE slices carry their own local relative pointers. Unchanged
    records, heap bytes and unknown ranges remain at their original addresses.
    """
    from .compression import encode_greedy
    original_blocks={b['index']:decode(iff.raw[b['start']:b['start']+b['size']],b['logical_size']) for b in iff.blocks}
    mutable={i:bytearray(data) for i,data in original_blocks.items()};offset_updates={};expected={}
    for index,parts in changes.items():
        rec=record(iff,index);spans=list(iff.spans(rec))
        if len(spans)!=len(parts):raise ToolError('block_count_mismatch',rec['name'])
        for (block,start,end),new in zip(spans,parts):
            old=original_blocks[block][start:end]
            if new==old:continue
            shared=any(other['index']!=index and any(b==block and start<e and s<end for b,s,e in iff.spans(other)) for other in iff.records)
            if len(new)>len(old) or shared:
                if rec['type'] not in ('TXTR','SCNE','NAME','CDAN','LAYT','ROST','AUDO'):raise ToolError('unsupported_record_growth',rec['name']+'.'+rec['type'])
                alignment=128 if iff.blocks[block]['fields'][0]==0x411536D5 else 16
                target=(len(mutable[block])+alignment-1)&~(alignment-1)
                mutable[block]+=b'\0'*(target-len(mutable[block]));mutable[block]+=new
                offset_updates[index,block]=target
            else:
                mutable[block][start:start+len(new)]=new
                # Unreferenced tail remains intact; no unrelated bytes are erased.
            expected[index,block]=bytes(new)
    if not expected:return iff.raw
    # GPU resources are relocatable slices, but their RSX base addresses must
    # remain 128-byte aligned. Repack them once instead of retaining obsolete
    # images followed by an appended replacement for every resized texture.
    # Unknown records pin the prefix: their internal pointer semantics are not
    # established and their addresses must not change.
    for block in iff.blocks:
        bi=block['index']
        if block['fields'][0]!=0x411536D5 or not any(b==bi for _,b in expected):continue
        spans=[(rec,start,end) for rec in iff.records for b,start,end in iff.spans(rec) if b==bi]
        if not spans:continue
        pinned=max([end for rec,start,end in spans if rec['type'] not in ('TXTR','SCNE')]+[min(start for _,start,_ in spans)])
        packed=bytearray(original_blocks[bi][:pinned]);aliases={}
        for rec,start,end in sorted(spans,key=lambda row:(row[1],row[0]['index'])):
            key=(rec['index'],bi);wanted=expected.get(key,original_blocks[bi][start:end])
            if end<=pinned and len(wanted)<=end-start:
                target=start;packed[start:start+len(wanted)]=wanted
            else:
                alias=(start,wanted)
                if alias in aliases:target=aliases[alias]
                else:
                    target=(len(packed)+127)&~127
                    packed+=b'\0'*(target-len(packed))+wanted;aliases[alias]=target
            offset_updates[key]=target
        mutable[bi]=packed
    header=bytearray(iff.raw[:iff.header_size]);b=Binary(header)
    for (index,block),target in offset_updates.items():
        field=iff.record_table+index*4;descriptor=b.relative(field)
        struct.pack_into('>I',header,descriptor+12+block*4,target)
    payload=bytearray();cursor=iff.header_size
    for block in sorted(iff.blocks,key=lambda b:b['start']):
        if len(mutable[block['index']])>512*1024*1024:raise ToolError('oversized_logical_block','Expanded logical block exceeds limit')
        payload+=iff.raw[cursor:block['start']]
        logical=bytes(mutable[block['index']]);old=original_blocks[block['index']]
        stored=iff.raw[block['start']:block['start']+block['size']]
        if logical!=old:stored=encode_greedy(stored,logical) if block['compressed'] else logical
        entry=32+block['index']*32
        struct.pack_into('>I',header,entry+12,len(logical));struct.pack_into('>II',header,entry+20,iff.header_size+len(payload),len(stored))
        payload+=stored;cursor=block['start']+block['size']
    payload+=iff.raw[cursor:iff.file_length];end=iff.header_size+len(payload)
    struct.pack_into('>I',header,8,end)
    trailer=iff.raw[iff.file_length:];meaningful=0
    if trailer[:4]==bytes.fromhex('aa171516'):meaningful=8+Binary(trailer).u32(4,'<')
    elif any(trailer):raise ToolError('unknown_trailer','Unclassified IFF trailer')
    if meaningful>len(trailer) or any(trailer[meaningful:]):raise ToolError('unknown_trailer','Unclassified name-table padding')
    result=bytes(header)+bytes(payload)+trailer[:meaningful]
    if len(result)<len(iff.raw):result+=b'\0'*(len(iff.raw)-len(result))
    check=StandardIFF(result)
    checked_blocks={b['index']:decode(result[b['start']:b['start']+b['size']],b['logical_size']) for b in check.blocks}
    for rec in iff.records:
        old_spans=list(iff.spans(rec));new_spans=list(check.spans(check.records[rec['index']]))
        for (block,start,stop),(new_block,new_start,new_stop) in zip(old_spans,new_spans):
            wanted=expected.get((rec['index'],block),original_blocks[block][start:stop])
            raw=checked_blocks[new_block]
            if raw[new_start:new_start+len(wanted)]!=wanted:raise ToolError('writer_validation_failed','Record bytes differ after expansion')
    return result


def _replace_localization(iff,changes):
    """Extend the observed sole English resource at offset zero, without H7A.

    The native loader's equal stored/logical-size branch reads this block
    directly. Keep the original outer metadata and NAME trailer; reject layouts
    for which compacting would relocate any other resource or unknown heap data.
    """
    from .loc_system import validate_extension
    if len(iff.records)!=1 or len(iff.blocks)!=1 or set(changes)!={0} or len(changes[0])!=1:
        raise ToolError('unsupported_record_growth','Localization requires a sole complete block')
    rec=iff.records[0];block=iff.blocks[0]
    if rec['type_hash']!=0xa423b39e or rec['offsets']!=[0]:
        raise ToolError('unsupported_record_growth','Localization requires a sole complete block at offset zero')
    old=decode(iff.raw[block['start']:block['start']+block['size']],block['logical_size'])
    new=bytes(changes[0][0])
    if new==old:return iff.raw
    try:validate_extension(old,new)
    except ValueError as error:raise ToolError('unsafe_localization_growth',str(error)) from error
    if len(new)>512*1024*1024:raise ToolError('oversized_logical_block','Expanded localization exceeds limit')
    trailer=iff.raw[iff.file_length:];meaningful=0
    if trailer[:4]==bytes.fromhex('aa171516'):meaningful=8+Binary(trailer).u32(4,'<')
    if meaningful>len(trailer) or any(trailer[meaningful:]):
        raise ToolError('unknown_trailer','Unclassified localization trailer')
    header=bytearray(iff.raw[:iff.header_size]);end=block['start']+len(new)
    suffix=iff.raw[block['start']+block['size']:iff.file_length]
    struct.pack_into('>I',header,8,end+len(suffix))
    struct.pack_into('>I',header,44,len(new))
    struct.pack_into('>I',header,56,len(new))
    result=bytes(header)+iff.raw[iff.header_size:block['start']]+new+suffix+trailer[:meaningful]
    check=StandardIFF(result)
    if check.records!=iff.records or record_blocks(check,check.records[0])[0][3]!=new:
        raise ToolError('writer_validation_failed','Compact localization differs after writing')
    return result


def repair_compression(iff):
    """Repair old tool streams while retaining every decoded byte and offset."""
    from .compression import game_compatible,encode_greedy
    header=bytearray(iff.raw[:iff.header_size]);payload=bytearray();cursor=iff.header_size;expected={};repaired=[]
    for block in sorted(iff.blocks,key=lambda b:b['start']):
        payload+=iff.raw[cursor:block['start']]
        stored=iff.raw[block['start']:block['start']+block['size']]
        if block['compressed'] and not game_compatible(stored):
            logical=decode(stored,block['logical_size']);expected[block['index']]=logical
            stored=encode_greedy(stored,logical)
            if not game_compatible(stored):raise ToolError('compression_verification_failed','Repaired stream is not game compatible')
            repaired.append(block['index'])
        entry=32+block['index']*32
        struct.pack_into('>II',header,entry+20,iff.header_size+len(payload),len(stored))
        payload+=stored;cursor=block['start']+block['size']
    if not repaired:return iff.raw,[]
    payload+=iff.raw[cursor:iff.file_length];end=iff.header_size+len(payload);struct.pack_into('>I',header,8,end)
    result=bytes(header)+bytes(payload)+iff.raw[iff.file_length:]
    check=StandardIFF(result)
    for index,wanted in expected.items():
        b=check.blocks[index]
        if decode(result[b['start']:b['start']+b['size']],b['logical_size'])!=wanted:raise ToolError('writer_validation_failed','Compression repair changed decoded bytes')
    return result,repaired
