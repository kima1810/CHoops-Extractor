import struct

import pytest

from choops_py.modding.cloth_constraints import retarget_distances

pytestmark = pytest.mark.unit


def fixture():
    raw = bytearray(416)
    struct.pack_into(">H", raw, 0, 48)
    struct.pack_into(">HH", raw, 4, 8, 8)
    struct.pack_into(">I", raw, 0xC0, 256)
    struct.pack_into(">I", raw, 0xC8, 304)
    struct.pack_into(">II", raw, 0xD4, 320, 368)
    for i in range(3):
        struct.pack_into(">4f", raw, 256 + i * 16, float(i), 0, 0, 1)
    for table, length in ((320, 32), (368, 26)):
        for i in range(8):
            struct.pack_into(">I", raw, table + i * 4, (length << 10) | 1)
        raw[table + 32:table + 48] = bytes(range(16))
    return bytes(raw)


def test_stretch_and_prestrained_bend_both_follow_shape():
    before = fixture()
    edited = bytearray(before)
    struct.pack_into(">f", edited, 272, 0.5)
    after, count = retarget_distances(before, edited)
    assert count == 16
    for table, wanted in ((320, 16), (368, 13)):
        for i in range(8):
            word = struct.unpack_from(">I", after, table + i * 4)[0]
            assert word == (wanted << 10) | 1
        assert after[table + 32:table + 48] == before[table + 32:table + 48]
    assert after[:320] == edited[:320]
    assert retarget_distances(before, before) == (before, 0)


def test_self_edge_padding_preserved():
    raw = bytearray(fixture())
    struct.pack_into(">I", raw, 320, (32 << 10))
    assert retarget_distances(raw, raw) == (raw, 0)


@pytest.mark.parametrize("failure", ["outside", "overlap", "truncated", "overflow"])
def test_unsafe_constraint_edits_rejected(failure):
    raw = bytearray(fixture())
    if failure == "outside":
        struct.pack_into(">I", raw, 320, (32 << 10) | 3)
    if failure == "overlap":
        struct.pack_into(">I", raw, 0xD8, 320)
    if failure == "truncated":
        raw = raw[:-1]
    edited = bytearray(raw)
    if failure == "overflow":
        struct.pack_into(">f", edited, 272, 100)
    with pytest.raises(ValueError):
        retarget_distances(raw, edited)
