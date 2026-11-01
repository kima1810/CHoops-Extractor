import struct
import pytest
from support import txtr_fixture
from choops_py.formats.package import repack_images,textures
from choops_py.formats.txtr import TXTR
from choops_py.texture_tools.override_import import apply_raw_texture


def fixture():
    header=bytearray(640);texture=txtr_fixture(format=0x86,split=True)
    struct.pack_into('>II',header,0x20,1,128-0x24+1)
    header[128:304]=texture[0];struct.pack_into('>I',header,128+0xa4,1)
    struct.pack_into('>II',header,0x44,1,304-0x48+1)
    struct.pack_into('>II',header,304+0x84,1,480-(304+0x88)+1)
    struct.pack_into('>I',header,500,2)
    struct.pack_into('>4I',header,508,0,4,16,129)
    struct.pack_into('>4I',header,524,0,4,16,257)
    struct.pack_into('>II',header,304+0xa8,4,385)
    payload=bytearray(400);payload[:8]=texture[1][:8]
    payload[128:144]=b'FIRST STREAM!!!!';payload[256:272]=b'SECOND STREAM!!!';payload[384:392]=b'INDICES!'
    return [bytes(header),bytes(payload)]


def test_images_grow_and_shrink_without_changing_either_vertex_stream():
    original=fixture();new=txtr_fixture(format=0x88,width=32,height=32,split=True)
    imported=apply_raw_texture(original,'texture_0',new)
    packed=repack_images(original,imported)
    assert TXTR([textures(packed)[0].header,textures(packed)[0].payload]).image()==TXTR(new).image()
    for field,expected in [(520,b'FIRST STREAM!!!!'),(536,b'SECOND STREAM!!!'),(304+0xac,b'INDICES!')]:
        start=struct.unpack_from('>I',packed[0],field)[0]-1
        assert start%128==0 and packed[1][start:start+len(expected)]==expected
    restored=apply_raw_texture(packed,'texture_0',txtr_fixture(format=0x86,split=True))
    small=repack_images(packed,restored)
    assert len(small[1])<len(packed[1])


def test_geometry_overlap_fails_closed():
    original=fixture();header=bytearray(original[0]);struct.pack_into('>I',header,520,1)
    with pytest.raises(ValueError,match='Geometry overlaps'):repack_images([bytes(header),original[1]],[bytes(header),original[1]])


def test_non_stadium_import_removes_old_oversized_images(tmp_path):
    import io
    from PIL import Image
    from support import iff_fixture
    from choops_py.archive.folder_import import compile_group
    from choops_py.archive.hash_names import replacement_hash
    from choops_py.formats.cdf_backed_iff_writer import name_trailer
    from choops_py.formats.standard_iff import StandardIFF
    from choops_py.formats.standard_iff_writer import record_blocks
    from choops_py.formats.tool_wrapper import wrap
    original=fixture()
    raw=repack_images(original,apply_raw_texture(original,'texture_0',txtr_fixture(format=0x88,width=32,height=32,split=True)))
    source=iff_fixture(original,[(0xe26c9b5d,[0,0])])+name_trailer([dict(name='scene',type='SCNE')])
    entry=dict(name='global.iff',hash=replacement_hash('global.iff'))
    class MemoryArchive:
        def read(self,entry):return source
    replacement=tmp_path/'scene.scne';replacement.write_bytes(wrap(2,raw))
    artwork=tmp_path/'texture_0.dds';output=io.BytesIO();Image.new('RGBA',(64,64),(0,0,255,255)).save(output,format='DDS');artwork.write_bytes(output.getvalue())
    group=dict(entry=entry,name='global.iff',whole=None,records={('scene','SCNE'):replacement},package_records={},dds={'scene/texture_0':artwork})
    result,_=compile_group(MemoryArchive(),group);iff=StandardIFF(result)
    blocks=[r[3] for r in record_blocks(iff,iff.records[0])]
    # Retain unclassified source padding; the obsolete 1 KiB image is removed.
    assert len(blocks[1])<=len(original[1])+128 and len(blocks[1])<len(raw[1])
    item=textures(blocks)[0];assert TXTR([item.header,item.payload]).info()['width']==4
    for field,expected in [(520,b'FIRST STREAM!!!!'),(536,b'SECOND STREAM!!!'),(304+0xac,b'INDICES!')]:
        start=struct.unpack_from('>I',blocks[0],field)[0]-1
        assert blocks[1][start:start+len(expected)]==expected


def inline_fixture():
    original=fixture();header=bytearray(original[0]);payload=original[1]
    for field,flags,length in [(520,0x40000002,16),(536,0x40000002,16),(304+0xac,0x10,8)]:
        start=struct.unpack_from('>I',header,field)[0]-1
        target=len(header);header.extend(payload[start:start+length])
        struct.pack_into('>I',header,field,target-field+1)
        struct.pack_into('>I',header,field-12 if field in (520,536) else 304+0xa4,flags)
    return [bytes(header),payload]


def test_inline_menu_geometry_is_not_confused_with_texture_payload():
    original=inline_fixture()
    imported=apply_raw_texture(original,'texture_0',txtr_fixture(format=0x88,width=32,height=32,split=True))
    packed=repack_images(original,imported)
    assert packed[0][304:]==original[0][304:]
    for field,expected in [(520,b'FIRST STREAM!!!!'),(536,b'SECOND STREAM!!!'),(304+0xac,b'INDICES!')]:
        start=field+struct.unpack_from('>I',packed[0],field)[0]-1
        assert packed[0][start:start+len(expected)]==expected
    assert TXTR([textures(packed)[0].header,textures(packed)[0].payload]).info()['width']==32


def test_inline_geometry_changes_and_bad_ranges_still_fail_closed():
    original=inline_fixture();changed=[bytearray(original[0]),original[1]]
    changed[0][-1]^=1
    with pytest.raises(ValueError,match='Inline geometry changed'):
        repack_images(original,[bytes(changed[0]),changed[1]])
    head=bytearray(original[0]);struct.pack_into('>I',head,520,0x7fffffff)
    with pytest.raises(ValueError):repack_images([bytes(head),original[1]],[bytes(head),original[1]])


def test_menu_gpu_stream_flag_remains_data_relative():
    original=fixture();head=bytearray(original[0])
    for field in (508,524):struct.pack_into('>I',head,field,0x40000003)
    struct.pack_into('>I',head,304+0xa4,0x20000010)
    original=[bytes(head),original[1]]
    imported=apply_raw_texture(original,'texture_0',txtr_fixture(format=0x88,width=32,height=32,split=True))
    packed=repack_images(original,imported)
    for field,expected in [(520,b'FIRST STREAM!!!!'),(536,b'SECOND STREAM!!!'),(304+0xac,b'INDICES!')]:
        start=struct.unpack_from('>I',packed[0],field)[0]-1
        assert packed[1][start:start+len(expected)]==expected
