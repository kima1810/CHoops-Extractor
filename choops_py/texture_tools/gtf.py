import struct
from ..formats.binary import Binary
from ..core.errors import ToolError
from .dds import FORMATS,image_size

def descriptor_info(descriptor):
    b=Binary(descriptor);b.slice(0,24)
    code=descriptor[0];fmt=FORMATS.get(code&0x9f)
    if not fmt:raise ToolError('unsupported_texture_format',f'PS3 format 0x{code:02x}')
    width,height,mips=b.u16(8),b.u16(10),descriptor[1]
    # The dimension selects a volume. A volume with one stored slice has the
    # same payload extent as 2D art and can accept a 2D replacement while its
    # original descriptor is preserved. Deeper volumes remain unsupported.
    depth=b.u16(12)
    single_slice_volume=descriptor[2]==3 and descriptor[3]==0 and depth==1
    if (descriptor[2]!=2 and not single_slice_volume) or descriptor[3] not in (0,1):
        raise ToolError('unsupported_texture_layout',f'Only 2D textures, single-slice volumes, and complete cubemaps are writable (dimension={descriptor[2]}, cube={descriptor[3]}, stored_depth={depth}, size={width}x{height})')
    cubemap=bool(descriptor[3])
    if cubemap and width!=height:raise ToolError('unsupported_texture_layout','Cubemap faces must be square')
    size=image_size(width,height,fmt,mips)
    pitch=b.u32(16)
    if code&0x20 and fmt in ('L8','ARGB8') and pitch!=width*(1 if fmt=='L8' else 4):raise ToolError('unsupported_texture_pitch',f'Padded pitch {pitch} is not validated')
    if code&0x20 and fmt in ('DXT1','DXT3','DXT5'):
        block_bytes=8 if fmt=='DXT1' else 16
        if pitch<max(1,(width+3)//4)*block_bytes:raise ToolError('unsupported_texture_pitch','Compressed row pitch is smaller than a block row')
        # RSX linear mip levels retain the top-level block-row pitch.
        size=0;mip_height=height
        for _ in range(mips):
            size+=pitch*max(1,(mip_height+3)//4);mip_height=max(1,mip_height//2)
    if cubemap:size=size*6 if code&0x20 else ((size+127)&~127)*5+size
    return dict(remap=b.u32(4),width=width,height=height,format=fmt,mip_count=mips,image_size=size,ps3_format=code,linear=bool(code&0x20),pitch=pitch,cubemap=cubemap)

def make(descriptor,payload):
    descriptor_info(descriptor)
    return struct.pack('>6I',0x01080000,len(payload)+48,1,0,48,len(payload))+descriptor+payload

def parse(data):
    b=Binary(data);b.slice(0,48)
    if b.u32(0)!=0x01080000 or b.u32(8)!=1:raise ToolError('invalid_gtf','Expected one-texture GTF')
    offset,size=b.u32(16),b.u32(20);payload=b.slice(offset,size)
    if offset<48 or offset+size>len(data):raise ToolError('invalid_gtf','Invalid GTF payload range')
    info=descriptor_info(data[24:48]);info.update(payload_offset=offset,payload_size=size)
    return info,data[24:48],payload


def remap_preview(image,remap):
    """Apply RSX A/R/G/B selectors and ZERO/ONE/REMAP output controls."""
    from PIL import Image
    if remap==0xaae4:return image
    if remap>>16:raise ValueError('Unsupported RSX texture remap order')
    red,green,blue,alpha=image.convert('RGBA').split()
    sources=(alpha,red,green,blue);outputs=[]
    for index in range(4):
        operation=(remap>>(8+index*2))&3
        if operation==0:outputs.append(Image.new('L',image.size,0))
        elif operation==1:outputs.append(Image.new('L',image.size,255))
        elif operation==2:outputs.append(sources[(remap>>(index*2))&3])
        else:raise ValueError('Reserved RSX texture remap operation')
    return Image.merge('RGBA',(outputs[1],outputs[2],outputs[3],outputs[0]))
