import struct
import pytest
from choops_py.formats.scne import preview_meshes


def scene_fixture():
    head = bytearray(1024)
    def u(off, value): struct.pack_into('>I', head, off, value)
    def pointer(field, target): u(field, target-field+1)
    u(0x44, 1); pointer(0x48, 0x54)
    off = 0x54
    pointer(off, 900); head[900:910] = 'mesh\0'.encode('utf-16-be')
    u(off+0x84, 1); pointer(off+0x88, 300)
    u(316, 4); u(332, 16); u(336, 64); u(340, 9)
    u(off+0x94, 2); pointer(off+0x9c, 400)
    head[408:416] = bytes.fromhex('2000000002030000')
    head[472:480] = bytes.fromhex('200c000003020800')
    u(off+0xa4, 0x20000010); u(off+0xa8, 4); u(off+0xac, 1)
    u(off+0x7c, 1); pointer(off+0x80, 600)
    u(600, 6); u(604, 0); u(608, 4)
    vertices = [(-1.,0.,-1.,0.,0.), (1.,0.,-1.,1.,0.), (-1.,0.,1.,0.,1.), (1.,0.,1.,1.,1.)]
    data = struct.pack('>4H', 0,1,2,3) + b''.join(struct.pack('>3f2e',*v) for v in vertices)
    return [bytes(head), data]


def test_declared_mesh_strip_winding_and_uv():
    result = preview_meshes(scene_fixture())
    assert result['warnings'] == []
    vertices = result['meshes'][0]['vertices']
    assert len(vertices) == 6
    assert vertices[0] == (-1.,0.,-1.,0.,0.)
    assert vertices[3] == (-1.,0.,1.,0.,1.)
    assert vertices[4] == (1.,0.,-1.,1.,0.)


def test_invalid_indices_skip_part_instead_of_guessing():
    head, data = scene_fixture()
    data = struct.pack('>H',99) + data[2:]
    result = preview_meshes([head,data])
    assert not result['meshes']
    assert 'index outside' in result['warnings'][0]


def test_bad_declaration_and_truncated_payload_are_reported():
    head, data = scene_fixture()
    modified = bytearray(head); modified[412:416] = b'BAD!'
    assert not preview_meshes([bytes(modified),data])['meshes']
    assert not preview_meshes([head,data[:-1]])['meshes']
    assert not preview_meshes([head])['meshes']


def test_instance_matrix_places_geometry_without_changing_uv():
    head, data = scene_fixture()
    head = bytearray(head)
    struct.pack_into('>I',head,0x3c,1)
    struct.pack_into('>I',head,0x40,700-0x40+1)
    struct.pack_into('>16f',head,700,2,0,0,0,0,2,0,0,0,0,2,0,10,20,30,1)
    result = preview_meshes([bytes(head),data])
    assert result['meshes'][0]['vertices'][0] == (8.,20.,28.,0.,0.)


def test_signed_normalized_uvs():
    head,data = scene_fixture()
    head = bytearray(head);head[476:480] = bytes.fromhex('01020800')
    data = bytearray(data)
    struct.pack_into('>2h',data,8+12,32767,0)
    result = preview_meshes([bytes(head),bytes(data)])
    assert result['meshes'][0]['vertices'][0][3:] == (1.,0.)


def material_fixture(base_hash=0x12345678):
    head,data = scene_fixture()
    head = bytearray(head)+bytearray(3072)
    def u(off,value): struct.pack_into('>I',head,off,value)
    def ptr(field,target):u(field,target-field+1)
    u(0x20,2);ptr(0x24,1024);u(1024,0x12345678);u(1200,0x87654321)
    u(0x28,1);ptr(0x2c,1400);u(1400,0x11111111);u(1408,2);u(1412,96);ptr(1428,1600)
    u(0x30,1);ptr(0x38,1480);u(1488,0x11111111);ptr(1512,1800)
    # Put the normal map first in parameter memory and the sampler table.
    u(1600,0xab0d0064);struct.pack_into('>H',head,1616,0)
    u(1636,0xb6e7ae40);struct.pack_into('>H',head,1652,20)
    u(1812,0x87654321);u(1832,base_hash)
    return [bytes(head),data]


def test_material_reference_resolves_diffuse_not_first_normal_map():
    result=preview_meshes(material_fixture())
    assert result['meshes'][0]['batches'][0]['texture_index'] == 0
    assert result['meshes'][0]['batches'][0]['count'] == 6


def test_missing_diffuse_never_falls_back_to_embedded_normal_map():
    result=preview_meshes(material_fixture(base_hash=0x99999999))
    assert result['meshes'][0]['batches'][0]['texture_index'] is None


def test_non_power_of_two_compressed_texture_preview():
    import io
    from PIL import Image
    from choops_py.texture_tools.dds import compressed_preview
    # Opaque red DXT5 blocks; final block row extends past the logical image.
    block = bytes.fromhex('ffff000000000000') + bytes.fromhex('00f800f800000000')
    raw = compressed_preview(8,5,'DXT5',block*4)
    with Image.open(io.BytesIO(raw)) as image:
        assert image.size == (8,5)
        assert image.convert('RGBA').getpixel((7,4)) == (255,0,0,255)


