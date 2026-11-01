"""Research reads preserve input and never reinterpret NBA/player IDs as face IDs."""
import struct
from types import SimpleNamespace

import pytest

from choops_py.research.player_faces import player_faces, inventory, MORPH_RANGES


def model(slots):
    # Includes the logical final row tail after the biased editor window.
    data = bytearray(len(slots)*308+16)
    for index, slot in enumerate(slots):
        offset = index*308
        struct.pack_into('>I', data, offset+0x9c, 0xabcde000 | slot)
        struct.pack_into('>I', data, offset+0x1c, 0x76543210+index)
    return SimpleNamespace(data=data, tables={'players': (0, len(slots), 308)},
        rows={'players': [dict(display_name='Synthetic '+str(i)) for i in range(len(slots))]})


def test_face_slots_are_independent_of_ids_and_unknown_bits():
    source = model([0, 1, 3, 7, 15])
    before = bytes(source.data)
    report = player_faces(source, True)
    assert report['dedicated_slot_counts'] == {0: 1, 1: 1, 3: 1, 7: 1, 15: 1}
    assert report['players'][1]['original_likeness'] == 'Mike Conley'
    assert report['players'][2]['original_likeness'] == 'Greg Oden'
    assert report['players'][4]['slot_established'] is False
    assert report['players'][0]['generation_seed'] == 0x76543210
    assert source.data == before and report['writable'] is False


def test_custom_morph_flag_and_biased_final_array_are_read_separately():
    source = model([4])
    struct.pack_into('>I', source.data, 0x98, 0x12345679)
    for start, count in MORPH_RANGES:
        source.data[start+count-1] = 1
    report = player_faces(source)
    assert report['custom_morph_flag_count'] == 1
    assert report['nonzero_morph_row_counts'] == [1, 1, 1]
    assert 'players' not in report
    source.data = source.data[:308]
    with pytest.raises(ValueError):
        player_faces(source)


def test_other_roster_families_and_strides_are_not_guessed():
    source = model([0])
    source.game = 'nba2k9'
    with pytest.raises(ValueError, match='not NBA'):
        player_faces(source)
    del source.game
    source.tables['players'] = (0, 1, 312)
    with pytest.raises(ValueError, match='stride'):
        player_faces(source)


def test_missing_banks_are_reported_without_writes_or_asset_guessing():
    archive = SimpleNamespace(entries=[])
    result = inventory(archive)
    assert result['mode'] == 'read-only'
    assert result['banks'] == {} and len(result['unresolved']) == 6
