"""Observed English TXT loc-system table; append isolated ASCII literal IDs.

IDs are tagged odd numeric tokens, not the CRCs used by archive names. Literal
characters use 0x01/ASCII pairs; existing translations and token streams stay opaque.
"""
import struct

from .binary import Binary


def entries(data):
    b=Binary(data)
    if b.u32(0)!=0xe33e3b9c:raise ValueError('Not an observed loc-system table')
    count=b.u32(4);table=b.relative(8)
    if table!=32 or not 1<=count<=1000000:raise ValueError('Unsupported loc-system table layout')
    end=table+count*8;b.slice(table,count*8);rows=[];previous=-1;terminated=set()
    for i in range(count):
        at=table+i*8;key=b.u32(at)
        # Observed final invalid-ID sentinel carries an even opaque word, not a
        # usable string pointer. Preserve it without interpreting its target.
        if key==0xffffffff:
            if i!=count-1 or b.u32(at+4)&1:raise ValueError('Invalid loc-system sentinel')
            rows.append((key,None));previous=key;continue
        target=b.relative(at+4)
        if key<=previous or not key&1:raise ValueError('Unsorted or invalid loc-system ID')
        if not end<=target<len(data) or target%2:raise ValueError('Invalid loc-system string pointer')
        if target not in terminated:
            stop=data.find(bytes(2),target)
            while stop>=0 and stop%2:stop=data.find(bytes(2),stop+1)
            if stop<0:raise ValueError('Unterminated loc-system token stream')
            terminated.add(target)
        rows.append((key,target));previous=key
    if rows[-1][0]!=0xffffffff:raise ValueError('Missing observed loc-system sentinel')
    return rows


def tokens(data,key):
    table=dict(entries(data))
    if key not in table:raise ValueError('Missing loc-system ID')
    b=Binary(data);start=table[key]
    if start is None:raise ValueError('Reserved loc-system ID has no string')
    end=start
    while b.slice(end,2)!=bytes(2):end+=2
    return b.slice(start,end-start+2)


def add_literal(data,key,text):
    rows=entries(data)
    if type(key) is not int or not 0<key<0xffffffff or not key&1:raise ValueError('Literal ID must be a non-reserved odd token')
    if key in dict(rows):raise ValueError('Loc-system ID already exists')
    if not isinstance(text,str) or not 1<=len(text)<=4096 or any(c!='\n' and not 32<=ord(c)<=126 for c in text):raise ValueError('Only observed ASCII/newline literals are writable')
    old_end=32+len(rows)*8;pool=data[old_end:]
    if len(pool)%2:raise ValueError('Unaligned loc-system string pool')
    new_end=old_end+8;literal=b''.join(bytes((1,ord(c))) for c in text)+bytes(2)
    targets=[(old_key,None if target is None else target+8) for old_key,target in rows]+[(key,new_end+len(pool))]
    sentinel=Binary(data).u32(old_end-4) if rows[-1][1] is None else None
    targets.sort();out=bytearray(data[:32]);struct.pack_into('>I',out,4,len(targets))
    for ident,target in targets:
        field=len(out)+4;out.extend(struct.pack('>II',ident,sentinel if target is None else target-field+1))
    out.extend(pool);out.extend(literal);result=bytes(out)
    check=dict(entries(result))
    if result[new_end:new_end+len(pool)]!=pool or any(check[k]!=(None if p is None else p+8) for k,p in rows):raise ValueError('Loc-system preservation failed')
    if tokens(result,key)!=literal:raise ValueError('Literal round trip failed')
    return result


def validate_extension(source,result):
    old,new=entries(source),entries(result);old_end=32+len(old)*8;new_end=32+len(new)*8
    if len(new)!=len(old)+1 or source[:4]!=result[:4] or source[8:32]!=result[8:32]:raise ValueError('Localization growth must only extend the observed table')
    pool=source[old_end:];shift=new_end-old_end;new_map=dict(new)
    if result[new_end:new_end+len(pool)]!=pool:raise ValueError('Localization growth changes existing token bytes')
    for key,target in old:
        if key not in new_map or new_map[key]!=(None if target is None else target+shift):raise ValueError('Localization growth changes existing ID mapping')
    if old[-1][1] is None and source[old_end-4:old_end]!=result[new_end-4:new_end]:raise ValueError('Localization growth changes opaque sentinel')
    old_keys={key for key,_ in old}
    key=next(key for key,_ in new if key not in old_keys)
    raw=tokens(result,key)
    if any(raw[i]!=1 or (raw[i+1]!=10 and not 32<=raw[i+1]<=126) for i in range(0,len(raw)-2,2)):
        raise ValueError('New localization entry uses an unsupported token encoding')
