"""Independent DDS/GTF container conversion; compressed blocks remain lossless.

RSX uses Morton addresses for uncompressed swizzled samples, big-endian color
words, a constant pitch for linear mip rows, and 128-byte swizzled cube alignment.
Formats: L8, ARGB8, DXT1/3/5 and RGBA16F. No proprietary executable is needed.
"""
from array import array
from functools import lru_cache
import struct
from . import dds,gtf
from ..core.errors import ToolError


def _power_two(value):return value>0 and value&(value-1)==0


@lru_cache(maxsize=20)
def _morton_order(width,height,inverse=False):
    if not _power_two(width) or not _power_two(height):raise ToolError('unsupported_swizzle_dimensions','Swizzled dimensions must be powers of two')
    result=array('I')
    def visit(x,y,w,h):
        if w==h==1:result.append(y*width+x);return
        if h>w:visit(x,y,w,h//2);visit(x,y+h//2,w,h//2)
        elif w>h:visit(x,y,w//2,h);visit(x+w//2,y,w//2,h)
        else:
            a,b=w//2,h//2
            visit(x,y,a,b);visit(x+a,y,a,b);visit(x,y+b,a,b);visit(x+a,y+b,a,b)
    visit(0,0,width,height)
    if inverse:
        indices=array('I',[0])*len(result)
        for address,linear in enumerate(result):indices[linear]=address
        return indices
    return result


def _swizzle(data,width,height,bytes_per_pixel,inverse=False):
    unit=min(4,bytes_per_pixel);width*=bytes_per_pixel//unit
    indices=_morton_order(width,height,inverse)
    if len(data)!=width*height*unit:raise ToolError('payload_size_mismatch','Swizzle sample count differs')
    if unit==1:return bytes(data[i] for i in indices)
    samples=array('I');samples.frombytes(data)
    return array('I',(samples[i] for i in indices)).tobytes()


def _endian(data,fmt):
    unit=4 if fmt=='ARGB8' else 2 if fmt=='RGBA16F' else 1
    if unit==1:return data
    result=bytearray(len(data))
    for i in range(unit):result[i::unit]=data[unit-1-i::unit]
    return bytes(result)


def _levels(width,height,mips,fmt):
    for _ in range(mips):
        compressed=fmt.startswith('DXT');unit=(8 if fmt=='DXT1' else 16) if compressed else {'L8':1,'ARGB8':4,'RGBA16F':8}[fmt]
        columns=max(1,(width+3)//4) if compressed else width
        rows=max(1,(height+3)//4) if compressed else height
        yield width,height,columns*unit,rows,unit
        width=max(1,width//2);height=max(1,height//2)


def _extent(info,padded):
    levels=list(_levels(info['width'],info['height'],info['mip_count'],info['format']))
    chain=sum((info['pitch'] if padded else row)*rows for _,_,row,rows,_ in levels)
    if not info['cubemap']:return chain
    return chain*6 if info['linear'] else ((chain+127)&~127)*5+chain


def to_gtf(data,swizzle=False):
    data=dds.normalized_2d(data);info=dds.inspect(data);fmt=info['format']
    width,height=info['width'],info['height'];pot=_power_two(width) and _power_two(height)
    compressed=fmt.startswith('DXT')
    # Block compression uses linear block order even with RSX's SZ format bit.
    linear=not pot if compressed else not (swizzle and pot)
    levels=list(_levels(width,height,info['mip_count'],fmt))
    pitch=levels[0][2] if linear else 0
    payload=bytearray();cursor=128
    for face in range(6 if info['cubemap'] else 1):
        if face and not linear:payload+=b'\0'*((-len(payload))%128)
        for w,h,row,rows,unit in levels:
            size=row*rows;image=data[cursor:cursor+size];cursor+=size
            image=_endian(image,fmt)
            if not linear and not compressed:image=_swizzle(image,w,h,unit)
            if linear:
                for y in range(rows):payload+=image[y*row:(y+1)*row]+b'\0'*(pitch-row)
            else:payload+=image
    code=next(k for k,v in dds.FORMATS.items() if v==fmt)|(0x20 if linear else 0)
    descriptor=struct.pack('>4BI3HBBII',code,info['mip_count'],2,int(info['cubemap']),0xa9ff if fmt=='L8' else 0xaae4,width,height,1,0,0,pitch,0)
    padded=(len(payload)+127)&~127
    result=struct.pack('>6I',0x01080000,padded,1,0,128,len(payload))+descriptor+b'\0'*80+payload+b'\0'*(padded-len(payload))
    # Every imported mip and cubemap face must survive inverse conversion.
    if to_dds(result)[128:]!=data[128:]:raise ToolError('conversion_roundtrip_mismatch','Built-in DDS conversion changed image bytes')
    return bytes(result)


def _unpack_image(info,payload,decode_swizzle=True):
    compact=_extent(info,False);physical=_extent(info,True) if info['linear'] else compact
    padded=info['linear'] and len(payload)==physical
    if len(payload) not in (compact,physical):raise ToolError('payload_size_mismatch','GTF texture storage extent is not validated')
    levels=list(_levels(info['width'],info['height'],info['mip_count'],info['format']))
    position=0;result=bytearray()
    for face in range(6 if info['cubemap'] else 1):
        if face and not info['linear']:position=(position+127)&~127
        for w,h,row,rows,unit in levels:
            pitch=info['pitch'] if padded else row;size=pitch*rows
            image=payload[position:position+size];position+=size
            if pitch!=row:image=b''.join(image[y*pitch:y*pitch+row] for y in range(rows))
            if decode_swizzle and not info['linear'] and not info['format'].startswith('DXT'):image=_swizzle(image,w,h,unit,True)
            result+=image
    if position!=len(payload):raise ToolError('payload_size_mismatch','GTF mip/face traversal differs')
    return bytes(result)


def compact_linear(descriptor,payload):
    """Retain CH2K8's existing tightly packed uncompressed linear mip layout."""
    info=gtf.descriptor_info(descriptor)
    if not info['linear'] or info['format'].startswith('DXT'):return payload
    tight=_unpack_image(info,payload,False)
    return tight


def to_dds(data):
    info,descriptor,payload=gtf.parse(data);fmt=info['format']
    image=_endian(_unpack_image(info,payload),fmt)
    header=bytearray(128);header[:4]=b'DDS '
    compressed=fmt.startswith('DXT');mips=info['mip_count'];cube=info['cubemap']
    flags=0x1007|(0x20000 if mips>1 else 0)|(0x80000 if compressed else 8)
    vals={4:124,8:flags,12:info['height'],16:info['width'],20:dds.image_size(info['width'],info['height'],fmt) if compressed else info['width']*{'L8':1,'ARGB8':4,'RGBA16F':8}[fmt],28:mips,76:32,108:0x1000|(0x400008 if mips>1 else 8 if cube else 0),112:0xfe00 if cube else 0}
    if compressed:vals[80]=4;header[84:88]=fmt.encode('ascii')
    elif fmt=='RGBA16F':vals.update({80:4,84:113})
    elif fmt=='L8':vals.update({80:0x20000,88:8,92:255})
    else:vals.update({80:0x41,88:32,92:0xff0000,96:0xff00,100:0xff,104:0xff000000})
    for offset,value in vals.items():struct.pack_into('<I',header,offset,value)
    result=bytes(header)+image;dds.inspect(result);return result
