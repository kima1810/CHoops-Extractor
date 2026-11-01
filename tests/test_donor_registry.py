import struct

import pytest
from support import iff_fixture

from choops_py.formats.standard_iff import StandardIFF
from choops_py.research.donor_registry import (
    COLLECTION,
    GROUP,
    MOTION,
    inspect_banks,
    inspect_entries,
    reference_selection,
)


@pytest.mark.parametrize(
    "kind,mode,member,offset",
    [
        (0, "direct", None, None),
        (1, "group-member", 0, 12),
        (4, "group-member", 3, 60),
        (5, "disabled", None, None),
        (6, "unestablished", None, None),
        (0xFFFFFFFF, "unestablished", None, None),
    ],
)
def test_native_reference_selection_does_not_default_unknown_kinds(
    kind, mode, member, offset
):
    assert reference_selection(kind) == dict(
        mode=mode, group_member=member, runtime_offset=offset
    )


def collection(category=0, ordinal=0):
    count = 8 if category == 0 else 1 if 2 <= category <= 10 else 2
    raw = bytearray(28 + count * 12 + 4)
    struct.pack_into(">II", raw, 0, 1, 5)
    struct.pack_into(">5I", raw, 8, 101, category, 13, ordinal, 0)
    for slot in range(count):
        struct.pack_into(">3I", raw, 28 + slot * 12, 1000 + slot, slot % 2, 0)
    raw[-4:] = b"TAIL"
    return raw


@pytest.mark.parametrize(
    "category,slots", [(0, 8), (1, 2), (2, 1), (10, 1), (11, 2), (14, 2), (30, 2)]
)
def test_native_category_walk_uses_typed_references_and_keeps_unknown_tail(
    category, slots
):
    raw = collection(category)
    before = bytes(raw)
    row = inspect_entries(raw)[0]
    assert len(row["references"]) == slots and row["unparsed_tail_bytes"] == 4
    assert row["localization_key"] == 101 and row["ordinal_word"] == 0
    assert row["references"][0]["resource_type_hash"] == MOTION
    if slots > 1:
        assert row["references"][1]["resource_type_hash"] == GROUP
    assert not row["payload_semantics_complete"] and raw == before


def bank_with_resource(typ, identity):
    raw = bytearray(iff_fixture([bytes(64)], [(typ, [0])]))
    iff = StandardIFF(raw)
    field = iff.record_table
    record = field + struct.unpack_from(">I", raw, field)[0] - 1
    struct.pack_into(">I", raw, record, identity)
    return bytes(raw)


def test_related_bank_resolution_uses_type_and_id_and_never_selects_duplicate_winner():
    raw = collection(2)
    signature = iff_fixture([bytes(raw)], [(COLLECTION, [0])])
    motion = bank_with_resource(MOTION, 1000)
    wrong = bank_with_resource(GROUP, 1000)
    report = inspect_banks([("signature", signature), ("wrong-type", wrong)])
    assert report["reference_counts"] == {"external-or-missing": 1}
    report = inspect_banks([("signature", signature), ("motion", motion)])
    ref = report["entries"][0]["references"][0]
    assert ref["status"] == "resolved-identity" and ref["candidates"] == [
        {"bank": 1, "record": 0}
    ]
    report = inspect_banks([("signature", signature), ("a", motion), ("b", motion)])
    assert report["reference_counts"] == {"ambiguous": 1}
    assert not report["runtime_registration_installed"]


def test_registry_rejects_bad_category_extent_stale_runtime_pointer_and_other_game():
    raw = collection()
    struct.pack_into(">I", raw, 12, 31)
    with pytest.raises(ValueError, match="category"):
        inspect_entries(raw)
    raw = collection()
    struct.pack_into(">I", raw, 36, 0x1000)
    with pytest.raises(ValueError, match="cache pointer"):
        inspect_entries(raw)
    with pytest.raises(ValueError, match="extent"):
        inspect_entries(collection()[:40])
    with pytest.raises(ValueError, match="only for NBA11"):
        inspect_entries(collection(), "nba-2k14")


def test_large_ordinal_is_reported_without_allocating_a_range_of_that_size():
    raw = iff_fixture([bytes(collection(2, 0xFFFFFFFF))], [(COLLECTION, [0])])
    report = inspect_banks([("synthetic", raw)])
    assert report["categories"][0]["contiguous_from_zero"] is False


def test_cli_protects_related_banks_and_rejects_other_game_before_output(
    tmp_path, monkeypatch
):
    import json

    from choops_py.archive import manifests
    from choops_py.cli import execute, parser

    monkeypatch.setattr(manifests, "OUTPUT", tmp_path)
    source, related = tmp_path / "collection.iff", tmp_path / "motion.iff"
    source.write_bytes(iff_fixture([bytes(collection(2))], [(COLLECTION, [0])]))
    related.write_bytes(bank_with_resource(MOTION, 1000))
    before = source.read_bytes(), related.read_bytes()
    output = tmp_path / "registry.json"
    args = [
        "inspect-donor-registry",
        str(source),
        "nba-2k11",
        str(output),
        "--related-bank",
        str(related),
    ]
    execute(parser().parse_args(args))
    assert json.loads(output.read_text())["reference_counts"] == {
        "resolved-identity": 1
    }
    args[3] = str(related)
    with pytest.raises(ValueError, match="overwrite input"):
        execute(parser().parse_args(args))
    args[2] = "nba-2k14"
    args[3] = str(tmp_path / "rejected.json")
    with pytest.raises(ValueError, match="NBA11"):
        execute(parser().parse_args(args))
    assert not (tmp_path / "rejected.json").exists()
    assert (source.read_bytes(), related.read_bytes()) == before
