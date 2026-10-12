"""Prepare a single-surface court from user-supplied SCNE and artwork."""
import io
import math
import re
import struct
import zipfile
from pathlib import Path
from PIL import Image
from ..formats.binary import Binary
from ..formats.tool_wrapper import unwrap,wrap
from ..formats.package import textures,repack_images
from ..formats.txtr import TXTR
from ..formats.scne import preview_meshes
from ..texture_tools.builtin_converter import to_dds
from ..texture_tools.runtime_layout import conform
from ..texture_tools.override_import import apply_dds
from ..texture_tools import dds

ALBEDO=0xb6e7ae40
BUMP=0xc8fb297e
BUMP_SHADER=0xfca5f1a8


def active_slots(blocks):
    """Recognize the prepared court by its actual draw and sampler routing."""
    try:
        b=Binary(blocks[0]);items=textures(blocks)
        if len(items)<3:return None
        parts=b.relative(0x48);live=[parts+i*176 for i in range(b.u32(0x44)) if b.u32(parts+i*176+0x7c)]
        if len(live)!=1 or b.utf16(b.relative(live[0]),'be').casefold()!='floor':return None
        run=b.relative(live[0]+0x80)
        if b.u32(live[0]+0x7c)!=1 or b.u32(run+32)!=0:return None
        material=b.relative(0x38)
        if b.u32(material+8)!=BUMP_SHADER:return None
        shaders=b.relative(0x2c);matches=[shaders+i*48 for i in range(b.u32(0x28)) if b.u32(shaders+i*48)==BUMP_SHADER]
        if len(matches)!=1:return None
        shader=matches[0];samplers=b.relative(shader+28);params=b.relative(material+32);bindings={}
        for i in range(b.u32(shader+8)&65535):
            sampler=samplers+i*36;bindings[b.u32(sampler)]=b.u32(params+b.u16(sampler+16)+12)
        if bindings.get(ALBEDO)!=int.from_bytes(items[0].header[:4],'big') or bindings.get(BUMP)!=int.from_bytes(items[2].header[:4],'big'):return None
        return {0,2}
    except (ValueError,struct.error):return None


def _put(buffer,offset,value):struct.pack_into('>I',buffer,offset,value)


def _append(buffer,data,alignment=16):
    offset=(len(buffer)+alignment-1)&~(alignment-1)
    buffer.extend(b'\0'*(offset-len(buffer)));buffer.extend(data)
    return offset


def _unit(vector,fallback):
    length=math.sqrt(sum(x*x for x in vector))
    return tuple(x/length for x in vector) if length>1e-12 else fallback


def _tangents(triangles):
    sums={}
    for i in range(0,len(triangles),3):
        a,b,c=triangles[i:i+3];e1=tuple(b[j]-a[j] for j in range(3));e2=tuple(c[j]-a[j] for j in range(3))
        u1,v1=b[3]-a[3],b[4]-a[4];u2,v2=c[3]-a[3],c[4]-a[4]
        determinant=u1*v2-u2*v1
        if abs(determinant)<1e-12:continue
        tangent=tuple((e1[j]*v2-e2[j]*v1)/determinant for j in range(3))
        bitangent=tuple((e2[j]*u1-e1[j]*u2)/determinant for j in range(3))
        for vertex in (a,b,c):
            previous=sums.setdefault(vertex,[0.]*6)
            for j,value in enumerate(tangent+bitangent):previous[j]+=value
    return sums


