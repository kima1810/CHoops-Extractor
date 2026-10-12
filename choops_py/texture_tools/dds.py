"""Bounds-checked DDS metadata for safe imports; no DX10 guessing."""
import struct
from ..formats.binary import Binary
from ..core.errors import ToolError
FORMATS={0x81:'L8',0x85:'ARGB8',0x86:'DXT1',0x87:'DXT3',0x88:'DXT5',0x9a:'RGBA16F'}

def image_size(width,height,fmt,mips=1):
    if not (1<=width<=8192 and 1<=height<=8192 and 1<=mips<=max(width,height).bit_length()):raise ToolError('invalid_texture_dimensions','Invalid dimensions/mip count')
    total=0
    for _ in range(mips):
        if fmt in ('DXT1','DXT3','DXT5'):total+=max(1,(width+3)//4)*max(1,(height+3)//4)*(8 if fmt=='DXT1' else 16)
        elif fmt=='L8':total+=width*height
        elif fmt=='ARGB8':total+=width*height*4
        elif fmt=='RGBA16F':total+=width*height*8
        else:raise ToolError('unsupported_texture_format',str(fmt))
        width=max(1,width//2);height=max(1,height//2)
    return total

def inspect(data):
    b=Binary(data);b.slice(0,128)
    if data[:4]!=b'DDS ' or b.u32(4,'<')!=124 or b.u32(76,'<')!=32:raise ToolError('invalid_dds','Invalid DDS header')
    width,height,mips=b.u32(16,'<'),b.u32(12,'<'),max(1,b.u32(28,'<'))
    caps=b.u32(112,'<');cubemap=caps in (0xfc00,0xfe00)
    if b.u32(24,'<') not in (0,1) or (caps and not cubemap):raise ToolError('unsupported_dds_layout','Partial cubemaps, arrays and volume textures are not supported')
    if cubemap and width!=height:raise ToolError('unsupported_dds_layout','Cubemap faces must be square')
    flags=b.u32(80,'<');fourcc=data[84:88]
    if flags&4:
        fmt='RGBA16F' if fourcc==struct.pack('<I',113) else fourcc.decode('ascii',errors='replace')
        if fmt not in ('DXT1','DXT3','DXT5','RGBA16F'):raise ToolError('unsupported_texture_format',fmt)
    elif flags&0x20000 and b.u32(88,'<')==8 and b.u32(92,'<')==255:fmt='L8'
    elif flags&0x40 and b.u32(88,'<')==32 and tuple(b.u32(o,'<') for o in (92,96,100,104)) in ((0xff0000,0xff00,0xff,0xff000000),(0xff,0xff00,0xff0000,0xff000000)):fmt='ARGB8'
    else:raise ToolError('unsupported_texture_format','DDS pixel masks are not validated')
    size=image_size(width,height,fmt,mips)*(6 if cubemap else 1)
    if len(data)!=128+size:raise ToolError('dds_payload_size_mismatch',f'Expected {size} payload bytes, found {len(data)-128}')
    return dict(width=width,height=height,format=fmt,mip_count=mips,payload_size=size,cubemap=cubemap)

def linear_l8(width,height,mips,payload):
    size=image_size(width,height,'L8',mips)
    if len(payload)!=size:raise ToolError('payload_size_mismatch','L8 bytes are incomplete')
    header=bytearray(128);header[:4]=b'DDS '
    for offset,value in {4:124,8:0x2100f,12:height,16:width,20:width,28:mips,76:32,80:0x20000,88:8,92:255,108:0x401008 if mips>1 else 0x1000}.items():struct.pack_into('<I',header,offset,value)
    result=bytes(header)+payload;inspect(result);return result


def compressed_preview(width, height, fmt, payload):
    """Wrap the base level of block-compressed PS3 textures for read-only viewing."""
    if fmt not in ('DXT1','DXT3','DXT5'):
        raise ToolError('unsupported_texture_format', fmt)
    size = image_size(width,height,fmt)
    if len(payload) < size:
        raise ToolError('payload_size_mismatch','Compressed base mip is incomplete')
    header = bytearray(128);header[:4]=b'DDS '
    for offset,value in {4:124,8:0x81007,12:height,16:width,20:size,28:1,76:32,80:4,108:0x1000}.items():
        struct.pack_into('<I',header,offset,value)
    header[84:88]=fmt.encode('ascii')
    result=bytes(header)+payload[:size]
    inspect(result)
    return result



def normalized_2d(data):
    """Normalize legacy 2D depth and RGBA masks in a scratch copy only."""
    info=inspect(data);result=bytearray(data)
    struct.pack_into('<I',result,24,0)
    struct.pack_into('<I',result,8,struct.unpack_from('<I',result,8)[0]&~0x800000)
    if info['cubemap']:struct.pack_into('<I',result,112,0xfe00)
    if info['format']=='ARGB8' and struct.unpack_from('<I',result,92)[0]==0xff:
        red=bytes(result[128::4]);blue=bytes(result[130::4])
        result[128::4]=blue;result[130::4]=red
        struct.pack_into('<I',result,92,0xff0000);struct.pack_into('<I',result,100,0xff)
    return bytes(result)
