import struct
import pytest
from PIL import Image
from choops_py.formats.binary import Binary
from choops_py.roster.shoes import player_fields,team_fields,texture_name
from choops_py.texture_tools.gtf import remap_preview
from choops_py.archive.hash_names import hash_name,namespace
from support import roster_fixture


def test_team_default_and_player_shoe_packing_use_distinct_offsets():
    team=bytearray(752);player=bytearray(308)
    struct.pack_into('>I',team,0x2e0,(2<<22)|(4<<17)|(12<<12)|0xabc)
    struct.pack_into('>I',team,0x2e8,1<<20)
    struct.pack_into('>I',player,0xa0,(2<<27)|(4<<22)|(12<<17)|0xabcd)
    struct.pack_into('>I',player,0xa8,1<<29)
    assert team_fields(Binary(team),0)==player_fields(Binary(player),0)
    assert player_fields(Binary(player),0)['home_shoe_texture']=='shoe_102_04.iff'
    assert player_fields(Binary(player),0)['away_shoe_texture']=='shoe_102_12.iff'
    assert texture_name(0,0,1)=='shoe_1.iff'
    assert texture_name(2,1,0) is None and texture_name(4,0,2) is None


def test_shoe_namespace_has_verified_families_and_body_variants():
    names=set(namespace())
    assert len([n for n in names if n.startswith('shoe_')])==90
    assert 'shoe_102_15.iff' in names and 'cloth_wishbone_thin.iff' in names


def test_ps3_green_luminance_remap_and_identity():
    image=Image.new('RGBA',(1,1),(10,80,150,30))
    assert remap_preview(image,0xaae4).getpixel((0,0))==(10,80,150,30)
    assert remap_preview(image,0xa9a8).getpixel((0,0))==(80,80,80,255)
    assert remap_preview(image,0).getpixel((0,0))==(0,0,0,0)
    assert remap_preview(image,0x5555).getpixel((0,0))==(255,255,255,255)
    with pytest.raises(ValueError):remap_preview(image,0x3ff)


@pytest.mark.parametrize('table',['players','teams'])
def test_shoe_writes_preserve_other_packed_bits_and_undo(table):
    from choops_py.roster.shoes import FIELDS
    model=roster_fixture();off=model.row_offset(table,0);before=bytes(model.data)
    model.edit_shoes(table,0,1,2,4,12)
    row=model.rows[table][0]
    assert row['home_shoe_texture']=='shoe_102_04.iff' and row['away_shoe_texture']=='shoe_102_12.iff'
    masks={}
    for relative,shift,bits in FIELDS[table].values():masks[relative]=masks.get(relative,0)|(((1<<bits)-1)<<shift)
    for position in range(len(before)):
        if not any(off+relative<=position<off+relative+4 for relative in masks):assert model.data[position]==before[position]
    for relative,mask in masks.items():
        assert Binary(model.data).u32(off+relative)&~mask==Binary(before).u32(off+relative)&~mask
    changed=bytes(model.data);model.undo();assert bytes(model.data)==before
    model.redo();assert bytes(model.data)==changed
    encoded=model.source.encode(changed)
    from choops_py.roster.adapters import load_bytes
    assert load_bytes(encoded).payload==changed


def test_invalid_shoe_assignment_is_atomic_and_scalar_fields_are_writable():
    model=roster_fixture();before=bytes(model.data)
    with pytest.raises(ValueError):model.edit_shoes('players',0,2,2,0,0)
    assert bytes(model.data)==before and not model.history
    model.edit('players',0,'shoe_brand_code',1)
    model.edit('players',0,'shoe_style_code',2)
    assert model.rows['players'][0]['home_shoe_texture']=='shoe_102_00.iff'


def test_shoe_dialog_refreshes_choices_and_applies_one_undoable_edit(qtbot,monkeypatch):
    from PySide6.QtWidgets import QDialog,QComboBox
    from choops_py.studio.app import Window
    window=Window();qtbot.addWidget(window)
    model=roster_fixture();model.edit_shoes('players',0,1,2,4,12)
    window.display_roster(model);window.roster_tabs.setCurrentWidget(window.roster_views['players'])
    window.roster_views['players'].selectRow(0)
    window.edit_roster_shoes()
    panel=window.player_details.shoes
    brand=panel.widgets['shoe_brand_code'];brand.setCurrentIndex(brand.findData(0))
    assert panel.widgets['shoe_style_code'].count()==1
    assert panel.widgets['home_shoe_color_code'].count()==2
    away=panel.widgets['away_shoe_color_code'];away.setCurrentIndex(away.findData(1))
    panel.apply()
    qtbot.waitUntil(lambda:window.active is None,timeout=10000)
    assert model.rows['players'][0]['away_shoe_texture']=='shoe_1.iff'
    model.undo();assert model.rows['players'][0]['away_shoe_texture']=='shoe_102_12.iff'
