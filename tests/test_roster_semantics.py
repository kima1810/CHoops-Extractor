import struct
import pytest
from support import roster_fixture
from choops_py.roster.adapters import load_bytes
from choops_py.roster.editor_model import EditorModel
from choops_py.roster.schema import HEADER_TABLES,RATING_NAMES
from choops_py.core.errors import ToolError


def test_named_rating_offsets_and_fractional_source_preservation():
    base=roster_fixture();raw=bytearray(base.data)
    offset=base.row_offset('players',0)+0x52
    struct.pack_into('>H',raw,offset,8446)
    model=EditorModel(load_bytes(bytes(raw)),base.tables)
    assert RATING_NAMES[11]=='Stamina'
    assert model.rows['players'][0]['attribute_ratings'][11]==84
    assert bytes(model.data)==bytes(raw)
    model.edit('players',0,'attribute_ratings',90,11)
    assert model.data[offset:offset+2]==struct.pack('>H',9000)
    assert model.data[:offset]==raw[:offset] and model.data[offset+2:]==raw[offset+2:]
    model.undo();assert bytes(model.data)==bytes(raw)
    with pytest.raises(ToolError):model.edit('players',0,'attribute_ratings',100,0)


def test_weight_and_handedness_preserve_neighboring_packed_bits():
    model=roster_fixture();off=model.row_offset('players',0)
    struct.pack_into('>I',model.data,off+0x9c,0xa5a5a5a5)
    struct.pack_into('>I',model.data,off+0x94,0x55aaaa55)
    model.reload();original=bytes(model.data)
    model.edit('players',0,'weight_lbs',235)
    assert model.rows['players'][0]['weight_lbs']==235
    before=int.from_bytes(original[off+0x9c:off+0xa0],'big')
    after=int.from_bytes(model.data[off+0x9c:off+0xa0],'big')
    assert (before^after)&~(0x1ff<<11)==0
    model.edit('players',0,'hand_code',1)
    assert model.rows['players'][0]['hand_code']==1
    assert (int.from_bytes(model.data[off+0x94:off+0x98],'big')^int.from_bytes(original[off+0x94:off+0x98],'big'))&~(1<<25)==0


def test_tendency_and_potential_single_byte_writes():
    model=roster_fixture();before=bytes(model.data);off=model.row_offset('players',0)
    model.edit('players',0,'shot_tendencies',80,2)
    assert [i for i,(a,b) in enumerate(zip(before,model.data)) if a!=b]==[off+0x7a]
    model.edit('players',0,'potential',95)
    assert model.rows['players'][0]['potential']==95
    assert model.data[off+0x7f]==95


def header_roster():
    data=bytearray(0x6000)
    starts={'players':0x200,'arenas':0x600,'teams':0x800,'coaches':0x1000,'conferences':0x1100,'uniforms':0x5000}
    for name,(field,bias,stride,_) in HEADER_TABLES.items():
        struct.pack_into('>I',data,field,2)
        struct.pack_into('>i',data,field+4,starts[name]+bias-(field+4))
    # Reciprocal team/conference pointers use the game's interior target biases.
    field=starts['teams']+0x48
    struct.pack_into('>i',data,field,starts['conferences']+1-field)
    field=starts['conferences']+0x6e0
    struct.pack_into('>i',data,field,starts['teams']+0x31-field)
    struct.pack_into('>H',data,starts['conferences']+0x870,1)
    return data,starts


def test_header_derived_tables_and_reciprocal_conference_membership():
    data,starts=header_roster();model=EditorModel(load_bytes(bytes(data)))
    assert model.tables['coaches'][0]==starts['coaches']
    assert model.rows['teams'][0]['conference_index']==0
    assert model.rows['conferences'][0]['team_indices']==[0]
    assert model.validate()['valid']
    with pytest.raises(ToolError):model.edit('teams',0,'conference_index',1)
    broken=bytearray(data);struct.pack_into('>I',broken,8,0xffffffff)
    with pytest.raises(ValueError):EditorModel(load_bytes(bytes(broken)))


@pytest.mark.parametrize('school,conference', [(-1, 0), (2, 0), (True, 0), (0, -1), (0, 2), (0, True)])
def test_conference_assignment_rejects_invalid_indices_atomically(school, conference):
    data, _ = header_roster()
    model = EditorModel(load_bytes(bytes(data)))
    before = bytes(model.data)
    with pytest.raises(ToolError):
        model.move_team_to_conference(school, conference)
    assert bytes(model.data) == before and not model.history and not model.edits


def test_edit_schools_color_callback_indices_remain_distinct_from_palette_slots():
    from choops_py.roster.research import palette_rows
    rows=palette_rows(roster_fixture(),0)
    assert rows[14]['school_control']==11
    assert rows[15]['school_control']==12
    assert rows[0]['school_control'] is None
    assert rows[11]['school_control'] is None
    assert 'verified' in rows[14]['confidence']


@pytest.mark.gui
def test_edit_schools_view_uses_team_records(qtbot):
    from choops_py.studio.app import Window,selected
    window=Window();qtbot.addWidget(window)
    model=roster_fixture();window.display_roster(model)
    window.roster_tabs.setCurrentWidget(window.roster_views['schools'])
    window.roster_views['schools'].selectRow(1)
    assert selected(window.roster_tabs.currentWidget())[0]['asset_id']==1
    assert window.roster_tabs.tabText(window.roster_tabs.currentIndex())=='Schools'