def prepare_blocks(floor,arena,artwork,normal,job=None):
    """Retain scene identities and geometry; bind a real tangent-space bump."""
    if len(floor)!=2 or len(arena)!=2:raise ValueError('Court preparation requires two-block floor and arena scenes')
    if len(textures(floor))<3:raise ValueError('Court template needs texture slots 0 and 2')
    for source in (artwork,normal):
        meta=dds.inspect(source)
        if meta['cubemap'] or max(meta['width'],meta['height'])>4096:raise ValueError('Court surfaces require 2D images within the RSX dimension ceiling')
    original=preview_meshes(floor)
    meshes=[m for m in original['meshes'] if m['name'].casefold()=='floor']
    if len(meshes)!=1:raise ValueError('Template must contain one declared floor mesh')
    head=bytearray(floor[0]);gpu=bytearray(floor[1]);b=Binary(floor[0]);donor=Binary(arena[0])
    part_table=b.relative(0x48)
    floor_parts=[part_table+i*176 for i in range(b.u32(0x44)) if b.utf16(b.relative(part_table+i*176),'be').casefold()=='floor']
    if len(floor_parts)!=1:raise ValueError('Ambiguous floor part')
    active=floor_parts[0];disabled=[]
    for i in range(b.u32(0x44)):
        part=part_table+i*176
        if part!=active:
            disabled.append(b.utf16(b.relative(part),'be'));_put(head,part+0x7c,0)
    run=b.relative(active+0x80)
    if b.u32(active+0x7c)!=1 or b.u32(run+32)!=0:raise ValueError('Unsupported floor material routing')
    shader_table=donor.relative(0x2c)
    shaders=[shader_table+i*48 for i in range(donor.u32(0x28)) if donor.u32(shader_table+i*48)==BUMP_SHADER]
    if len(shaders)!=1:raise ValueError('Arena has no matching bump shader')
    shader=shaders[0];material_table=donor.relative(0x38)
    materials=[material_table+i*40 for i in range(donor.u32(0x30)) if donor.u32(material_table+i*40+8)==BUMP_SHADER]
    if not materials:raise ValueError('Arena bump parameters are missing')
    material=materials[0];parameters=donor.relative(material+32)
    # Copy the complete metadata pool to preserve nested CG program pointers.
    # New top-level descriptors precede the pools, retaining forward pointers.
    old_shaders=b.relative(0x2c);count=b.u32(0x28)
    table=_append(head,b'\0'*((count+1)*48))
    original_pool=_append(head,floor[0],128);donor_pool=_append(head,arena[0],128)
    for i in range(count+1):
        source=b if i<count else donor;old=old_shaders+i*48 if i<count else shader
        pool=original_pool if i<count else donor_pool;new=table+i*48
        head[new:new+48]=source.slice(old,48)
        for field in (24,28,32,36):
            if source.u32(old+field):
                relative=struct.unpack('>i',source.slice(old+field,4))[0]
                target=old+field+relative-1
                if not 0<=target<len(source.data):raise ValueError('Shader pointer is outside metadata')
                _put(head,new+field,pool+target-(new+field)+1)
    _put(head,0x28,count+1);_put(head,0x2c,table-0x2c+1)
    destination=b.relative(0x38);identity=b.u32(destination)
    head[destination:destination+40]=donor.slice(material,40);_put(head,destination,identity)
    params=donor_pool+parameters;_put(head,destination+32,params-(destination+32)+1)
    slots=textures(floor);slot_ids=[int.from_bytes(t.header[:4],'big') for t in slots]
    sampler_table=donor.relative(shader+28);bump_reference=None
    for i in range(donor.u32(shader+8)&65535):
        sampler=sampler_table+i*36;semantic=donor.u32(sampler);offset=donor.u16(sampler+16)+12
        if offset+4>(donor.u32(shader+12)&65535):raise ValueError('Invalid bump sampler offset')
        if semantic==BUMP:bump_reference=donor.u32(parameters+offset)
        value=slot_ids[0] if semantic==ALBEDO else slot_ids[2] if semantic==BUMP else donor.u32(parameters+offset)
        _put(head,params+offset,value)
    uniforms=donor.relative(shader+24)
    for i in range(donor.u32(shader+8)>>16):
        uniform=uniforms+i*44
        if donor.u32(uniform)==0x9015351f:
            offset=donor.u16(uniform+20)
            if offset+16>(donor.u32(shader+12)&65535):raise ValueError('Invalid diffuse color offset')
            struct.pack_into('>4f',head,params+offset,1.,1.,1.,1.)
    bump_textures=[t for t in textures(arena) if int.from_bytes(t.header[:4],'big')==bump_reference]
    if len(bump_textures)!=1:raise ValueError('Bump sampler has no unique texture')
    head[slots[2].header_offset+0x58:slots[2].header_offset+0x70]=bump_textures[0].header[0x58:0x70]
    # Slot 2 still points at its old pixels until replacement: only copy routing.
    head[slots[2].header_offset+0x58:slots[2].header_offset+0x5c]=slots[2].header[0x58:0x5c]
    head[slots[2].header_offset+0x60:slots[2].header_offset+0x70]=slots[2].header[0x60:0x70]
    # Add a second stream using ordinary float attributes; the RSX converts
    # these to the same shader inputs as the donor's packed normal stream.
    desc=b.relative(active+0x88);vertices=b.u32(desc+16)
    if b.u32(desc+20)!=1 or b.u32(desc+32)!=36:raise ValueError('Unsupported floor vertex stream')
    start=b.u32(desc+40)-1;vertex_data=floor[1][start:start+vertices*36]
    sums=_tangents(meshes[0]['vertices']);stream=bytearray()
    for i in range(vertices):
        xyz=struct.unpack_from('>3f',vertex_data,i*36);uv=struct.unpack_from('>2e',vertex_data,i*36+28)
        accumulated=sums.get(xyz+uv,[1.,0.,0.,0.,0.,1.])
        tangent=_unit((accumulated[0],0.,accumulated[2]),(1.,0.,0.))
        candidate=_unit((accumulated[3],0.,accumulated[5]),(0.,0.,1.))
        perpendicular=(-tangent[2],0.,tangent[0])
        bitangent=perpendicular if sum(x*y for x,y in zip(perpendicular,candidate))>=0 else tuple(-x for x in perpendicular)
        stream.extend(struct.pack('>11f',*uv,0.,1.,0.,*tangent,*bitangent))
    stream_offset=_append(gpu,stream,128)
    descriptor=bytearray(b.slice(desc,44));_put(descriptor,20,2)
    descriptor.extend(struct.pack('>4I',b.u32(desc+28),44,len(stream),stream_offset+1))
    new_desc=_append(head,descriptor);_put(head,active+0x88,new_desc-(active+0x88)+1)
    declaration=b.relative(active+0x9c);decl_count=b.u32(active+0x94)
    declarations=bytearray(b.slice(declaration,decl_count*64))
    for semantic,offset,components,attribute in ((0x821be059,0,2,9),(0x57b6a2fa,8,3,2),(0xa77313e4,20,3,14),(0xea659b6d,32,3,15)):
        entry=bytearray(64);_put(entry,0,semantic);entry[8:16]=bytes((0x20,offset,1,0,2,components,attribute,0));declarations.extend(entry)
    new_decl=_append(head,declarations);_put(head,active+0x94,decl_count+4);_put(head,active+0x9c,new_decl-(active+0x9c)+1)
    baseline=[bytes(head),bytes(gpu)];result=baseline
    for i in range(len(slots)):
        if job:job.check()
        source=artwork if i==0 else normal if i==2 else _dummy()
        result,_=apply_dds(result,'SCNE',f'texture_{i}',source,job)
    result=repack_images(baseline,result)
    after=preview_meshes(result)
    if len(after['meshes'])!=1 or after['meshes'][0]['vertices']!=meshes[0]['vertices']:raise ValueError('Floor geometry verification failed')
    if any(batch['texture_index']!=0 for batch in after['meshes'][0]['batches']):raise ValueError('Floor albedo routing verification failed')
    return result,dict(disabled_parts=disabled,active_texture_slots=[0,2],texture_bytes=sum(TXTR([t.header,t.payload]).info()['image_size'] for t in textures(result)),geometry_preserved=True,runtime_verified=False)


