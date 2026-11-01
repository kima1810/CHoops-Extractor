import struct
import zlib

import pytest

from support import iff_fixture
from test_scene_preview import scene_fixture
from choops_py.formats.compression import decode,encode_like,encode_greedy
from choops_py.formats.standard_iff import StandardIFF
from choops_py.formats.standard_iff_writer import record_blocks,replace_records_expanding
from choops_py.formats.scne import preview_meshes


def wrapped(data):
    compressed=zlib.compress(data)
    return b'ZLIB'+struct.pack('>III',len(data),len(compressed)+16,6)+compressed


def test_zlib_strict_bounds_and_logical_replacement_roundtrip():
    data=b'NBA synthetic roster'*300;raw=wrapped(data)
    assert decode(raw,len(data))==data
    for encoder in (encode_like,encode_greedy):
        replacement=b'Changed synthetic roster'*350
        encoded=encoder(raw,replacement)
        assert encoded[:4]==b'ZLIB' and decode(encoded)==replacement
        assert encoded[12:16]==raw[12:16]
    for bad in (raw[:-1],raw+b'EXTRA',raw[:4]+struct.pack('>I',len(data)-1)+raw[8:]):
        with pytest.raises(ValueError):decode(bad)
    with pytest.raises(ValueError):decode(raw,len(data)+1)


def test_extended_iff_record_pointer_table_read_only_writer():
    raw=bytearray(iff_fixture([b'abcdefgh'],[(0xc61649b2,[0])]))
    raw[64:64]=bytes(16)
    for off in (4,8,52):struct.pack_into('>I',raw,off,struct.unpack_from('>I',raw,off)[0]+16)
    struct.pack_into('>I',raw,28,80-28+1)
    iff=StandardIFF(bytes(raw))
    assert iff.record_table==80 and record_blocks(iff,iff.records[0])[0][3]==b'abcdefgh'
    with pytest.raises(ValueError,match='Extended IFF'):replace_records_expanding(iff,{0:[b'ABCDEFGH']})


def test_new_vertex_and_64_byte_draw_layout_preserve_material_indices():
    header,data=scene_fixture();header=bytearray(header)
    for off,value in [(324,13),(328,1),(332,0x21c00000),(336,0x03000000),(340,16),(344,64),(348,9)]:struct.pack_into('>I',header,off,value)
    part=0x54;struct.pack_into('>I',header,part+0x7c,2)
    for run,material in [(600,5),(664,2)]:
        struct.pack_into('>3I',header,run,6,0,4);struct.pack_into('>I',header,run+32,material<<16)
    result=preview_meshes([bytes(header),data])
    assert not result['warnings'] and len(result['meshes'][0]['vertices'])==12
    assert [b['material_index'] for b in result['meshes'][0]['batches']]==[5,2]


def test_128_byte_instance_layout_places_both_instances():
    header,data=scene_fixture();header=bytearray(header)
    struct.pack_into('>II',header,0x3c,2,700-0x40+1)
    for off,x in [(700,10),(828,20)]:struct.pack_into('>16f',header,off,1,0,0,0,0,1,0,0,0,0,1,0,x,0,0,1)
    result=preview_meshes([bytes(header),data])
    assert not result['warnings'] and len(result['meshes'])==2
    assert [m['vertices'][0][0] for m in result['meshes']]==[9,19]
