"""Shared SCNE package texture layout; geometry remains byte-preserved."""
from dataclasses import dataclass
from .binary import Binary
from ..core.errors import ToolError
@dataclass
class PackageTexture:
    index: int
    header_offset: int
    payload_offset: int
    payload_end: int
    header: bytes
    payload: bytes

def textures(blocks):
    if len(blocks)!=2: raise ToolError('package_layout_not_supported','SCNE texture package requires header and data blocks')
    head,data=blocks; b=Binary(head);b.slice(0,0x54)
    count=b.u32(0x20)
    if count>4096:raise ToolError('invalid_package','Texture count exceeds limit')
    if not count:return []
    table=b.relative(0x24);b.slice(table,count*0xb0)
    offsets=[b.u32(table+i*0xb0+0xa4)-1 for i in range(count)]
    if any(o<0 or o>=len(data) for o in offsets):raise ToolError('invalid_package','Texture payload pointer outside data block')
    result=[]
    for i,start in enumerate(offsets):
        end=min([o for o in offsets if o>start],default=len(data));off=table+i*0xb0
        result.append(PackageTexture(i,off,start,end,head[off:off+0xb0],data[start:end]))
    return result

def replace_texture(blocks,index,image,logical_length):
    items=textures(blocks);matches=[t for t in items if t.index==index]
    if len(matches)!=1:raise ToolError('texture_not_found',str(index))
    t=matches[0]
    if logical_length>len(t.payload) or len(image)!=logical_length:raise ToolError('payload_size_mismatch','Texture image must fit original slice')
    for other in items:
        if other.index!=index and other.payload_offset==t.payload_offset:raise ToolError('aliased_texture','Shared package payload')
    data=bytearray(blocks[1]);data[t.payload_offset:t.payload_offset+logical_length]=image
    return [blocks[0],bytes(data)]


def repack_images(original,updated):
    """Replace image spans, relocate declared GPU buffers, preserve other bytes."""
    import struct
    from .txtr import TXTR
    if len(original)!=2 or len(updated)!=2:raise ValueError('Image packing requires a two-block scene')
    before=textures(original);after=textures(updated)
    if len(before)!=len(after):raise ValueError('Image packing must retain texture slots')
    b=Binary(original[0]);head=bytearray(updated[0]);old=original[1]
    intervals=[];images={}
    for t,n in zip(before,after):
        length=TXTR([t.header,t.payload]).info()['image_size']
        if t.payload_offset+length>len(old):raise ValueError('Image exceeds scene data')
        intervals.append((t.payload_offset,t.payload_offset+length))
        images[t.index]=TXTR([n.header,n.payload]).image()
    merged=[]
    for start,end in sorted(intervals):
        if merged and start<merged[-1][1]:merged[-1]=(merged[-1][0],max(end,merged[-1][1]))
        else:merged.append((start,end))
    refs=[];count=b.u32(0x44);parts=b.relative(0x48) if count else 0
    if count>4096:raise ValueError('Scene part count exceeds limit')
    for i in range(count):
        part=parts+i*176;descriptors=b.u32(part+0x84)
        if descriptors not in (0,1):raise ValueError('Cannot relocate unclassified vertex descriptors')
        if descriptors:
            desc=b.relative(part+0x88);streams=b.u32(desc+20) or 1
            if not 1<=streams<=16:raise ValueError('Invalid vertex stream count')
            for j in range(streams):
                entry=desc+28+j*16;length=b.u32(entry+8)
                if length:refs.append((entry+12,b.u32(entry+12)-1,length))
        length=b.u32(part+0xa8)*2
        if length:refs.append((part+0xac,b.u32(part+0xac)-1,length))
    for field,start,length in refs:
        if start<0 or start+length>len(old):raise ValueError('GPU buffer exceeds scene data')
        if any(start<end and begin<start+length for begin,end in merged):raise ValueError('Geometry overlaps a texture image')
    data=bytearray();mapping=[];cursor=0
    def preserve(start,end):
        if end<=start:return
        target=len(data)+(start-len(data))%128
        data.extend(b'\0'*(target-len(data)));data.extend(old[start:end])
        if updated[1][start:end]!=old[start:end]:raise ValueError('Non-image scene data changed during texture import')
        mapping.append((start,end,target))
    for start,end in merged:
        preserve(cursor,start)
        aliases={}
        for t,n in zip(before,after):
            if not start<=t.payload_offset<end:continue
            image=images[t.index];key=(t.payload_offset,image,n.header[0x58:0x70])
            if key not in aliases:
                target=(len(data)+127)&~127
                data.extend(b'\0'*(target-len(data)));data.extend(image);aliases[key]=target
            struct.pack_into('>I',head,n.header_offset+0xa4,aliases[key]+1)
        cursor=end
    preserve(cursor,len(old))
    for field,start,length in refs:
        candidates=[target+start-begin for begin,end,target in mapping if begin<=start and start+length<=end]
        if len(candidates)!=1:raise ValueError('GPU buffer relocation is ambiguous')
        target=candidates[0];struct.pack_into('>I',head,field,target+1)
        if data[target:target+length]!=old[start:start+length]:raise ValueError('Geometry changed during image packing')
    result=[bytes(head),bytes(data)]
    for t in textures(result):
        if TXTR([t.header,t.payload]).image()!=images[t.index]:raise ValueError('Packed texture differs from imported artwork')
    return result
