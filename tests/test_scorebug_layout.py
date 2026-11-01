import struct

import pytest

from choops_py.modding.scorebug_layout import edit_scene


def fixture():
    head=bytearray(1200);payload=bytearray(4*36+8)
    def u(at,v):struct.pack_into('>I',head,at,v)
    def ptr(at,target):u(at,target-at+1)
    u(0x44,1);ptr(0x48,128);ptr(128,1000);head[1000:1010]='quad\0'.encode('utf-16-be')
    u(128+0x84,1);ptr(128+0x88,320)
    u(320+16,4);u(320+32,36);u(320+40,1)
    u(128+0x94,3);ptr(128+0x9c,400)
    for i,code in enumerate(['2000000002030000','200c000003020800','2010000002040300']):head[408+i*64:416+i*64]=bytes.fromhex(code)
    for i,(x,y,u_,v) in enumerate([(0,0,0,1),(2,2,0,0),(6,0,1,1),(8,2,1,0)]):
        struct.pack_into('>3f2e4fI',payload,i*36,x,y,5,u_,v,.1,.2,.3,.8,0xdeadbeef)
    payload[-8:]=b'KEEPBYTE'
    # One paired authored text record and its independent marker translations.
    u(0x4c,1);ptr(0x50,640);ptr(704,1040);head[1040:1056]='message\0'.encode('utf-16-be')
    for at in (688,736,848,864):struct.pack_into('>3f',head,at,10,20,3)
    ptr(880,1040)
    return [bytes(head),bytes(payload)]


def test_rectification_preserves_interleaved_data_and_moves_all_text_copies():
    source=fixture();result,report=edit_scene(source,dict(parts={'quad':dict(bounds=[20,30,24,34],rectify_uv=True,rgb_scale=.5,z_offset=1)},text={'message':[70,80]}))
    assert list(map(len,result))==list(map(len,source))
    for i in range(4):
        x,y,z=struct.unpack_from('>3f',result[1],i*36);u,v=struct.unpack_from('>2e',result[1],i*36+12)
        assert x==20+u*4 and y==34-v*4 and z==6
        assert result[1][i*36+32:i*36+36]==source[1][i*36+32:i*36+36]
        assert struct.unpack_from('>4f',result[1],i*36+16)==pytest.approx([.05,.1,.15,.8])
    assert result[1][-8:]==source[1][-8:]
    for at in (688,736,848,864):assert struct.unpack_from('>3f',result[0],at)==(70,80,3)
    assert report[-1]['matching_marker']
    assert edit_scene(source,{})[0]==source


def test_bad_target_or_unmatched_marker_does_not_mutate_input():
    source=fixture();before=list(source)
    with pytest.raises(ValueError,match='one scene profile'):edit_scene(source,{'scorebug_bottombar':{}})
    with pytest.raises(ValueError,match='Unknown HUD part'):edit_scene(source,{'parts':{'missing':{'hide':True}}})
    with pytest.raises(ValueError,match='HUD rectangle'):edit_scene(source,{'parts':{'quad':{'bounds':[0,0,0,4]}}})
    head=bytearray(source[0]);struct.pack_into('>f',head,864,999)
    with pytest.raises(ValueError,match='matching HUD marker'):edit_scene([bytes(head),source[1]],{'text':{'message':[1,2]}})
    assert source==before


def test_hide_changes_only_alpha_and_unknown_vertex_words_stay_exact():
    source=fixture();result,_=edit_scene(source,{'parts':{'quad':{'hide':True}}})
    assert result[0]==source[0]
    for i in range(4):
        assert result[1][i*36:i*36+28]==source[1][i*36:i*36+28]
        assert struct.unpack_from('>f',result[1],i*36+28)[0]==0
        assert result[1][i*36+32:i*36+36]==source[1][i*36+32:i*36+36]


def test_disable_native_label_loop_preserves_records_bones_and_geometry():
    source=fixture();result,report=edit_scene(source,{'disable_text':True})
    assert struct.unpack_from('>I',result[0],0x4c)[0]==0
    assert result[0][:0x4c]==source[0][:0x4c] and result[0][0x50:]==source[0][0x50:]
    assert result[1]==source[1] and report==[{'disabled_text_records':1}]
    # Ordered part operations must not lose the final label-suppression action.
    repeated,_=edit_scene(source,{'parts':{'quad':[{'hide':True}]},'disable_text':True})
    assert struct.unpack_from('>I',repeated[0],0x4c)[0]==0
    with pytest.raises(ValueError,match='boolean'):edit_scene(source,{'disable_text':1})


