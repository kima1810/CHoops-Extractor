import io
import struct
from PIL import Image
import pytest
from choops_py.texture_tools import dds
from choops_py.texture_tools.runtime_layout import conform
from choops_py.texture_tools.override_import import apply_dds
from choops_py.formats.txtr import TXTR
from support import txtr_fixture
from choops_py.texture_tools.archive_layout import normalize_record,stadium_archive


def artwork(width,height,color):
    output=io.BytesIO();Image.new('RGBA',(width,height),color).save(output,format='DDS')
    return output.getvalue()


def test_core_artwork_keeps_storage_dimensions_and_complete_small_mips():
    source=artwork(32,16,(0,0,255,255))
    layout=dict(width=8,height=4,format='DXT5',mip_count=4,cubemap=False)
    result,changed=conform(source,layout)
    assert changed and all(dds.inspect(result)[k]==v for k,v in layout.items())
    with Image.open(io.BytesIO(result)) as image:
        assert image.convert('RGBA').getpixel((0,0))==(0,0,255,255)
    assert len(result)==128+dds.image_size(8,4,'DXT5',4)


def test_matching_layout_keeps_artwork_bytes_exact():
    source=artwork(8,4,(11,22,33,44));layout=dds.inspect(source)
    assert conform(source,layout)==(source,False)


def test_core_dds_import_preserves_entire_header_and_payload_capacity(tmp_path):
    parts=txtr_fixture(format=0x86,split=True)
    header=bytearray(parts[0]);struct.pack_into('>3H',header,0x90,4,4,1)
    parts=[bytes(header),parts[1]]
    path=tmp_path/'replacement.dds';source=artwork(32,32,(0,0,255,255));path.write_bytes(source)
    result,report=apply_dds(parts,'TXTR','artwork',path,preserve_layout=True)
    assert result[0]==parts[0]
    assert list(map(len,result))==list(map(len,parts))
    assert TXTR(result).info()['format']=='DXT1'
    assert report['storage_layout_preserved'] and report['artwork_resampled']
    assert report['input_layout']['width']==32 and report['width']==4
    assert path.read_bytes()==source


def test_raw_texture_override_returns_to_base_size_and_keeps_artwork(tmp_path):
    base=txtr_fixture(format=0x86,split=True)
    enlarged,_=apply_dds(base,'TXTR','texture',artwork(32,32,(0,0,255,255)))
    normalized,reports=normalize_record(enlarged,base,'TXTR')
    assert normalized[0]==base[0]
    assert len(normalized[1])==len(base[1])
    assert reports[0]['width']==4
    from choops_py.texture_tools.builtin_converter import to_dds
    with Image.open(io.BytesIO(to_dds(TXTR(normalized).gtf()))) as image:
        assert image.convert('RGBA').getpixel((0,0))==(0,0,255,255)


def test_inline_override_restores_base_pointer_and_trailing_data():
    base=txtr_fixture(format=0x86)
    enlarged,_=apply_dds(base,'TXTR','texture',artwork(32,32,(0,0,255,255)))
    result,_=normalize_record(enlarged,base,'TXTR')
    assert len(result[0])==len(base[0]) and result[0].endswith(b'KEEP')
    assert TXTR(result).info()['payload_offset']==TXTR(base).info()['payload_offset']


def test_half_float_downsizing_retains_hdr_and_negative_values():
    header=bytearray(128);header[:4]=b'DDS '
    for off,value in {4:124,8:0x81007,12:4,16:4,20:128,76:32,80:4,84:113,108:0x1000}.items():struct.pack_into('<I',header,off,value)
    source=bytes(header)+struct.pack('<4e',2.,-1.,.5,1.)*16
    layout=dict(width=2,height=2,format='RGBA16F',mip_count=2,cubemap=False)
    result,changed=conform(source,layout)
    assert changed and len(result)==128+40
    assert all(pixel==(2.,-1.,.5,1.) for pixel in struct.iter_unpack('<4e',result[128:]))