def _dummy():
    output=io.BytesIO();Image.new('RGBA',(4,4),(0,0,0,0)).save(output,format='DDS',pixel_format='DXT1')
    return conform(output.getvalue(),dict(width=1,height=1,format='DXT1',mip_count=1,cubemap=False))[0]


def prepare(input_path,output,job=None):
    """Read the supplied ZIP without extracting or distributing its contents."""
    from ..archive.manifests import safe_output
    from ..core.reports import save_json
    output=safe_output(output,[input_path]);output.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(input_path) as archive:
        floors=[n for n in archive.namelist() if n.lower().endswith('/floor.scne')]
        if len(floors)!=1:raise ValueError('ZIP must contain one floor.scne')
        root=floors[0].rsplit('/',1)[0]
        if not re.fullmatch(r's\d{3,5}n?',Path(root).name,re.I):raise ValueError('Court ZIP must use a stadium sNNN folder')
        def read(name):
            if archive.getinfo(name).file_size>128*1024*1024:raise ValueError('Template asset exceeds the supported 128 MiB input limit')
            if job:job.check()
            return archive.read(name)
        floor=unwrap(read(floors[0]))[1];arena=unwrap(read(root+'/arena.scne'))[1]
        artwork=read(root+'/_floor.scne/texture_0.dds')
        # The supplied normal DDS has scrambled pixels; the raw TXTR retains
        # the clean normal artwork. Decode it with the built-in swizzle rules.
        normal_source=TXTR.from_bytes(read(root+'/floor_normalglossdetail.txtr'))
        normal_dds=to_dds(normal_source.gtf());layout=dds.inspect(normal_dds)
        with Image.open(io.BytesIO(normal_dds)) as image:
            rgba=image.convert('RGBA');r,g,_,_=rgba.split()
            # Arena's BumpSampler uses DXT5nm: X in alpha, Y in green.
            packed=Image.merge('RGBA',(Image.new('L',rgba.size),g,Image.new('L',rgba.size),r))
        raw=io.BytesIO();packed.save(raw,format='DDS')
        normal=conform(raw.getvalue(),dict(width=layout['width'],height=layout['height'],format='DXT5',mip_count=layout['mip_count'],cubemap=False),job)[0]
        meta=dds.inspect(artwork)
        if max(meta['width'],meta['height'],layout['width'],layout['height'])>4096:raise ValueError('Court image exceeds the RSX dimension ceiling')
        result,report=prepare_blocks(floor,arena,artwork,normal,job)
    target=output/Path(root).name;target.mkdir(exist_ok=True)
    (target/'floor.scne').write_bytes(wrap(2,result));images=target/'_floor.scne';images.mkdir(exist_ok=True)
    (images/'texture_0.dds').write_bytes(artwork);(images/'texture_2.dds').write_bytes(normal)
    report.update(albedo=meta,bump=dds.inspect(normal),dimension_ceiling=4096,
                  maximum_crash_free_resolution='Not established by static validation',
                  normal_source='Raw floor_normalglossdetail TXTR',floor=str(target/'floor.scne'))
    save_json(output/'court_template_report.json',report)
    return report