def test_jersey_number_preserves_adjacent_flag_byte_and_roundtrips():
    model = roster_fixture()
    offset = model.row_offset('players', 0)+0x1a
    model.data[offset:offset+2] = bytes((0x80, 19))
    model.reload()
    before = bytes(model.data)
    assert model.rows['players'][0]['jersey_number'] == 19
    model.edit('players', 0, 'jersey_number', 42)
    assert model.data[offset:offset+2] == bytes((0x80, 42))
    assert model.data[:offset+1] == before[:offset+1]
    assert model.data[offset+2:] == before[offset+2:]
    model.undo()
    assert bytes(model.data) == before
    model.redo()
    assert model.data[offset] == 0x80


def test_uniform_shape_and_asset_edits_preserve_packed_neighbors():
    from choops_py.roster.editor_model import EditorModel
    from choops_py.roster.adapters import load_bytes
    import struct
    data=bytearray(32)
    first=(4<<22)|(12<<12)|(2<<8)|0x80
    struct.pack_into('>II',data,8,first,0x48001234)
    struct.pack_into('>II',data,16,(4<<22)|(13<<12),0x18005678)
    model=EditorModel(load_bytes(bytes(data)),{'uniforms':(8,2,8)})
    assert model.rows['uniforms'][0]['team_asset_id']==4
    assert model.rows['uniforms'][0]['jersey_shape_code']==1
    model.edit('uniforms',0,'jersey_shape_code',4)
    assert int.from_bytes(model.data[12:16],'big')&~(7<<27)==0x48001234&~(7<<27)
    model.edit('uniforms',0,'uniform_asset_id',13)
    assert int.from_bytes(model.data[8:12],'big')&~(1023<<12)==first&~(1023<<12)
    assert model.rows['uniforms'][0]['jersey_shape_code']==4


def test_labeled_scalar_choices_preserve_neighbor_bits():
    from choops_py.roster.schema import ENUM_CHOICES
    model=roster_fixture();off=model.row_offset('players',0)
    model.data[off+0x90:off+0x94]=bytes.fromhex('AABBCCDD');model.reload()
    before=int.from_bytes(model.data[off+0x90:off+0x94],'big')
    model.edit('players',0,'headband_code',1)
    after=int.from_bytes(model.data[off+0x90:off+0x94],'big')
    assert after&~(7<<4)==before&~(7<<4)
    assert ENUM_CHOICES['hand_code']=={0:'L',1:'R'}
    assert ENUM_CHOICES['headband_code']=={0:'No',1:'Yes'}


def test_d1_conversion_updates_type_and_reciprocal_membership_with_undo():
    data,starts=header_roster()
    field=starts['teams']+0x2ec;struct.pack_into('>I',data,field,0xA5A5A5A5)
    model=EditorModel(load_bytes(bytes(data)));before=bytes(model.data)
    model.move_team_to_conference(0,1,make_d1=True)
    assert model.rows['teams'][0]['conference_index']==1
    assert model.rows['teams'][0]['team_type_code']==0
    assert model.rows['conferences'][0]['team_indices']==[]
    assert model.rows['conferences'][1]['team_indices']==[0]
    assert int.from_bytes(model.data[field:field+4],'big')&~(7<<15)==0xA5A5A5A5&~(7<<15)
    model.undo();assert bytes(model.data)==before


def test_alternate_model_undo_redo_and_replay():
    data,starts=header_roster()
    struct.pack_into('>II',data,starts['uniforms'],(12<<12)|(2<<8)|95,0x18005678)
    struct.pack_into('>II',data,starts['uniforms']+8,(13<<12)|(1<<8),0x48001234)
    model=EditorModel(load_bytes(bytes(data)))
    model.set_alternate_enabled(0,2,False)
    assert len(model.rows['uniforms'])==1
    patch={'source_sha256':model.document()['source_sha256'],'edits':list(model.edits)}
    saved=model.source.encode(bytes(model.data))
    reopened=EditorModel(load_bytes(saved));reopened.set_alternate_enabled(0,2,True)
    row=next(r for r in reopened.rows['uniforms'] if r['variant_code']==2)
    assert row['uniform_asset_id']==12 and row['unlock_id']==95 and row['jersey_shape_code']==3
    model.undo();assert bytes(model.data)==bytes(data)
    model.redo();assert len(model.rows['uniforms'])==1
    replay=EditorModel(load_bytes(bytes(data)));replay.apply_document(patch)
    assert bytes(replay.data)==bytes(model.data)


def test_independent_arena_rebases_strings_and_only_selected_team_link():
    from choops_py.modding.declone import append_independent_arena
    data,starts=header_roster()
    field=starts['teams']+0x44
    struct.pack_into('>i',data,field,starts['arenas']+25-field)
    field=starts['teams']+704+0x44
    struct.pack_into('>i',data,field,starts['arenas']+25-field)
    for relative,text in ((24,'Old Arena'),(28,'Town'),(32,'123')):
        field=starts['arenas']+relative;target=len(data)+1
        data+=b'\0'+text.encode('utf-16-le')+b'\0\0'
        struct.pack_into('>i',data,field,target-field)
    model=EditorModel(load_bytes(bytes(data)))
    result=append_independent_arena(model,bytearray(data),0,0,'1001')
    check=EditorModel(load_bytes(bytes(result)))
    assert check.validate()['valid']
    assert check.rows['teams'][0]['arena_index']==2 and check.rows['teams'][1]['arena_index']==0
    assert check.rows['arenas'][0]['arena_code']=='123'
    assert check.rows['arenas'][2]['arena_code']=='1001'
    assert check.rows['arenas'][2]['arena_name']=='Old Arena'
    assert check.rows['arenas'][2]['arena_city']=='Town'