def test_inventory_includes_sixth_man_and_named_authored_anchor():
    from support import iff_fixture
    from choops_py.formats.cdf_backed_iff_writer import name_trailer
    from choops_py.formats.scorebug import inspect_iff
    raw=iff_fixture(fixture(),[(0xe26c9b5d,[0,0])])+name_trailer([dict(name='6th_man_meter',type='SCNE')])
    rows=inspect_iff(raw)
    assert rows[0]['name']=='6th_man_meter'
    assert rows[0]['text_anchors']==[dict(name='message',position=[10.,20.,3.],matrix_copies_match=True)]


def test_single_quad_requires_confirmed_restart_topology_and_keeps_indices():
    source=fixture();head=bytearray(source[0]);first=source[1][:144]
    payload=first+first+struct.pack('>9H',0,1,2,3,65535,4,5,6,7)
    struct.pack_into('>I',head,320+16,8)
    struct.pack_into('>III',head,128+0xa4,0x20000010,9,289)
    result,_=edit_scene([bytes(head),payload],{'parts':{'quad':{'bounds':[0,0,4,4],'rectify_uv':True,'single_quad':True}}})
    assert result[1][288:]==payload[288:]
    assert all(struct.unpack_from('>f',result[1],i*36+28)[0]==0 for i in range(4,8))
    head[128+0xa4:128+0xa8]=bytes(4)
    with pytest.raises(ValueError,match='restart strips'):edit_scene([bytes(head),payload],{'parts':{'quad':{'bounds':[0,0,4,4],'rectify_uv':True,'single_quad':True}}})


def test_partial_range_preserves_other_draw_and_flattens_gradient():
    source=fixture();result,_=edit_scene(source,{'parts':{'quad':{
        'vertex_range':[0,2], 'bounds':[10,20,12,22], 'rgb':[.7,.7,.7]}}})
    assert result[1][72:]==source[1][72:]
    for i in range(2):
        assert struct.unpack_from('>4f',result[1],i*36+16)==pytest.approx([.7,.7,.7,.8])
    for selected in ([-1,2],[0,5],[1,1],[0,True]):
        with pytest.raises(ValueError,match='vertex range'):
            edit_scene(source,{'parts':{'quad':{'vertex_range':selected}}})


def test_straightening_keeps_original_atlas_coordinates():
    source=fixture();result,_=edit_scene(source,{'parts':{'quad':{
        'bounds':[20,30,24,34],'straighten':True}}})
    for i in range(4):
        assert result[1][i*36+12:i*36+16]==source[1][i*36+12:i*36+16]
    assert [struct.unpack_from('>2f',result[1],i*36) for i in range(4)]==[(20,30),(20,34),(24,30),(24,34)]


def test_native_text_basis_scale_preserves_pointers_and_translated_marker():
    source=fixture();head=bytearray(source[0])
    for at in (640,660,680):struct.pack_into('>f',head,at,1)
    struct.pack_into('>3f',head,848,10,120,8)
    original=bytes(head)
    with pytest.raises(ValueError,match='matching HUD marker'):
        edit_scene([original,source[1]],{'text':{'message':[30,40]}})
    result,_=edit_scene([original,source[1]],{'text':{'message':{
        'position':[30,40],'scale':1.25,'marker_offset':[0,100,5]}}})
    for at in (640,660,680):assert struct.unpack_from('>f',result[0],at)[0]==1.25
    assert struct.unpack_from('>3f',result[0],848)==(30,140,8)
    assert struct.unpack_from('>3f',result[0],864)==(30,40,3)
    assert result[0][704:708]==original[704:708]
    assert result[1]==source[1]


def test_ordered_operations_preserve_relocated_vertices_when_hiding_other_draw():
    source=fixture()
    result,_=edit_scene(source,{'parts':{'quad':[
        {'bounds':[20,30,24,34],'straighten':True},
        {'vertex_range':[2,4],'hide':True}]}})
    assert [struct.unpack_from('>2f',result[1],i*36) for i in range(4)]==[(20,30),(20,34),(24,30),(24,34)]
    assert struct.unpack_from('>f',result[1],28)[0]==pytest.approx(.8)
    assert struct.unpack_from('>f',result[1],100)[0]==0


def test_explicit_alpha_restores_a_previously_hidden_draw():
    source=fixture();hidden,_=edit_scene(source,{'parts':{'quad':{'hide':True}}})
    restored,_=edit_scene(hidden,{'parts':{'quad':{'alpha':1}}})
    assert all(struct.unpack_from('>f',restored[1],i*36+28)[0]==1 for i in range(4))
    with pytest.raises(ValueError,match='alpha'):edit_scene(source,{'parts':{'quad':{'alpha':2}}})
