from .binary import Binary
from .tool_wrapper import unwrap
def inspect(data):
    blocks=unwrap(data)[1] if data[:4]==b'2kTl' else [data];b=Binary(blocks[0]);b.slice(0,0x54)
    count=b.u32(0x44);table=b.relative(0x48);b.slice(table,count*0xb0);parts=[]
    for i in range(count):
        off=table+i*0xb0;parts.append(dict(index=i,name=b.utf16(b.relative(off),'be'),index_flags=b.u32(off+0xa4),index_count=b.u32(off+0xa8),index_offset_plus_one=b.u32(off+0xac),raw_words=[b.u32(off+j*4) for j in range(44)]))
    return dict(mode='read-only',texture_count=b.u32(0x20),parts=parts,block_sizes=[len(x) for x in blocks])


def preview_meshes(blocks):
    """Decode bounded, declared float-position/half-UV triangle strips read-only."""
    import math
    import struct
    if len(blocks) not in (1,2):
        raise ValueError("3D preview requires one or two SCNE blocks")
    embedded = len(blocks) == 1
    head = Binary(blocks[0])
    payload = head if embedded else Binary(blocks[1])
    head.slice(0, 0x54)
    count = head.u32(0x44)
    if count > 4096:
        raise ValueError("SCNE part count exceeds preview limit")
    table = head.relative(0x48) if count else 0
    head.slice(table, count * 0xb0)
    meshes, warnings = [], []
    total_vertices = 0
    material_textures = {}
    material_hashes = {}
    material_names = {}
    diffuse_materials = set()
    material_colors = {}
    lightmap_textures = {}
    material_shader_modes = {}
    transforms = {}
    instance_count = head.u32(0x3c)
    if instance_count:
        if instance_count > 10000:
            raise ValueError('SCNE instance count exceeds preview limit')
        instances = head.relative(0x40)
        candidates=[]
        for stride in (144,128):
            try:
                head.slice(instances,instance_count*stride)
                candidate={}
                for j in range(instance_count):
                    instance=instances+j*stride
                    matrix=struct.unpack('>16f',head.slice(instance,64))
                    if not all(math.isfinite(x) and abs(x)<1e8 for x in matrix) or any(abs(matrix[k])>1e-5 for k in (3,7,11)) or abs(matrix[15]-1.)>1e-5:
                        raise ValueError('Unsupported SCNE instance transform')
                    candidate.setdefault(head.u32(instance+68),[]).append(matrix)
                if candidate not in candidates:candidates.append(candidate)
            except ValueError:continue
        if len(candidates)!=1:raise ValueError('Unsupported or ambiguous SCNE instance transform layout')
        transforms=candidates[0]
    # Materials refer to shader-sized parameter blocks containing texture hashes.
    # Match only aligned references to unique texture IDs in this package.
    try:
        texture_count, shader_count, material_count = (head.u32(x) for x in (0x20, 0x28, 0x30))
        if texture_count > 4096 or shader_count > 256 or material_count > 10000:
            raise ValueError('material table exceeds limits')
        texture_table = head.relative(0x24) if texture_count else 0
        shader_table = head.relative(0x2c) if shader_count else 0
        external_materials = embedded and material_count and not head.u32(0x38) and head.u32(0x34)
        if external_materials:
            external_table=head.relative(0x34)
            head.slice(external_table,material_count*60)
            for j in range(material_count):
                entry=external_table+j*60
                material_hashes[j]=head.u32(entry+40)
                material_names[j]=head.utf16(head.relative(entry+36),'be')
            material_table=0
        else:
            material_table = head.relative(0x38) if material_count else 0
        head.slice(texture_table, texture_count * 176)
        head.slice(shader_table, shader_count * 48)
        if not external_materials:head.slice(material_table, material_count * 40)
        textures = {}
        for j in range(texture_count):
            textures.setdefault(head.u32(texture_table+j*176), []).append(j)
        shaders = {head.u32(shader_table+j*48): shader_table+j*48 for j in range(shader_count)}
        # Sampler semantics, rather than parameter order, select base color.
        # Bump/normal and gloss samplers must never become a diffuse fallback.
        color_semantics = (0xb6e7ae40, 0x49412c54)
        for j in range(0 if external_materials else material_count):
            material = material_table+j*40
            material_hashes[j] = head.u32(material)
            shader_hash=head.u32(material+8)
            material_shader_modes[j]={0x9bf5d4ae:'prelit',0xad91d4de:'glow',0xb3dc3294:'flare'}.get(shader_hash)
            shader = shaders.get(shader_hash)
            if shader is None:
                continue
            uniform_count = head.u32(shader+8) >> 16
            if uniform_count > 256:
                raise ValueError('uniform table exceeds limits')
            uniforms = head.relative(shader+24) if uniform_count else 0
            head.slice(uniforms, uniform_count*44)
            # CRC32('DiffuseColor') is the runtime court color setter semantic.
            if any(head.u32(uniforms+k*44) == 0x9015351f for k in range(uniform_count)):
                diffuse_materials.add(j)
            length = head.u32(shader+12) & 0xffff
            sampler_count = head.u32(shader+8) & 0xffff
            if not length or sampler_count > 32:
                continue
            parameters = head.relative(material+32)
            head.slice(parameters, length)
            for k in range(uniform_count):
                uniform=uniforms+k*44
                if head.u32(uniform)!=0x9015351f:continue
                color_offset=head.u16(uniform+20)
                if color_offset+16>length:raise ValueError('DiffuseColor extends outside material parameters')
                color=struct.unpack('>4f',head.slice(parameters+color_offset,16))
                if not all(math.isfinite(v) and 0<=v<=1 for v in color):raise ValueError('Unsupported DiffuseColor value')
                material_colors[j]=color
            samplers = head.relative(shader+28) if sampler_count else 0
            head.slice(samplers, sampler_count*36)
            colors = {}
            for k in range(sampler_count):
                sampler = samplers+k*36
                semantic = head.u32(sampler)
                if semantic not in (*color_semantics,0xab0d0064):
                    continue
                # Sampler state begins at this declared parameter offset;
                # its texture resource hash follows the 12-byte state header.
                reference = head.u16(sampler+16)+12
                if reference+4 > length:
                    continue
                matches = textures.get(head.u32(parameters+reference), [])
                if len(matches) == 1:
                    colors[semantic] = matches[0]
            if shader_hash==0x9bf5d4ae and 0xab0d0064 in colors:
                lightmap_textures[j]=colors[0xab0d0064]
            for semantic in color_semantics:
                if semantic in colors:
                    material_textures[j] = colors[semantic]
                    break
    except ValueError as error:
        warnings.append('Automatic material textures unavailable: ' + str(error))
    for i in range(count):
        off = table + i * 0xb0
        name = f"part_{i}"
        try:
            name = head.utf16(head.relative(off), 'be')
            if not head.u32(off+0x7c):continue
            if head.u32(off + 0x84) != 1:
                raise ValueError("multiple vertex streams are unsupported")
            descriptor = head.relative(off + 0x88)
            head.slice(descriptor, 44)
            vertices = head.u32(descriptor + 16)
            stream_count = head.u32(descriptor+20) or 1
            if not 1 <= stream_count <= 16 or not 1 <= vertices <= 250000:
                raise ValueError('invalid vertex stream dimensions')
            stream_layouts=[];stream_bases=[]
            for stream_base,stream_stride in ((28,16),(36,24)):
                try:
                    candidate=[]
                    for stream in range(stream_count):
                        entry=descriptor+stream_base+stream*stream_stride
                        head.slice(entry,16)
                        stride,length=head.u32(entry+4),head.u32(entry+8)
                        if not 1<=stride<=256 or length!=vertices*stride:raise ValueError('invalid vertex buffer dimensions')
                        start=head.relative(entry+12) if embedded else head.u32(entry+12)-1
                        candidate.append((stride,payload.slice(start,length)))
                    if candidate not in stream_layouts:stream_layouts.append(candidate);stream_bases.append(stream_base)
                except ValueError:continue
            if len(stream_layouts)!=1:raise ValueError('invalid or ambiguous vertex buffer dimensions')
            streams=stream_layouts[0]
            declaration_count = head.u32(off + 0x94)
            if not 1 <= declaration_count <= 16:
                raise ValueError("unsupported vertex declaration count")
            declaration = head.relative(off + 0x9c)
            head.slice(declaration, declaration_count * 64)
            position, uv, uv_format = None, None, None
            color_decl=None;secondary_uv=None;color_format='>4f'
            position_format = ">3f"
            position_transform = uv_transform = None
            position_stream = uv_stream = 0
            for j in range(declaration_count):
                code = head.slice(declaration + j * 64 + 8, 8)
                if code[0] not in (0x20,0x30) or code[2] >= stream_count:
                    continue
                if code[3]==1 and code[4:]==bytes.fromhex('01020900'):
                    secondary_uv=(code[1],code[2],'>2h')
                    continue
                if code[3] != 0:
                    continue
                quantized = code[0] == 0x30
                transform = None
                if quantized:
                    bias=struct.unpack('>4f',head.slice(declaration+j*64+16,16))
                    scale=struct.unpack('>4f',head.slice(declaration+j*64+32,16))
                    if not all(math.isfinite(x) and abs(x)<1e8 for x in bias+scale):raise ValueError('Invalid quantized vertex transform')
                    transform=(bias,scale)
                if quantized and code[4:] == bytes.fromhex('01040000'):
                    position,position_stream=code[1],code[2]
                    position_format='>4h';position_transform=transform
                elif not quantized and code[4:] == bytes.fromhex('02030000'):
                    position, position_stream = code[1], code[2]
                elif code[4:]==bytes.fromhex('02040300'):
                    color_decl=(code[1],code[2])
                elif code[4:]==bytes.fromhex('03040300'):
                    color_decl=(code[1],code[2]);color_format='>4e'
                elif code[4:] == bytes.fromhex('03040800'):
                    uv_stream=code[2];uv,uv_format=code[1],'>4e'
                elif code[4:] == bytes.fromhex('02040800'):
                    uv_stream=code[2];uv,uv_format=code[1],'>4f'
                elif code[4:] == bytes.fromhex('03020800'):
                    uv_stream = code[2]
                    uv, uv_format = code[1], '>2e'
                elif code[4:] == bytes.fromhex('01020800'):
                    uv_stream = code[2]
                    uv, uv_format = code[1], '>2h'
                    uv_transform=transform
                elif code[4:] == bytes.fromhex('02020800'):
                    uv_stream = code[2]
                    uv, uv_format = code[1], '>2f'
            position_stride, position_data = streams[position_stream]
            uv_stride, uv_data = streams[uv_stream]
            if position is None or position + struct.calcsize(position_format) > position_stride:
                raise ValueError("position declaration is unsupported")
            if uv is None or uv + struct.calcsize(uv_format) > uv_stride:
                raise ValueError("UV declaration is unsupported")
            points = []
            for v in range(vertices):
                xyz = struct.unpack_from(position_format, position_data, v * position_stride + position)[:3]
                if position_transform:
                    bias,scale=position_transform
                    xyz=tuple(max(-1.,x/32767.)*scale[k]+bias[k] for k,x in enumerate(xyz))
                tex = struct.unpack_from(uv_format, uv_data, v * uv_stride + uv)[:2]
                if uv_format == '>2h':
                    tex = tuple(max(-1., x/32767.) for x in tex)
                    if uv_transform:
                        bias,scale=uv_transform
                        tex=tuple(x*scale[k]+bias[k] for k,x in enumerate(tex))
                if not all(math.isfinite(x) and abs(x) < 1e8 for x in xyz + tex):
                    raise ValueError("non-finite or excessive vertex values")
                extra=()
                if color_decl or secondary_uv:
                    color=(1.,1.,1.,1.);tex1=tex
                    if color_decl:
                        color_offset,color_stream=color_decl;stride,data=streams[color_stream]
                        if color_offset+struct.calcsize(color_format)>stride:raise ValueError('Color declaration exceeds vertex stride')
                        color=struct.unpack_from(color_format,data,v*stride+color_offset)
                    if secondary_uv:
                        uv_offset,uv_index,fmt=secondary_uv;stride,data=streams[uv_index]
                        if uv_offset+4>stride:raise ValueError('Lightmap UV exceeds vertex stride')
                        tex1=tuple(max(-1.,x/32767.) for x in struct.unpack_from(fmt,data,v*stride+uv_offset))
                    if not all(math.isfinite(x) and abs(x)<1e8 for x in (*color,*tex1)):
                        raise ValueError('Invalid vertex colour/lightmap coordinates')
                    extra=(*color,*tex1)
                points.append(xyz + tex + extra)
            if head.u32(off + 0xa4) != (0x10 if embedded else 0x20000010):
                raise ValueError("index format is unsupported")
            index_count = head.u32(off + 0xa8)
            if index_count > 2000000:
                raise ValueError("index count exceeds preview limit")
            index_start = head.relative(off+0xac) if embedded else head.u32(off+0xac)-1
            index_data = payload.slice(index_start, index_count*2)
            indices = struct.unpack('>' + str(index_count) + 'H', index_data)
            runs = head.u32(off + 0x7c)
            if not 1 <= runs <= 10000:
                raise ValueError("unsupported draw count")
            draw = head.relative(off + 0x80)
            draw_layouts=[]
            for draw_stride in (48,64):
                try:
                    head.slice(draw,runs*draw_stride)
                    if all(head.u32(draw+j*draw_stride)==6 and head.u32(draw+j*draw_stride+4)+head.u32(draw+j*draw_stride+8)<=index_count for j in range(runs)):
                        draw_layouts.append(draw_stride)
                except ValueError:continue
            if not draw_layouts:raise ValueError('unsupported draw topology or index range')
            if len(draw_layouts)>1 and runs>1:raise ValueError('ambiguous draw record layout')
            draw_stride=64 if runs==1 and stream_bases[0]==36 and 64 in draw_layouts else draw_layouts[0]
            triangles = []
            batches = []
            for j in range(runs):
                batch_start = len(triangles)
                run = draw + j * draw_stride
                primitive, first, size = (head.u32(run + k) for k in (0, 4, 8))
                if primitive != 6 or first + size > index_count:
                    raise ValueError("unsupported draw topology or index range")
                strip = []
                for index in indices[first:first + size]:
                    if index == 0xffff:
                        strip = []
                        continue
                    if index >= vertices:
                        raise ValueError("index outside vertex buffer")
                    strip.append(index)
                    if len(strip) >= 3:
                        a, b, c = strip[-3:]
                        if len(strip) % 2 == 0:
                            a, b = b, a
                        if len({a, b, c}) == 3:
                            triangles.extend((points[a], points[b], points[c]))
                if len(triangles) > batch_start:
                    material_index=head.u16(run+32) if draw_stride==64 else head.u32(run+32)
                    batches.append({'first': batch_start, 'count': len(triangles)-batch_start,
                                    'texture_index': material_textures.get(material_index),
                                    'material_index': material_index,
                                    'lightmap_index':lightmap_textures.get(material_index) if secondary_uv else None,
                                    'shader_mode':material_shader_modes.get(material_index) if color_decl else None,
                                    'material_name': material_names.get(material_index),
                                    'material_hash': material_hashes.get(material_index),
                                    'supports_diffuse_color': material_index in diffuse_materials,
                                    'diffuse_color':material_colors.get(material_index)})
                if total_vertices + len(triangles) > 1500000:
                    raise ValueError("scene exceeds preview triangle budget")
            if triangles:
                total_vertices += len(triangles)
                matrices = transforms.get(head.u32(off+4), [None])
                for instance_index, matrix in enumerate(matrices):
                    placed = triangles if matrix is None else [
                        tuple(sum(matrix[row+column*4]*vertex[column] for column in range(3))+matrix[row+12] for row in range(3)) + vertex[3:]
                        for vertex in triangles
                    ]
                    if total_vertices + (len(matrices)-1)*len(triangles) > 1500000:
                        raise ValueError('Instanced scene exceeds preview triangle budget')
                    meshes.append({'name': name if len(matrices)==1 else f'{name} instance {instance_index}',
                                   'vertices': placed, 'batches': batches,
                                   'hidden_by_default': name.lower().startswith('light_fx') or 'roof' in name.lower()})
                total_vertices += (len(matrices)-1)*len(triangles)
        except (ValueError, struct.error) as error:
            warnings.append(f"{name}: {error}")
    return {'meshes': meshes, 'warnings': warnings}
