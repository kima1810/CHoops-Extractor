"""Research output must distinguish established masks from unresolved bytes."""
import struct

import pytest

from support import iff_fixture
from test_roster_semantics import header_roster
from choops_py.formats.cdf_backed_iff_writer import name_trailer
from choops_py.formats.scorebug import inspect_iff
from choops_py.roster.adapters import load_bytes
from choops_py.roster.editor_model import EditorModel
from choops_py.roster.research import analyze,unresolved_ranges
from choops_py.roster.schema import HEADER_TABLES


def test_roster_anchors_and_uniform_unknown_bits():
    data,_=header_roster();model=EditorModel(load_bytes(bytes(data)))
    report=analyze(model)
    for name,(field,bias,*_) in HEADER_TABLES.items():
        if name not in model.tables:continue
        anchor=next(row for row in report['header_anchors'] if row['field']==field)
        assert anchor['relative_anchor']==model.tables[name][0]+bias-1
        assert anchor['meaning']==name+' table anchor'
    uniform=report['tables']['uniforms']
    assert uniform['classified_bits_per_row']==33
    assert sum((r['end']-r['start'])*r['unresolved_bit_mask'].bit_count() for r in uniform['unresolved_ranges'])==31
    assert report['complete_semantic_reverse_engineering'] is False
    assert report['tables']['teams']['fields_crossing_declared_stride']
    arena=report['tables']['arenas']['logical_record_window']
    assert arena['raw_origin_offset']==24 and arena['classified_bits_per_row']==146
    assert report['tables']['teams']['logical_record_window']['classified_bits_per_row']>report['tables']['teams']['classified_bits_per_row']


def test_partial_unknown_runs_keep_exact_masks():
    assert unresolved_ranges([0,255,255,3,3,0,1])==[
        dict(start=1,end=3,unresolved_bit_mask=255),dict(start=3,end=5,unresolved_bit_mask=3),
        dict(start=6,end=7,unresolved_bit_mask=1)]


def test_scorebug_inventory_skips_unrelated_records_and_bounds_geometry():
    header=bytearray(0x54)
    def scene(name):
        return iff_fixture([bytes(header),b'payload'],[(0xe26c9b5d,[0,0])])+name_trailer([dict(name=name,type='SCNE')])
    assert inspect_iff(scene('unrelated'))==[]
    row=inspect_iff(scene('scorebug_bottombar'))[0]
    assert row['parts']==[] and row['textures']==[] and row['type']=='SCNE'
    struct.pack_into('>I',header,0x44,4097)
    with pytest.raises(ValueError,match='model count'):inspect_iff(scene('scorebug_bottombar'))
