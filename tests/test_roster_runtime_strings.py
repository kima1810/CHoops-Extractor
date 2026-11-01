import struct

import pytest
from support import roster_fixture

from choops_py.roster.adapters import load_bytes
from choops_py.roster.editor_model import EditorModel


@pytest.mark.parametrize('text', ['Albany', 'Łukasz', '漢字', '\U0001f600', ''])
def test_expanded_text_matches_runtime_pointer_and_big_endian_units(text):
    base = roster_fixture()
    raw = bytearray(base.data)
    raw[-1] = 0xa5  # Never rely on the old heap ending in a zero byte.
    model = EditorModel(load_bytes(bytes(raw)), base.tables)
    before = bytes(model.data)
    field = model.row_offset('players', 0) + 0x14
    model.edit('players', 0, 'first_name', text)
    displacement = struct.unpack_from('>i', model.data, field)[0]
    runtime_target = field + displacement - 1
    encoded = text.encode('utf-16-be') + b'\0\0'
    assert runtime_target % 2 == 0
    assert bytes(model.data[runtime_target:runtime_target + len(encoded)]) == encoded
    end = runtime_target
    while struct.unpack_from('>H', model.data, end)[0]:
        end += 2
    assert bytes(model.data[runtime_target:end]).decode('utf-16-be') == text
    assert model.rows['players'][0]['first_name'] == text
    model.undo()
    assert bytes(model.data) == before


def test_source_big_endian_non_latin_names_decode_without_shifted_view():
    base = roster_fixture()
    raw = bytearray(base.data)
    field = base.row_offset('players', 0) + 0x14
    target = len(raw)
    raw += '漢字'.encode('utf-16-be') + b'\0\0'
    struct.pack_into('>i', raw, field, target - field + 1)
    model = EditorModel(load_bytes(bytes(raw)), base.tables)
    assert model.rows['players'][0]['first_name'] == '漢字'
    assert bytes(model.data) == bytes(raw)
