"""Validated internal record cloning for two-block CDF texture banks."""
import struct
import zlib
from .binary import Binary
from .cdf_backed_iff import CDFPair
from .compression import decode


def replace_texture_records(iff,cdf,changes):
    """Rebuild compressed logo spans and adjust fixed logical slot strides."""
    from .compression import encode_greedy,game_compatible
    pair=CDFPair(iff,cdf);b=Binary(iff);header=bytearray(iff)
    sizes=[b.u32(52),b.u32(84)];align=[b.u32(48),b.u32(80)]
    if b.u32(16)!=2 or not all(sizes) or any(a not in (16,32,64,128,256) for a in align):
        raise ValueError('Unsupported CDF texture bank layout')
    old_strides=[(n+a-1)//a*a for n,a in zip(sizes,align)]
    slots={}
    for r in pair.records:
        words=r['primary_words']
        if r['type']!='TXTR' or words[2]!=2 or any(words[3+j]%old_strides[j] for j in range(2)):
            raise ValueError('Unclassified CDF texture slots')
        slot=words[3]//old_strides[0]
        if slot!=words[4]//old_strides[1]:raise ValueError('CDF texture slots disagree')
        slots[r['index']]=slot
    if len(set(slots.values()))!=len(slots):raise ValueError('Shared CDF texture slots')
    for index,parts in changes.items():
        if not 0<=index<len(pair.records) or len(parts)!=2:raise ValueError('Invalid CDF texture replacement')
        sizes=[max(n,len(p)) for n,p in zip(sizes,parts)]
    strides=[(n+a-1)//a*a for n,a in zip(sizes,align)]
    if max(strides)>128*1024*1024:raise ValueError('CDF texture slot exceeds limit')
    table=b.relative(32);out=bytearray();expected={}
    for r in pair.records:
        rec=b.relative(104+r['index']*4);desc=b.relative(table+r['index']*4)
        struct.pack_into('>II',header,rec+12,slots[r['index']]*strides[0],slots[r['index']]*strides[1])
        for j,key in enumerate(('header','payload')):
            raw=cdf[r[key+'_offset']:r[key+'_offset']+r[key+'_length']]
            logical=changes[r['index']][j] if r['index'] in changes else decode(raw)
            if r['index'] in changes or not game_compatible(raw):
                raw=encode_greedy(raw,logical) if raw[:4]==bytes.fromhex('0e4837c3') else logical
            struct.pack_into('>II',header,desc+j*8,len(out),len(raw));out+=raw
            expected[r['index'],key]=logical
    for j in range(2):
        struct.pack_into('>I',header,40+j*32+12,sizes[j])
        struct.pack_into('>I',header,40+j*32+20,b.u32(4)+(strides[0] if j else 0))
        struct.pack_into('>I',header,40+j*32+24,sizes[j])
    result=bytes(header);payload=bytes(out);check=CDFPair(result,payload)
    for r in check.records:
        for key in ('header','payload'):
            if decode(payload[r[key+'_offset']:r[key+'_offset']+r[key+'_length']])!=expected[r['index'],key]:
                raise ValueError('CDF texture rebuild changed pixels or headers')
    return result,payload


def name_trailer(records):
    count=len(records);body=bytearray(8+count*12)
    struct.pack_into('<II',body,0,count,5)
    for i,record in enumerate(records):
        field=8+i*4;descriptor=8+count*4+i*8
        struct.pack_into('<I',body,field,descriptor-field+1)
        for j,text in enumerate((record['name'],record['type'])):
            pointer=descriptor+j*4
            struct.pack_into('<I',body,pointer,len(body)-pointer+1)
            body+=text.encode('utf-16-le')+b'\0\0'
    return bytes.fromhex('aa171516')+struct.pack('<I',len(body))+body


def clone_texture_record(iff,cdf,template,new_name):
    """Preserve every old CDF byte and append independent compressed spans."""
    pair=CDFPair(iff,cdf);b=Binary(iff)
    if b.u32(4)!=b.u32(8) or b.u32(12)!=0 or b.u32(16)!=2 or b.relative(20)!=40:
        raise ValueError('Unsupported CDF metadata layout')
    if not new_name or not new_name.isascii() or any(not(c.isalnum() or c=='_') for c in new_name):
        raise ValueError('Use an ASCII texture record name')
    found=[r for r in pair.records if r['name']==template]
    if len(found)!=1 or found[0]['type']!='TXTR':raise ValueError('Choose one named texture template')
    count=len(pair.records)
    expected_end=104+count*44+len(pair.cdf_name.encode('utf-16-be'))+2
    if b.relative(32)!=104+count*24 or b.relative(36)!=104+count*44 or b.u32(4)!=expected_end:
        raise ValueError('Unclassified CDF metadata regions')
    record=found[0];identity=zlib.crc32(new_name.encode('ascii'))&0xffffffff
    if any(r['name']==new_name or r['primary_words'][0]==identity for r in pair.records):
        raise ValueError('Texture record name/hash already exists')
    logical_sizes=(b.u32(40+12),b.u32(72+12))
    alignments=(b.u32(40+8),b.u32(72+8))
    if any(a not in (16,32,64,128,256) for a in alignments):raise ValueError('Unsupported CDF block alignment')
    strides=tuple((n+a-1)//a*a for n,a in zip(logical_sizes,alignments))
    if not all(0<stride<=128*1024*1024 for stride in strides):raise ValueError('Unsupported CDF logical strides')
    slots=[]
    for r in pair.records:
        words=r['primary_words']
        if r['type']!='TXTR' or words[2]!=2 or words[3]%strides[0] or words[4]%strides[1]:
            raise ValueError('Unclassified CDF record layout')
        if words[3]//strides[0]!=words[4]//strides[1]:raise ValueError('CDF logical slots disagree')
        slots.append(words[3]//strides[0])
    if len(slots)!=len(set(slots)):raise ValueError('Shared CDF logical slots')
    slot=max(slots)+1;output=bytearray(cdf);spans=[]
    for prefix,stride in zip(('header','payload'),logical_sizes):
        raw=cdf[record[prefix+'_offset']:record[prefix+'_offset']+record[prefix+'_length']]
        decode(raw,stride)
        spans.extend((len(output),len(raw)));output+=raw
    cloned={**record,'name':new_name,'primary_words':[identity,*record['primary_words'][1:3],slot*strides[0],slot*strides[1]],
            'header_offset':spans[0],'header_length':spans[1],'payload_offset':spans[2],'payload_length':spans[3]}
    records=sorted(pair.records+[cloned],key=lambda r:r['primary_words'][0]);count=len(records)
    if count>8192:raise ValueError('CDF record count exceeds limit')
    desc_table=104+count*24;filename=104+count*44
    name=pair.cdf_name.encode('utf-16-be')+b'\0\0';end=filename+len(name)
    metadata=bytearray(end);metadata[:104]=iff[:104]
    struct.pack_into('>II',metadata,4,end,end);struct.pack_into('>I',metadata,24,count)
    struct.pack_into('>i',metadata,32,desc_table-32+1);struct.pack_into('>i',metadata,36,filename-36+1)
    metadata[filename:]=name
    for offset,start in ((40,end),(72,end+strides[0])):struct.pack_into('>I',metadata,offset+20,start)
    for i,r in enumerate(records):
        pointer=104+i*4;descriptor=104+count*4+i*20
        struct.pack_into('>i',metadata,pointer,descriptor-pointer+1)
        struct.pack_into('>5I',metadata,descriptor,*r['primary_words'])
        pointer=desc_table+i*4;descriptor=desc_table+count*4+i*16
        struct.pack_into('>i',metadata,pointer,descriptor-pointer+1)
        struct.pack_into('>4I',metadata,descriptor,r['header_offset'],r['header_length'],r['payload_offset'],r['payload_length'])
    rebuilt=bytes(metadata)+name_trailer(records);payload=bytes(output)
    check=CDFPair(rebuilt,payload);by_name={r['name']:r for r in check.records}
    for old in pair.records:
        new=by_name[old['name']]
        for field in ('primary_words','header_offset','header_length','payload_offset','payload_length'):
            if old[field]!=new[field]:raise ValueError('Preserved CDF record changed')
    if payload[:len(cdf)]!=cdf:raise ValueError('Preserved CDF bytes changed')
    return rebuilt,payload