def test_stadium_exception_covers_names_and_hashes():
    from choops_py.archive.hash_names import replacement_hash
    assert stadium_archive(dict(name='S258.iff',entry={'hash':replacement_hash('s258.iff')}))
    assert stadium_archive(dict(name='hash.iff',entry={'hash':replacement_hash('s258.iff')}))
    assert not stadium_archive(dict(name='ua258.iff',entry={'hash':replacement_hash('ua258.iff')}))


def test_complete_iff_replacement_is_normalized_without_loose_dds(tmp_path):
    from support import iff_fixture
    from choops_py.archive.folder_import import compile_group
    from choops_py.archive.hash_names import replacement_hash
    from choops_py.formats.standard_iff import StandardIFF
    from choops_py.formats.standard_iff_writer import record_blocks
    base=txtr_fixture(format=0x86,split=True)
    large,_=apply_dds(base,'TXTR','texture',artwork(32,32,(0,0,255,255)))
    def bank(parts):
        raw=bytearray(iff_fixture(parts,[(0x5c369069,[0,0])]))
        struct.pack_into('>I',raw,64,0x411536d5)
        return bytes(raw)
    source=bank(base)
    path=tmp_path/'global.iff';path.write_bytes(bank(large))
    class MemoryArchive:
        def read(self,entry):return source
    group=dict(name='global.iff',entry=dict(hash=replacement_hash('global.iff')),whole=path,records={},dds={},package_records={})
    result,details=compile_group(MemoryArchive(),group);iff=StandardIFF(result)
    parts=[row[3] for row in record_blocks(iff,iff.records[0])]
    assert parts[0]==base[0] and len(parts[1])==len(base[1])
    assert details[0]['storage_layout_preserved']


def test_oversized_artwork_is_reduced_before_graphics_limit_check():
    base=txtr_fixture(format=0x86,split=True);source=artwork(8192,4,(0,0,255,255))
    result,_=apply_dds(base,'TXTR','texture',source,preserve_layout=True)
    assert TXTR(result).info()['width']==4
    with pytest.raises(ValueError,match='4096'):apply_dds(base,'TXTR','texture',source)


def test_court_zip_cannot_escape_the_output_folder(tmp_path):
    import zipfile
    from choops_py.modding.court_template import prepare
    source=tmp_path/'court.zip'
    with zipfile.ZipFile(source,'w') as archive:archive.writestr('../floor.scne',b'not a scene')
    with pytest.raises(ValueError,match='All outputs must be under project output'):prepare(source,tmp_path/'result')
    assert not (tmp_path/'floor.scne').exists()


def test_dds_supersedes_invalid_legacy_raw_header_using_valid_base():
    base=txtr_fixture(format=0x86,split=True);raw=[bytearray(base[0]),base[1]]
    raw[0][0x5a]=3  # Discarded raw volume header; the base/DDS are 2D.
    result,report=apply_dds(raw,'TXTR','texture',artwork(16,16,(0,0,255,255)),preserve_layout=True,reference=TXTR(base))
    assert result[0]==base[0] and TXTR(result).info()['width']==4
    assert report['storage_layout_preserved']


@pytest.mark.parametrize('stored_depth',[0,1,7])
def test_2d_stored_depth_does_not_turn_menu_art_into_a_volume(stored_depth):
    base=txtr_fixture(format=0x86,split=True);head=bytearray(base[0]);struct.pack_into('>H',head,0x64,stored_depth);base=[bytes(head),base[1]]
    result,_=apply_dds(base,'TXTR','menu',artwork(16,16,(0,0,255,255)),preserve_layout=True,reference=TXTR(base))
    assert result[0]==base[0] and TXTR(result).info()['width']==4


def test_real_volume_dimension_remains_rejected():
    base=txtr_fixture(format=0x86,split=True);head=bytearray(base[0]);head[0x5a]=3
    with pytest.raises(ValueError,match='dimension=3'):TXTR([bytes(head),base[1]]).info()
