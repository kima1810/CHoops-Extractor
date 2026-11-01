"""Guarded single-face artwork support for legacy folder exports."""
from . import dds
from .runtime_layout import conform


def replace_cube_first_face(data,reference,job=None):
    """Legacy flat DDS updates +X; retain the other five authored cube faces."""
    from .builtin_converter import to_dds
    source=dds.inspect(data);layout=reference.info()
    if source['cubemap'] or not layout['cubemap']:
        raise ValueError('Single-face import requires 2D DDS and a cubemap target')
    face_layout={**layout,'cubemap':False}
    face,_=conform(data,face_layout,job)
    base=to_dds(reference.gtf())
    size=dds.image_size(layout['width'],layout['height'],layout['format'],layout['mip_count'])
    result=base[:128]+face[128:128+size]+base[128+size:]
    info=dds.inspect(result)
    if not info['cubemap'] or result[128+size:]!=base[128+size:]:
        raise ValueError('Cubemap face preservation failed')
    return result
