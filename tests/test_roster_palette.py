import struct
import pytest
from support import roster_fixture
from choops_py.roster.adapters import load_bytes
from choops_py.roster.editor_model import EditorModel
from choops_py.roster.research import palette_rows, analyze
from choops_py.core.errors import ToolError


def test_palette_edit_preserves_every_other_byte_and_roundtrips():
    model=roster_fixture();before=bytes(model.data)
    model.edit('teams',0,'palette_colors','#AD3640FF',14)
    position=model.row_offset('teams',0)+0x1a0+14*4
    assert model.data[position:position+4] == bytes.fromhex('AD3640FF')
    assert model.data[:position] == before[:position]
    assert model.data[position+4:] == before[position+4:]
    reopened=EditorModel(load_bytes(model.source.encode(bytes(model.data))),model.tables)
    assert reopened.rows['teams'][0]['palette_colors'][14] == '#AD3640FF'
    model.undo();assert bytes(model.data)==before
    model.redo();assert model.rows['teams'][0]['palette_colors'][14]=='#AD3640FF'
    assert 'verified' in palette_rows(model,0)[14]['confidence']


def test_palette_validation_and_json_transaction():
    model=roster_fixture();before=bytes(model.data)
    with pytest.raises(ToolError):model.edit('teams',0,'palette_colors','#ABC',0)
    with pytest.raises(ToolError):model.edit('teams',0,'palette_colors','#FFFFFFFF',31)
    assert bytes(model.data)==before
    document=model.document();document['tables']['teams'][0]['palette_colors'][1]='#01020304'
    model.apply_document(document)
    assert model.rows['teams'][0]['palette_colors'][1]=='#01020304'


def test_fixed_length_school_string_edit_is_isolated():
    base=roster_fixture();raw=bytearray(base.data)
    pointer=base.row_offset('teams',0)+0x38
    target=0xd00
    struct.pack_into('>i',raw,pointer,target-pointer)
    raw[target:target+10]='Test'.encode('utf-16-le')+b'\0\0'
    model=EditorModel(load_bytes(bytes(raw)),base.tables)
    model.edit('teams',0,'school_name','Demo')
    assert model.rows['teams'][0]['school_name']=='Demo'
    assert model.data[:target]==raw[:target]
    assert model.data[target+8:]==raw[target+8:]
    with pytest.raises(ToolError):model.edit('teams',0,'school_name','Longer')


def test_research_report_covers_every_row_byte_without_claiming_completion():
    report=analyze(roster_fixture())
    assert report['complete_semantic_reverse_engineering'] is False
    for table in report['tables'].values():
        assert len(table['fields']) == table['stride']
        assert table['classified_bytes_per_row']+table['unknown_bytes_per_row']==table['stride']
