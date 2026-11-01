"""Bounded PS3 SCNE text bindings and authored font-style properties.

Style entries serialize a 16-byte value followed by type/key/reserved words.
They are not key/value records starting at the type word. Runtime text callbacks
select by text-record name; bone names stay independent of those bindings.
"""
import math
import struct

from ..formats.binary import Binary


FONT = 0xbf045bdb
COLOR = (0x6109ea5a, 0x97de0310, 0x6814845a)
SHADOW = (0x53c67207, 0x661f09b0, 0x7dfc668b)


def _records(header):
    b=Binary(header);count=b.u32(0x4c)
    if count>4096:raise ValueError('SCNE text count exceeds limit')
    table=b.relative(0x50) if count else 0;b.slice(table,count*144)
    if count and table%16:raise ValueError('SCNE text table must be 16-byte aligned')
    records={}
    for i in range(count):
        at=table+i*144;name=b.utf16(b.relative(at+64),'be')
        if name in records:raise ValueError('Ambiguous SCNE text binding')
        style=b.relative(at+80);n=b.u32(style)
        if style%16:raise ValueError('SCNE text properties must be 16-byte aligned for native vector loads')
        if n>1024:raise ValueError('SCNE text property count exceeds limit')
        b.slice(style+16,n*32);properties={}
        for j in range(n):
            value=style+16+j*32;kind=b.u32(value+16);key=b.u32(value+20)
            if key in properties:raise ValueError('Ambiguous SCNE text property')
            properties[key]=(value,kind)
        records[name]=(at,properties)
    return b,records


def inspect_styles(header):
    b,records=_records(header);rows=[]
    for name,(at,properties) in records.items():
        font=None
        if FONT in properties:
            value,kind=properties[FONT]
            if kind!=3:raise ValueError('Font alias is not a string property')
            font=b.utf16(b.relative(value),'be') if b.u32(value) else ''
        def values(keys):
            return [b.u32(properties[k][0]) if k in properties and properties[k][1]==0 else None for k in keys]
        literal=None
        if 0x72b6694d in properties and 0x92f9b3f9 in properties:
            flags,flag_type=properties[0x72b6694d];vector,vector_type=properties[0x92f9b3f9]
            if flag_type==0 and vector_type==2 and b.u32(flags)&0x10:
                lo,hi=struct.unpack('>2f',b.slice(vector,8))
                if not all(math.isfinite(v) and 0<=v<=65535 and v==int(v) for v in (lo,hi)):raise ValueError('Invalid literal text ID vector')
                literal=(int(hi)<<16)|int(lo)|1
        alpha=properties.get(0xad44372a)
        alpha=struct.unpack('>f',b.slice(alpha[0],4))[0] if alpha and alpha[1]==1 else None
        rows.append(dict(binding=name,font=font,color=values(COLOR),shadow=values(SHADOW),literal_id=literal,alpha=alpha))
    return rows


def edit_styles(parts, changes):
    if len(parts)!=2:raise ValueError('Text styles require a split SCNE')
    b,records=_records(parts[0]);out=bytearray(parts[0]);names=set(records);report=[]
    for name,change in changes.items():
        if name not in records:raise ValueError('Unknown SCNE text binding '+name)
        if set(change)-{'font','binding','literal_id','align','alpha','color','max_width'}:raise ValueError('Unsupported SCNE text style edit')
        at,properties=records[name]
        if 'max_width' in change:
            width=change['max_width'];limit=properties.get(0x11fa397c);flags=properties.get(0x72b6694d)
            if type(width) not in (int,float) or not math.isfinite(width) or not 0<width<=4096:raise ValueError('Invalid native text width')
            if limit is None or limit[1]!=0 or flags is None or flags[1]!=0:raise ValueError('Missing native text width/flags properties')
            if any(sum(1 for _,props in records.values() if props.get(key)==properties[key])!=1 for key in (0x11fa397c,0x72b6694d)):raise ValueError('Native text width properties are shared')
            # Loader reads this numeric property through the generic conversion
            # accessor. Source stores an integer; preserve its serialized type.
            if width!=int(width):raise ValueError('Native text width must use whole authored units')
            struct.pack_into('>I',out,limit[0],int(width))
            struct.pack_into('>I',out,flags[0],b.u32(flags[0])|0x100)
        for option,keys,kind in [('alpha',(0xad44372a,),1),('color',COLOR,0)]:
            if option not in change:continue
            values=[change[option]] if option=='alpha' else change[option]
            if not isinstance(values,(list,tuple)) or len(values)!=len(keys):raise ValueError('Invalid text '+option)
            if option=='alpha':
                if any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1 for v in values):raise ValueError('Invalid text alpha')
            elif any(type(v) is not int or not 0<=v<=255 for v in values):raise ValueError('Invalid text color')
            for key,value in zip(keys,values):
                prop=properties.get(key)
                if prop is None or prop[1]!=kind:raise ValueError('Missing typed text '+option+' property')
                if sum(1 for _,props in records.values() if props.get(key)==prop)!=1:raise ValueError('Text '+option+' property is shared')
                struct.pack_into('>f' if kind==1 else '>I',out,prop[0],value)
        for option in ('font','binding'):
            if option not in change:continue
            value=change[option]
            if not isinstance(value,str) or not 1<=len(value)<=128 or any(ord(c)<32 for c in value):raise ValueError('Invalid SCNE text string')
            if option=='font':
                if FONT not in properties or properties[FONT][1]!=3:raise ValueError('Missing string font property')
                field=properties[FONT][0]
                if sum(1 for _,props in records.values() if FONT in props and props[FONT][0]==field)!=1:raise ValueError('Font property is shared by another text record')
            else:
                if value in names and value!=name:raise ValueError('SCNE text binding already exists')
                names.discard(name);names.add(value);field=at+64
            out.extend(bytes((-len(out))%4));target=len(out);out.extend(value.encode('utf-16-be')+bytes(2))
            struct.pack_into('>I',out,field,target-field+1)
        if 'literal_id' in change or 'align' in change:
            flags=properties.get(0x72b6694d)
            if flags is None or flags[1]!=0:raise ValueError('Missing integer text flags')
            if sum(1 for _,props in records.values() if props.get(0x72b6694d)==flags)!=1:raise ValueError('Text flags are shared by another record')
            value=struct.unpack_from('>I',out,flags[0])[0]
            if 'literal_id' in change:
                key=change['literal_id'];vector=properties.get(0x92f9b3f9)
                if type(key) is not int or not 0<key<0xffffffff or not key&1:raise ValueError('Invalid literal text ID')
                if vector is None or vector[1]!=2:raise ValueError('Missing literal ID vector')
                if sum(1 for _,props in records.values() if props.get(0x92f9b3f9)==vector)!=1:raise ValueError('Literal vector is shared by another record')
                struct.pack_into('>2f',out,vector[0],key&0xffff,key>>16);value|=0x10
            if 'align' in change:
                if change['align']!='center':raise ValueError('Only confirmed center alignment is writable')
                value=(value&~0x30000)|0x30000
            struct.pack_into('>I',out,flags[0],value)
        report.append(dict(source=name,**change))
    if len(out)>len(parts[0]):out.extend(bytes((-len(out))%4))
    result=[bytes(out),parts[1]]
    # Reparse, including duplicate-name and property-layout guards.
    inspect_styles(result[0])
    return result,report