@pytest.mark.gui
def test_court_layers_preserve_geometry_and_do_not_bias_arena(qtbot):
    from choops_py.studio.scene_view import SceneView
    view = SceneView();qtbot.addWidget(view)
    original = [(0.,0.,0.,0.,0.)]*3
    meshes = [{'name':'floor/'+name, 'court_surface':True, 'vertices':original}
              for name in ('floor','paint','|centerlogo','lines')]
    meshes.append({'name':'arena/floor','vertices':original})
    view.set_meshes(meshes)
    assert [b['court_layer'] for b in view.batches] == [1,2,3,4,0]
    assert view.vertices == original*5


@pytest.mark.gui
def test_camera_keyboard_travels_in_view_direction(qtbot):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QVector3D
    from choops_py.studio.scene_view import SceneView
    view = SceneView();qtbot.addWidget(view)
    view.yaw = 0.;view.pitch = 0.;view.radius = 100.
    qtbot.keyClick(view, Qt.Key.Key_W)
    assert view.center == QVector3D(0,0,-2.5)
    qtbot.keyClick(view, Qt.Key.Key_D, modifier=Qt.KeyboardModifier.ShiftModifier)
    assert view.center == QVector3D(10,0,-2.5)
    qtbot.keyClick(view, Qt.Key.Key_E)
    assert view.center == QVector3D(10,2.5,-2.5)


def embedded_scene_fixture():
    head, payload = scene_fixture()
    head = bytearray(head)+bytearray(128)
    head[:4] = bytes.fromhex("00010b1d")
    def u(off,value):struct.pack_into('>I',head,off,value)
    def ptr(field,target):u(field,target-field+1)
    u(320,2)
    u(332,12);u(336,48);ptr(340,1040)
    u(344,0);u(348,4);u(352,16);ptr(356,1088)
    head[408:416] = bytes.fromhex('2000000002030000')
    head[472:480] = bytes.fromhex('2000010003020800')
    u(0x54+0xa4,0x10);ptr(0x54+0xac,1024)
    head[1024:1032] = payload[:8]
    for i in range(4):
        head[1040+i*12:1052+i*12] = payload[8+i*16:20+i*16]
        head[1088+i*4:1092+i*4] = payload[20+i*16:24+i*16]
    return bytes(head)


def test_embedded_multistream_matches_two_block_geometry():
    result = preview_meshes([embedded_scene_fixture()])
    assert not result['warnings']
    assert result['meshes'][0]['vertices'] == preview_meshes(scene_fixture())['meshes'][0]['vertices']


def test_standalone_embedded_scne_preview(tmp_path):
    from choops_py.studio.services import inspect_scene_preview
    from choops_py.formats.tool_wrapper import wrap
    raw = embedded_scene_fixture()
    for name,data in [('cloth.scne',raw),('cloth_wrapped.scne',wrap(2,[raw]))]:
        source=tmp_path/name;source.write_bytes(data)
        result=inspect_scene_preview(source,0)
        assert len(result['meshes']) == 1
        assert len(result['meshes'][0]['vertices']) == 6


def test_quantized_shoe_positions_and_uv_transform():
    head,data=scene_fixture();head=bytearray(head)
    head[408:416]=bytes.fromhex('3000000001040000')
    head[472:480]=bytes.fromhex('3008000001020800')
    struct.pack_into('>4f',head,416,10,20,30,0);struct.pack_into('>4f',head,432,2,3,4,1)
    struct.pack_into('>4f',head,480,.5,.5,0,0);struct.pack_into('>4f',head,496,.5,.5,1,1)
    packed=[(-32768,0,-32768,32767,-32768,-32768),(32767,0,-32768,32767,32767,-32768),
            (-32768,0,32767,32767,-32768,32767),(32767,0,32767,32767,32767,32767)]
    data=data[:8]+b''.join(struct.pack('>6hI',*v,0) for v in packed)
    result=preview_meshes([bytes(head),data])
    assert not result['warnings']
    vertices=result['meshes'][0]['vertices']
    assert vertices[0]==(8.,20.,26.,0.,0.) and vertices[1]==(12.,20.,26.,1.,0.)
    struct.pack_into('>f',head,432,float('nan'))
    assert not preview_meshes([bytes(head),data])['meshes']


def test_embedded_external_material_names_are_decoded():
    head,data=scene_fixture();head=bytearray(head)
    struct.pack_into('>I',head,0x30,1);struct.pack_into('>I',head,0x34,700-0x34+1)
    struct.pack_into('>I',head,736,780-736+1)
    head[780:798]='sole_mat\0'.encode('utf-16-be')
    off=0x54
    struct.pack_into('>I',head,340,1032-340+1)
    struct.pack_into('>I',head,off+0xa4,0x10)
    struct.pack_into('>I',head,off+0xac,1024-(off+0xac)+1)
    result=preview_meshes([bytes(head)+data])
    assert not result['warnings']
    assert result['meshes'][0]['batches'][0]['material_name']=='sole_mat'
