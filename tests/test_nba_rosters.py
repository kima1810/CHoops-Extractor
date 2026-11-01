import copy
import struct

import pytest

from choops_py.roster.adapters import load_bytes
from choops_py.roster.editor_model import EditorModel
from choops_py.roster.nba import NBARosterModel, PROFILES


def nba_payload(game):
    profile=PROFILES[game];raw=bytearray(0x3000)
    struct.pack_into('>II',raw,0,1,profile['marker'])
    if game=='nba2k14':struct.pack_into('>I',raw,0x14,0xf34551e7)
    for table,start,count,bias in [('players',0x600,2,17),('arenas',0xc00,1,1),('teams',0x1000,1,49)]:
        key=table[:-1];field=profile[key+'_header']
        struct.pack_into('>Ii',raw,field,count,start+bias-field-4)
    field=profile['template_header']+4
    struct.pack_into('>i',raw,field,0x600+16+2*profile['player_stride']-field+1)
    cursor=0x2000
    def text(field,value):
        nonlocal cursor
        data=value.encode('utf-16-be')+bytes(2)
        raw[cursor:cursor+len(data)]=data;struct.pack_into('>i',raw,field,cursor-field+1);cursor+=len(data)
    for i in range(2):
        off=0x600+i*profile['player_stride']
        text(off+16,'Surname'+str(i));text(off+20,'Given'+str(i))
        struct.pack_into('>f',raw,off+profile['height'],198.12)
        struct.pack_into('>f',raw,off+profile['weight'],210.)
        rel,shift=profile['number'];struct.pack_into('>I',raw,off+rel,7<<shift)
        rel,shift=profile['face'];word=struct.unpack_from('>I',raw,off+rel)[0];struct.pack_into('>I',raw,off+rel,word|(123<<shift))
    for field,rel in profile['team_strings'].items():text(0x1000+rel,field)
    for field,rel in profile['arena_strings'].items():text(0xc00+rel,field)
    struct.pack_into('>i',raw,0x1030,0x610-0x1030+1)
    return bytes(raw)


@pytest.mark.parametrize('game',PROFILES)
def test_nba_schema_edits_preserve_unrelated_bytes_and_wrapper(game,tmp_path):
    payload=nba_payload(game);source=load_bytes(struct.pack('>I',len(payload))+payload)
    model=NBARosterModel(source)
    assert model.game==game and model.rows['teams'][0]['roster_slots'][0]==0
    model.edit('players',0,'jersey_number',99)
    rel,shift=model.profile['number'];off=model.row_offset('players',0)+rel
    before=struct.unpack_from('>I',payload,off)[0];after=struct.unpack_from('>I',model.data,off)[0]
    assert (before^after)&~(127<<shift)==0
    assert model.data[:off]==payload[:off] and model.data[off+4:]==payload[off+4:]
    model.undo();assert bytes(model.data)==payload
    model.redo();assert model.rows['players'][0]['jersey_number']==99
    model.edit('players',0,'height_inches',80)
    model.edit('players',0,'weight_pounds',225)
    model.edit('players',0,'position_code',3)
    model.edit('players',0,'first_name','New')
    if game=='nba2k14':model.edit('players',0,'secondary_position_code',4)
    decoded=load_bytes(source.encode(bytes(model.data)))
    reopened=NBARosterModel(decoded)
    assert reopened.validate()['valid']
    assert reopened.rows['players'][0]['height_inches']==80
    assert reopened.rows['players'][0]['first_name']=='New'
    assert reopened.rows['players'][0]['position_code']==3
    path=tmp_path/'roster.rost';path.write_bytes(decoded.payload)
    assert EditorModel.open(path).game==game


@pytest.mark.parametrize('game',PROFILES)
def test_nba_rejects_unknown_fields_growth_and_invalid_numbers_atomically(game):
    model=NBARosterModel(load_bytes(nba_payload(game)));before=bytes(model.data)
    for field,value in [('attribute_ratings',[99]*30),('first_name','X'*100),('jersey_number',101),('height_inches',float('nan')),('position_code',6)]:
        with pytest.raises(ValueError):model.edit('players',0,field,value)
        assert bytes(model.data)==before and not model.history
    patch={**model.document(),'edits':[dict(table='players',index=0,field='jersey_number',value=8),dict(table='players',index=0,field='unknown',value=0)]}
    with pytest.raises(ValueError):model.apply_document(patch)
    assert bytes(model.data)==before and not model.history
    patch=copy.deepcopy(model.document());patch['tables']['players'][0]['jersey_number']=9
    model.apply_document(patch);assert model.rows['players'][0]['jersey_number']==9


@pytest.mark.parametrize('game',PROFILES)
def test_nba_shared_names_and_malformed_directory_rejected(game):
    raw=bytearray(nba_payload(game));profile=PROFILES[game]
    first=0x614;second=first+profile['player_stride']
    target=first+struct.unpack_from('>i',raw,first)[0]-1
    struct.pack_into('>i',raw,second,target-second+1)
    model=NBARosterModel(load_bytes(bytes(raw)))
    with pytest.raises(ValueError,match='shared'):model.edit('players',0,'first_name','A')
    struct.pack_into('>I',raw,profile['player_header'],20001)
    with pytest.raises(ValueError):NBARosterModel(load_bytes(bytes(raw)))


@pytest.mark.gui
@pytest.mark.parametrize('game',PROFILES)
def test_gui_detected_nba_panel_does_not_use_college_fields(qtbot,game):
    from choops_py.studio.app import Window
    window=Window();qtbot.addWidget(window)
    model=NBARosterModel(load_bytes(nba_payload(game)));window.display_roster(model)
    assert window.nba_roster is model and window.roster is None
    assert window.ch_roster_panel.isHidden()
    assert window.nba_panel.records.rowCount()==2
    window.nba_panel.teams.setCurrentIndex(1)
    assert window.nba_panel.records.rowCount()==1
    model.edit('players',0,'jersey_number',99);window.undo_roster()
    assert model.rows['players'][0]['jersey_number']==7
