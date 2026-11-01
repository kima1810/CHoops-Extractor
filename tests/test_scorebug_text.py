import struct

import pytest

from choops_py.formats.binary import Binary
from choops_py.modding.scorebug_text import edit_styles,inspect_styles


def fixture():
    h=bytearray(2048)
    def u(at,value):struct.pack_into('>I',h,at,value)
    def ptr(at,target):u(at,target-at+1)
    u(0x4c,1);ptr(0x50,128);ptr(192,1000);ptr(208,1200)
    h[1000:1016]='message\0'.encode('utf-16-be')
    h[1600:1616]='message\0'.encode('utf-16-be')
    alias='Stratum2 22 32\0'.encode('utf-16-be');h[1500:1500+len(alias)]=alias
    u(1200,6)
    for i,(kind,key) in enumerate([(3,0xbf045bdb),(3,0xae7e1958),(0,0x6109ea5a),(0,0x72b6694d),(2,0x92f9b3f9),(1,0xad44372a)]):
        at=1216+i*32;u(at+16,kind);u(at+20,key)
    ptr(1216,1500);ptr(1248,1600);u(1280,222);u(1312,0x10090)
    struct.pack_into('>4f',h,1344,31793,59031,7,9)
    return [bytes(h),b'untouched payload']


def test_native_property_values_precede_type_and_key_and_binding_keeps_bone():
    source=fixture()
    assert inspect_styles(source[0])[0]['font']=='Stratum2 22 32'
    assert inspect_styles(source[0])[0]['color']==[222,None,None]
    result,_=edit_styles(source,{'message':{'font':'Stratum2 25','binding':'home_city'}})
    b=Binary(result[0]);row=inspect_styles(result[0])[0]
    assert row['binding']=='home_city' and row['font']=='Stratum2 25'
    assert b.utf16(b.relative(1248),'be')=='message'
    changed=set(range(192,196))|set(range(1216,1220))
    assert all(x==y for i,(x,y) in enumerate(zip(source[0],result[0])) if i not in changed)
    assert result[1]==source[1]
    assert len(result[0])%4==0


def test_style_guards_and_noop_preserve_input():
    source=fixture();assert edit_styles(source,{})[0]==source
    for change in [{'font':''},{'font':'bad\nname'},{'bogus':3}]:
        with pytest.raises(ValueError):edit_styles(source,{'message':change})
    with pytest.raises(ValueError,match='Unknown'):edit_styles(source,{'absent':{'font':'Stratum2 25'}})
    h=bytearray(source[0]);struct.pack_into('>I',h,1232,1)
    with pytest.raises(ValueError,match='font property'):edit_styles([bytes(h),source[1]],{'message':{'font':'Stratum2 25'}})
    assert source==fixture()


def test_shared_font_property_and_duplicate_binding_are_not_silently_changed():
    source=fixture();h=bytearray(source[0]);h[272:416]=h[128:272]
    struct.pack_into('>I',h,0x4c,2)
    h[1700:1714]='second\0'.encode('utf-16-be')
    struct.pack_into('>I',h,336,1700-336+1)
    struct.pack_into('>I',h,352,1200-352+1)
    with pytest.raises(ValueError,match='shared'):
        edit_styles([bytes(h),source[1]],{'message':{'font':'Stratum2 25'}})
    with pytest.raises(ValueError,match='already exists'):
        edit_styles([bytes(h),source[1]],{'message':{'binding':'second'}})


def test_native_literal_id_vector_and_center_flags_follow_loader_pack_order():
    source=fixture();assert inspect_styles(source[0])[0]['literal_id']==0xe6977c31
    result,_=edit_styles(source,{'message':{'literal_id':0xc8b40001,'align':'center'}})
    assert inspect_styles(result[0])[0]['literal_id']==0xc8b40001
    assert struct.unpack_from('>4f',result[0],1344)==(1,51380,7,9)
    assert struct.unpack_from('>I',result[0],1312)[0]==0x30090
    assert result[1]==source[1]
    for key in [0,2,0xffffffff]:
        with pytest.raises(ValueError,match='literal'):edit_styles(source,{'message':{'literal_id':key}})


def test_popup_alpha_restoration_preserves_events_bones_and_property_tails():
    source=fixture();assert inspect_styles(source[0])[0]['alpha']==0
    result,_=edit_styles(source,{'message':{'alpha':1}})
    assert inspect_styles(result[0])[0]['alpha']==1
    assert all(a==b for i,(a,b) in enumerate(zip(source[0],result[0])) if i not in range(1376,1380))
    assert result[1]==source[1]
    for alpha in [-1,2,float('nan'),'1']:
        with pytest.raises(ValueError,match='alpha'):edit_styles(source,{'message':{'alpha':alpha}})
    with pytest.raises(ValueError,match='Missing typed'):edit_styles(source,{'message':{'color':[222,222,222]}})
    with pytest.raises(ValueError,match='color'):edit_styles(source,{'message':{'color':[222,222,256]}})


def test_native_alignment_rejects_parseable_but_misaligned_properties():
    source=fixture();h=bytearray(source[0]);style=bytes(h[1200:1408])
    h[1204:1412]=style
    struct.pack_into('>I',h,208,1204-208+1)
    struct.pack_into('>I',h,1220,1500-1220+1)
    struct.pack_into('>I',h,1252,1600-1252+1)
    # Byte-wise parsing still finds the intended literal, but native lvx rounds
    # the address down and consumes different bytes. Reject before editing it.
    assert struct.unpack_from('>2f',h,1348)==(31793,59031)
    assert h[1344:1360]!=h[1348:1364]
    with pytest.raises(ValueError,match='16-byte aligned'):
        inspect_styles(bytes(h))


def test_native_width_fit_preserves_literal_and_alignment_flags():
    source=fixture();h=bytearray(source[0]);struct.pack_into('>I',h,1200,7)
    struct.pack_into('>II',h,1424,0,0x11fa397c)
    source=[bytes(h),source[1]]
    result,_=edit_styles(source,{'message':{'max_width':96,'align':'center','literal_id':0xc8b40001}})
    assert struct.unpack_from('>I',result[0],1408)[0]==96
    assert struct.unpack_from('>I',result[0],1312)[0]==0x30190
    assert inspect_styles(result[0])[0]['literal_id']==0xc8b40001
    assert result[1]==source[1]
    for width in [0,-1,4097,1.5,float('nan')]:
        with pytest.raises(ValueError,match='width'):
            edit_styles(source,{'message':{'max_width':width}})
