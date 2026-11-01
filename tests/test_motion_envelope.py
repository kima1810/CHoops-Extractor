import struct

import pytest
from support import iff_fixture

from choops_py.archive.catalog import category
from choops_py.archive.hash_names import hash_name, lookup
from choops_py.formats.motion_envelope import inspect_collection, inspect_envelope
from choops_py.research.animation_compat import header_records


def test_inventory_keeps_large_native_banks_and_validates_pointer_table():
    raw = iff_fixture([b"payload"], [(0x60900D71, [0]) for _ in range(10001)])
    size = struct.unpack_from(">I", raw, 4)[0]
    assert len(header_records(raw[:size], len(raw))) == 10001
    bad = bytearray(raw[:size])
    struct.pack_into(">I", bad, 24, len(raw))
    with pytest.raises(ValueError, match="pointer table"):
        header_records(bytes(bad), len(raw))


def test_old_and_new_reference_keys_are_not_followed_as_pointers():
    ch = bytearray(64)
    nba = bytearray(56)
    struct.pack_into(">I", ch, 0x30, 0xFABC1234)
    struct.pack_into(">I", nba, 0x28, 0xFABC1234)
    for profile, raw in [("college-hoops-2k8", ch), ("nba-2k11", nba)]:
        result = inspect_envelope(bytes(raw), profile)
        assert result["kind"] == "unresolved-reference"
        assert result["source_reference_id"] == 0xFABC1234
        assert result["import_supported"] is False
    with pytest.raises(ValueError, match="not established"):
        inspect_envelope(bytes(nba), "nba-2k14")


def test_native_event_pointer_fixups_are_bounded_and_sentinel_checked():
    nba = bytearray(128)
    struct.pack_into(">I", nba, 0x30, 80 - 0x30 + 1)
    struct.pack_into(">III", nba, 80, 7, 8, 112 - 88 + 1)
    struct.pack_into(">I", nba, 92, 0x80000000)
    result = inspect_envelope(bytes(nba), "nba-2k11")
    assert result["event_entries"] == [dict(offset=80, raw_words=[7, 8], payload=112)]
    broken = bytearray(nba)
    struct.pack_into(">I", broken, 88, 1000)
    with pytest.raises(ValueError, match="bounds"):
        inspect_envelope(bytes(broken), "nba-2k11")
    with pytest.raises(ValueError, match="bounds"):
        inspect_envelope(bytes(nba[:92]), "nba-2k11")


@pytest.mark.parametrize(
    "profile,stride,pointer", [("nba-2k11", 20, 8), ("nba-2k14", 28, 16)]
)
def test_collection_layouts_have_separate_strides_and_reject_bad_targets(
    profile, stride, pointer
):
    raw = bytearray(8 + stride + 4)
    struct.pack_into(">II", raw, 0, 1, 5)
    struct.pack_into(">I", raw, 8 + pointer, stride - pointer + 1)
    result = inspect_collection(bytes(raw), profile)
    assert result["entry_stride"] == stride
    assert result["entries"][0]["payload"] == 8 + stride
    struct.pack_into(">I", raw, 8 + pointer, 0xFFFFFFFF)
    assert (
        inspect_collection(bytes(raw), profile)["entries"][0]["payload"]
        == 8 + pointer - 2
    )
    struct.pack_into(">I", raw, 8 + pointer, 100000)
    with pytest.raises(ValueError, match="bounds"):
        inspect_collection(bytes(raw), profile)


def test_native_motion_names_resolve_to_animation_bank_category():
    for name in (
        "nba_animations.iff",
        "animgraph_dribbler.iff",
        "siganims_generic.iff",
    ):
        h = hash_name(name)
        assert lookup()[h] == name
        assert category(dict(hash=h, name=name)) == "Animation banks"


def test_alias_index_detects_cycles_external_ids_and_wrong_profiles():
    from choops_py.formats.motion_envelope import inspect_links
    from choops_py.formats.standard_iff import StandardIFF

    a, b = bytearray(64), bytearray(64)
    struct.pack_into(">I", a, 0x30, 222)
    struct.pack_into(">I", b, 0x30, 111)
    raw = bytearray(
        iff_fixture([bytes(a + b)], [(0x60900D71, [0]), (0x60900D71, [64])])
    )
    iff = StandardIFF(raw)
    for index, identity in enumerate((111, 222)):
        field = iff.record_table + index * 4
        record = field + struct.unpack_from(">I", raw, field)[0] - 1
        struct.pack_into(">I", raw, record, identity)
    report = inspect_links(bytes(raw), "college-hoops-2k8")
    assert report["local_alias_cycles"] == [[0, 1]]
    assert all(r["status"] == "local-candidate" for r in report["records"])
    assert not report["import_supported"]
    with pytest.raises(ValueError, match="not established"):
        inspect_links(bytes(raw), "nba-2k14")
