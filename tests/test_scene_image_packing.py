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
