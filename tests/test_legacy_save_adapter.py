import struct

import pytest

from choops_py.core.errors import ToolError
from choops_py.roster.adapters import (
    LEGACY_SAVE_ROSTER_OFFSET, LEGACY_SAVE_ROSTER_SIZE, LEGACY_SAVE_SIGNATURE,
    LEGACY_SAVE_TABLES, load_bytes,
)
from choops_py.roster.schema import HEADER_TABLES, TABLES


def legacy_fixture():
    raw = bytearray(LEGACY_SAVE_ROSTER_SIZE)
    for name, (count, stride) in LEGACY_SAVE_TABLES.items():
        field, bias, _, _ = HEADER_TABLES[name]
        start = TABLES[name][0] if name in TABLES else 0x300000
        assert start+count*stride <= len(raw)
        struct.pack_into('>Ii', raw, field, count, start-field-4+bias)
    prefix = LEGACY_SAVE_SIGNATURE+bytes(LEGACY_SAVE_ROSTER_OFFSET-len(LEGACY_SAVE_SIGNATURE))
    return prefix+raw+b'KEEP MODE STATE'


def test_legacy_save_fixed_size_encode_preserves_all_outer_bytes():
    source = legacy_fixture()
    model = load_bytes(source)
    assert model.kind == 'legacy-save'
    assert model.encode(model.payload) == source
    edited = bytearray(model.payload)
    edited[0x271ac+0x1a] = 42
    result = model.encode(edited)
    start = LEGACY_SAVE_ROSTER_OFFSET
    assert result[:start] == source[:start]
    assert result[start+len(edited):] == b'KEEP MODE STATE'
    assert load_bytes(result).payload == edited
    with pytest.raises(ToolError, match='legacy_save_size_change_blocked'):
        model.encode(model.payload+b'grow')


def test_legacy_save_rejects_truncation_and_unrecognized_table_profile():
    raw = legacy_fixture()
    with pytest.raises(ToolError, match='truncated_legacy_save'):
        load_bytes(raw[:1000])
    bad = bytearray(raw)
    struct.pack_into('>I', bad, LEGACY_SAVE_ROSTER_OFFSET+8, 5684)
    with pytest.raises(ToolError, match='unsupported_legacy_save_layout'):
        load_bytes(bytes(bad))
