"""Import DDS layout and artwork into a copied TXTR or SCNE texture record."""
import shutil
import uuid
from pathlib import Path
from ..archive.manifests import OUTPUT
from ..formats.txtr import TXTR
from ..formats.package import textures
from ..formats.binary import Binary
from . import dds,gtf,external_converters


def apply_dds(parts,kind,selector,source,job=None,converter=None,preserve_layout=False,reference=None):
    source_data=bytes(source) if isinstance(source,(bytes,bytearray)) else Path(source).read_bytes()
    meta=dds.inspect(source_data)
    index=None
    if kind=='TXTR':texture=TXTR(parts)
    elif kind=='SCNE':
        if not selector.startswith('texture_') or not selector[8:].isdigit():raise ValueError('Expected SCNE/texture_N DDS target')
        index=int(selector[8:]);items=textures(parts)
        if not 0<=index<len(items):raise ValueError('SCNE texture index is out of range')
        item=items[index];texture=TXTR([item.header,item.payload])
    else:raise ValueError('DDS target must be TXTR or SCNE')
    if kind=='TXTR' and preserve_layout and reference is not None:
        # DDS supersedes raw TXTR artwork and layout. Build from the validated
        # base header instead of attempting to parse an obsolete raw header
        # (older exports can carry invalid depth/dimension markers).
        texture=reference;parts=list(reference.blocks)
    old=texture.info();reference=reference or texture
    work=OUTPUT/'temp'/('override_dds_'+uuid.uuid4().hex);work.mkdir(parents=True)
    try:
        if job:job.check()
        converted=work/'converted.gtf'
        # Legacy exports use depth=1 for ordinary 2D DDS files. The native
        # converter incorrectly treats that header as a 3D texture.
        normalized=dds.normalized_2d(source_data);input_meta=meta;conformed=False
        if preserve_layout:
            from .runtime_layout import conform
            normalized,conformed=conform(normalized,reference.info(),job)
            meta=dds.inspect(normalized)
        if max(meta['width'],meta['height'])>4096:raise ValueError('Texture exceeds the RSX 4096-pixel dimension ceiling')
        conversion_source=work/'input.dds';conversion_source.write_bytes(normalized)
        external_converters.convert('dds2gtf',conversion_source,converted,override=converter,swizzle=not (reference.info()['linear'] if preserve_layout else old['linear']))
        info,descriptor,image=gtf.parse(converted.read_bytes())
        for key in ('width','height','format','mip_count','cubemap'):
            if info[key]!=meta[key]:raise ValueError('DDS converter changed '+key)
        # A converter may select linear storage for a texture that cannot be
        # swizzled. Its returned descriptor describes the actual pixel layout.
        if len(image)!=info['image_size'] and info['linear'] and info['format'] in ('L8','ARGB8','RGBA16F'):
            from .builtin_converter import compact_linear,to_dds
            if to_dds(converted.read_bytes())[128:]!=normalized[128:]:raise ValueError('Unvalidated linear texture padding')
            image=compact_linear(descriptor,image)
        if len(image)!=info['image_size']:
            # GTF aligns the final storage extent, while TXTR uses exact image
            # bytes. Strip only identified zero padding, preserving all mips.
            if len(image)>info['image_size'] and not any(image[info['image_size']:]):image=image[:info['image_size']]
            else:raise ValueError('DDS converter output size differs from declared image size')
        # Preserve runtime channel routing and placement flags; the DDS supplies
        # format, dimensions, mip count and image pixels.
        descriptor=bytearray(descriptor)
        descriptor[4:8]=texture.blocks[0][0x5c:0x60]
        descriptor[20:24]=texture.blocks[0][0x6c:0x70]
        if preserve_layout:
            descriptor=bytearray(reference.blocks[0][0x58:0x70])
        result=[bytearray(p) for p in parts]
        def update_header(buffer,base):
            old_descriptor=texture.blocks[0][0x58:0x70]
            old_key=(int.from_bytes(old_descriptor[4:8],'big')<<8)|old_descriptor[0]
            new_key=(int.from_bytes(descriptor[4:8],'big')<<8)|descriptor[0]
            for field in (8,12):
                if int.from_bytes(buffer[base+field:base+field+4],'big')==old_key:
                    buffer[base+field:base+field+4]=new_key.to_bytes(4,'big')
            buffer[base+0x58:base+0x70]=descriptor
            if preserve_layout:buffer[base+0x90:base+0x96]=reference.blocks[0][0x90:0x96]
            # +0x90/+0x92 are also consumed by sprite sizing in the game.
            # Preserve the authored extent when replacing artwork at a higher
            # resolution; the RSX descriptor carries the actual image size.
        if kind=='SCNE':
            item=items[index];update_header(result[0],item.header_offset)
            shared=any(t.index!=index and t.payload_offset==item.payload_offset for t in items)
            if len(image)<=old['image_size'] and not shared:
                target=item.payload_offset;result[1][target:target+len(image)]=image
            else:
                target=(len(result[1])+127)&~127
                result[1]+=b'\0'*(target-len(result[1]))+image
                import struct
                struct.pack_into('>I',result[0],item.header_offset+0xa4,target+1)
            updated=next(t for t in textures(result) if t.index==index)
            check=TXTR([updated.header,updated.payload])
        else:
            update_header(result[0],0)
            if len(result)==2:
                if preserve_layout and len(reference.blocks)==2:
                    base_info=reference.info();result[1]=bytearray(image+reference.blocks[1][base_info['image_size']:])
                elif len(image)<=len(result[1]):result[1][:len(image)]=image
                else:result[1]=bytearray(image)
            else:
                target=old['payload_offset']
                if preserve_layout and len(reference.blocks)==1:
                    base_info=reference.info();target=base_info['payload_offset']
                    prefix=bytearray(reference.blocks[0][:target])
                    prefix[:0xb0]=result[0][:0xb0]
                    prefix[0xa4:0xac]=reference.blocks[0][0xa4:0xac]
                    result[0]=prefix+image+reference.blocks[0][target+base_info['image_size']:]
                elif len(image)>old['image_size']:
                    target=(len(result[0])+15)&~15
                    result[0]+=b'\0'*(target-len(result[0]))+image
                    import struct
                    struct.pack_into('>I',result[0],0xa4,target-0xa4+1)
                else:result[0][target:target+len(image)]=image
            check=TXTR(result)
        if check.image()!=image:raise ValueError('DDS override failed texture round-trip')
        report={key:meta[key] for key in ('width','height','format','mip_count')}
        if preserve_layout:report.update(storage_layout_preserved=True,artwork_resampled=conformed,input_layout=input_meta)
        return [bytes(p) for p in result],report
    finally:
        if work.resolve().is_relative_to((OUTPUT/'temp').resolve()):shutil.rmtree(work)



