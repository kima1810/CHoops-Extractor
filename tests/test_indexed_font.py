import struct
import pytest
from PIL import Image
from choops_py.formats.txtr import TXTR
from choops_py.formats.indexed_font import atlas,number_metrics,number_image,number_uv
from support import txtr_fixture

pytestmark=pytest.mark.unit


def test_number_uv_uses_authored_placement_and_rejects_invalid_extent():
    data=bytearray(96);struct.pack_into('>4f',data,0x1c,.25,.75,.5,.25)
    uv=number_uv(data)
    assert uv==(2,4,0,-2.5)
    assert .25*uv[0]+uv[2]==.5 and .75*uv[1]+uv[3]==.5
    struct.pack_into('>f',data,0x24,0)
    with pytest.raises(ValueError):number_uv(data)


def test_indexed_atlas_uses_argb_palette_and_preserves_alpha():
    blocks=txtr_fixture(format=0xa1,width=4,height=4,split=True)
    header=bytearray(blocks[0]);struct.pack_into('>I',header,0x5c,0x5500)
    pixels=b'\x00\x01\x02\x01'*4
    colors=[(0,10,20,30),(255,200,100,50),(64,5,6,7)]+[(0,0,0,0)]*253
    palette=b''.join(bytes(c) for c in colors)
    original=[bytes(header),pixels+palette]
    image=atlas(TXTR(original))
    assert image.getpixel((0,0))==(10,20,30,0)
    assert image.getpixel((1,0))==(200,100,50,255)
    assert image.getpixel((2,0))==(5,6,7,64)
    assert original==[bytes(header),pixels+palette]
    with pytest.raises(ValueError,match='palette'):
        atlas(TXTR([bytes(header),pixels]))


def test_number_composition_uses_metrics_alignment_and_00():
    image=Image.new('RGBA',(80,4),(10,20,30,0))
    metrics=[(i*8,5) for i in range(10)]
    for digit in range(10):
        for x in range(digit*8,digit*8+5):
            for y in range(4):image.putpixel((x,y),(digit*20,30,40,255))
    raw=b''.join(struct.pack('>2H',*m) for m in metrics)
    assert number_metrics(raw,80)==metrics
    single=number_image(image,metrics,7,(32,8))
    assert single.getpixel((13,0))==(140,30,40,255)
    assert single.getpixel((0,0))[3]==0
    double=number_image(image,metrics,100,(32,8))
    assert double.getpixel((11,0))==(0,30,40,255)
    assert double.getpixel((19,0))==(0,30,40,255)
    with pytest.raises(ValueError):number_image(image,metrics,101)
    with pytest.raises(ValueError):number_metrics(b'\0'*40,80)


def test_surname_metrics_case_mapping_spacing_and_placement():
    from choops_py.formats.indexed_font import name_metrics,name_image,name_placement
    image=Image.new('RGBA',(224,4),(10,20,30,0))
    metrics=[(i*8,5) for i in range(28)]
    for index in range(28):
        for x in range(index*8,index*8+5):
            for y in range(4):image.putpixel((x,y),(index*8,30,40,255))
    assert name_metrics(b''.join(struct.pack('>2H',*m) for m in metrics),224)==metrics
    reborn=name_image(image,metrics,'Reborn',(256,8))
    assert reborn.tobytes()==name_image(image,metrics,'REBORN',(256,8)).tobytes()
    assert reborn.getpixel((64,0))==(19*8,30,40,255)
    assert reborn.getpixel((88,0))==(6*8,30,40,255)
    assert name_image(image,metrics,"A-B'C").getbbox()
    with pytest.raises(ValueError,match='glyph'):name_image(image,metrics,'123')
    with pytest.raises(ValueError):name_metrics(b'\0'*112,224)
    data=bytearray(96);struct.pack_into('>5f',data,8,.625,.875,.5,.25,8)
    assert name_placement(data)==((.625,.875,.5,.25),8)
    struct.pack_into('>f',data,24,float('nan'))
    with pytest.raises(ValueError):name_placement(data)


@pytest.mark.parametrize('number',range(101))
def test_every_jersey_number_renders_including_00(number):
    image=Image.new('RGBA',(80,4),(255,0,0,255))
    rendered=number_image(image,[(i*8,5) for i in range(10)],number,(32,8))
    assert rendered.getbbox() and rendered.getpixel((0,7))[3]==0
