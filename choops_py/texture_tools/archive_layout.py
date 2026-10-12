"""Apply the selected base JB's texture contract outside stadium archives."""
import re
from ..archive.hash_names import replacement_hash
from ..formats.txtr import TXTR
from ..formats.package import textures, repack_images
from .override_import import apply_dds
from .builtin_converter import to_dds
from .dds import FORMATS


def stadium_archive(group):
    name=group.get('name') or group['entry'].get('name') or ''
    if re.fullmatch(r's\d{3,5}n?\.(?:iff|cdf)',name,re.I):return True
    # Numeric hashes in Python exports must receive the same policy as names.
    return group['entry']['hash'] in _STADIUM_HASHES


_STADIUM_HASHES=frozenset(replacement_hash(f's{i:03d}{suffix}.iff') for i in range(1024) for suffix in ('','n'))


def normalize_record(parts,base,kind,job=None,compact=True):
    """Keep replacement geometry and artwork; restore base image layout."""
    if kind=='TXTR':current=[TXTR(parts)];reference=[TXTR(base)]
    elif kind=='SCNE':
        if len(parts)==1 and len(parts[0])>=0x24 and not int.from_bytes(parts[0][0x20:0x24],'big'):return parts,[]
        current=[TXTR([t.header,t.payload]) for t in textures(parts)]
        candidates=[TXTR([t.header,t.payload]) for t in textures(base)]
        reference=[]
        for texture in current:
            identity=texture.blocks[0][:4]
            matches=[t for t in candidates if t.blocks[0][:4]==identity]
            if len(matches)!=1:raise ValueError('Scene texture has no unique base-JB identity; cannot normalize safely')
            reference.append(matches[0])
    else:return parts,[]
    result=parts;reports=[]
    for index,(texture,target) in enumerate(zip(current,reference)):
        if job:job.check()
        if len(texture.blocks[0])<0x70 or len(target.blocks[0])<0x70:
            raise ValueError('Texture header is truncated; cannot normalize its base-JB layout')
        if texture.blocks[0][0x58]&0x9f not in FORMATS:
            if texture.blocks[0][0x58:0x70]!=target.blocks[0][0x58:0x70]:raise ValueError('Unsupported texture format changed its base-JB layout')
            continue
        # Unchanged render targets can have formats not supported for artwork.
        if texture.blocks[0][0x58:0x70]==target.blocks[0][0x58:0x70] and texture.blocks==target.blocks:continue
        selector=f'texture_{index}' if kind=='SCNE' else 'texture'
        result,report=apply_dds(result,kind,selector,to_dds(texture.gtf()),job,
                                preserve_layout=True,reference=target)
        reports.append(dict(texture=selector,**report))
    if kind=='SCNE' and reports and compact:result=repack_images(parts,result)
    return result,reports