def apply_raw_texture(parts,selector,replacement):
    """Apply a Python-exported package TXTR when no DDS supersedes it."""
    import struct
    index=int(selector.removeprefix('texture_'));items=textures(parts)
    if not 0<=index<len(items):raise ValueError('Package texture index is out of range')
    item=items[index];texture=TXTR(replacement);image=texture.image()
    result=[bytearray(p) for p in parts];base=item.header_offset
    descriptor=texture.blocks[0][0x58:0x70]
    original=item.header[0x58:0x70]
    old_key=(int.from_bytes(original[4:8],'big')<<8)|original[0]
    new_key=(int.from_bytes(descriptor[4:8],'big')<<8)|descriptor[0]
    for field in (8,12):
        if int.from_bytes(result[0][base+field:base+field+4],'big')==old_key:
            result[0][base+field:base+field+4]=new_key.to_bytes(4,'big')
    result[0][base+0x58:base+0x70]=descriptor
    # Keep the destination scene's authored extent and layout.
    target=(len(result[1])+127)&~127;result[1]+=b'\0'*(target-len(result[1]))+image
    struct.pack_into('>I',result[0],base+0xa4,target+1)
    updated=textures(result)[index]
    if TXTR([updated.header,updated.payload]).image()!=image:raise ValueError('Raw texture override failed round-trip')
    return [bytes(p) for p in result]
