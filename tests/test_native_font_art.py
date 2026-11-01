import io
import struct

import pytest
from PIL import Image

from choops_py.modding import native_font_art as font


def fixture(monkeypatch):
    head=bytearray(512)
    struct.pack_into('>HHI',head,0,65,66,1)
    struct.pack_into('>I',head,8,33)  # relative map at 40
    struct.pack_into('>I',head,12,3)
    struct.pack_into('>HHI',head,40,65,66,9)  # glyphs at 52
    for i in range(2):
        at=52+i*96;struct.pack_into('>I',head,at,5)
        for j,(x,y) in enumerate([(1,1),(3,1),(1,3),(3,3)]):
            struct.pack_into('>4f',head,at+16+j*16,x,y,0,0)
        struct.pack_into('>4f',head,at+80,0,0,.5,.5)
    atlas=Image.new('RGB',(4,4),(0,200,0));buf=io.BytesIO();atlas.save(buf,format='DDS')
    class Atlas:
        def __init__(self,parts):pass
        def gtf(self):return b'fixture'
    monkeypatch.setattr(font,'TXTR',Atlas)
    monkeypatch.setattr(font,'to_dds',lambda _:buf.getvalue())
    return [bytes(head),b'payload']


def test_native_bearings_advances_space_and_green_coverage(monkeypatch):
    source=fixture(monkeypatch);image=font.render_line(source,'A B')
    assert image.size==(13,3)
    assert image.getpixel((1,1))==(255,255,255,200)
    assert image.getpixel((9,1))==(255,255,255,200)
    assert image.getpixel((6,1))[3]==0
    with pytest.raises(ValueError,match='absent'):font.render_line(source,'C')


def test_bad_native_font_metrics_are_rejected(monkeypatch):
    source=fixture(monkeypatch);head=bytearray(source[0])
    struct.pack_into('>f',head,52+80,float('nan'))
    with pytest.raises(ValueError,match='metrics'):font.render_line([bytes(head),source[1]],'A')
    with pytest.raises(ValueError,match='header'):font.render_line([source[0]],'A')
