"""Synthetic native-layout and CLI audits, with no game/save writes."""

import json
import struct
from hashlib import sha256

import pytest

from choops_py.research.recruit_pool import (
    INTEREST_CAPACITY,
    MAX_RECRUITS,
    RECRUIT_STRIDE,
    RECRUITING_STATE_SIZE,
    inspect_interest_graph,
    inspect_recruit_pool,
    inspect_recruiting_section,
)
from choops_py.roster.schema import HEADER_TABLES


def pool_fixture():
    data = bytearray(0x10000)
    cursor = 0x100
    for field, bias, stride, _ in HEADER_TABLES.values():
        struct.pack_into(">Ii", data, field, 1, cursor - field - 4 + bias)
        cursor += stride
        cursor = (cursor + 3) & ~3
    start = cursor
    struct.pack_into(">Ii", data, 0x48, 3, start - 0x4C + 1)
    at = start + RECRUIT_STRIDE
    data[at + 0x2D] = 5
    struct.pack_into(
        ">II", data, at + 0x40, (1 << 31) | (5 << 21) | (95 << 7), 1023 << 3
    )
    struct.pack_into(">H", data, at + 0x4A, 0xFFFF)
    data[at + 0x90] = 0xAD  # Uninterpreted bytes must remain unchanged.
    return data[: start + 3 * RECRUIT_STRIDE], start


def interest_fixture():
    data = bytearray(bytes.fromhex("7fffffff00000000") * INTEREST_CAPACITY)
    struct.pack_into(">hhhBB", data, 0, 1, 1, 100, 0x9A, 0xBC)
    struct.pack_into(">hhhBB", data, 8, 2, -1, -7, 0, 1)
    struct.pack_into(">h", data, 2 * 8 + 2, 3)
    return data


def test_native_pool_offsets_metadata_blanks_and_source_preservation():
    data, start = pool_fixture()
    before = bytes(data)
    report = inspect_recruit_pool(data)
    assert report["pool_start"] == start
    assert report["allocated_slots"] == 3
    assert report["blank_records"] == 2
    assert report["nonzero_records"] == 1
    row = report["records"][0]
    assert row["slot"] == 1 and row["class_label"] == "JC SO"
    assert row["preference_index"] == 95 and row["location_id"] == 1023
    assert row["committed_bit"] and row["recruiting_filter_bit_2"]
    assert row["interest_head"] == 0xFFFF and row["issues"] == []
    assert (
        row["record_sha256"]
        == sha256(data[start + RECRUIT_STRIDE : start + 2 * RECRUIT_STRIDE]).hexdigest()
    )
    assert not report["blank_slots_certified_reusable"]
    assert (
        not report["native_pool_insertion_installed"] and not report["gameplay_ready"]
    )
    assert bytes(data) == before


def test_unknown_classes_profiles_and_heads_are_reported_not_reinterpreted():
    data, start = pool_fixture()
    at = start + RECRUIT_STRIDE
    struct.pack_into(">I", data, at + 0x40, (9 << 21) | (127 << 7))
    struct.pack_into(">H", data, at + 0x4A, 16000)
    row = inspect_recruit_pool(data)["records"][0]
    assert row["class_label"] is None and row["preferences"] is None
    assert row["issues"] == [
        "unestablished_class_code",
        "uninitialized_preference_profile",
        "unsupported_interest_head",
    ]


@pytest.mark.parametrize(
    "case",
    [
        "null",
        "count",
        "negative",
        "unaligned",
        "truncated",
        "overlap",
        "other_directory",
    ],
)
def test_unsafe_pool_descriptor_rejected(case):
    data, start = pool_fixture()
    if case == "null":
        struct.pack_into(">i", data, 0x4C, 0)
    elif case == "count":
        struct.pack_into(">I", data, 0x48, MAX_RECRUITS + 1)
    elif case == "negative":
        struct.pack_into(">i", data, 0x4C, -0x100)
    elif case == "unaligned":
        struct.pack_into(">i", data, 0x4C, start - 0x4C + 2)
    elif case == "truncated":
        data = data[:-1]
    elif case == "overlap":
        struct.pack_into(">i", data, 0x4C, 0x100 - 0x4C + 1)
    else:
        struct.pack_into(">Ii", data, 0x50, 1, start + 8 - 0x54 + 1)
    with pytest.raises(ValueError):
        inspect_recruit_pool(data)


def test_backward_pool_pointer_cannot_point_into_header():
    data, _ = pool_fixture()
    # A backward target cannot point outside the directory/header.
    struct.pack_into(">i", data, 0x4C, -1)
    with pytest.raises(ValueError):
        inspect_recruit_pool(data)


def test_recruit_pool_rejects_wrong_type_before_allocating():
    with pytest.raises(ValueError):
        inspect_recruit_pool(10**1000)


def test_interest_graph_signed_scores_flags_ownership_and_free_nodes():
    data = interest_fixture()
    before = bytes(data)
    report = inspect_interest_graph(
        data, {4: 0, 9: 0xFFFF}, school_count=3, free_head=2
    )
    assert report["live_nodes"] == 2 and report["free_nodes_traced"] == 2
    assert report["unowned_nodes"] == INTEREST_CAPACITY - 4
    assert report["chains"][0]["nodes"][0] == {
        "index": 0,
        "school_index": 1,
        "score": 100,
        "byte_6": 0x9A,
        "byte_7": 0xBC,
    }
    assert report["chains"][0]["nodes"][1]["score"] == -7
    assert report["chains"][0]["descending_score_order"]
    assert not report["enclosing_save_offset_established"] and bytes(data) == before


def test_unknown_free_head_does_not_claim_remaining_nodes_are_leaked():
    report = inspect_interest_graph(interest_fixture(), {0: 0}, school_count=3)
    assert not report["free_head_supplied"] and report["free_nodes_traced"] == 0
    assert report["unowned_nodes"] == INTEREST_CAPACITY - 2


@pytest.mark.parametrize(
    "case",
    [
        "cycle",
        "shared",
        "free_alias",
        "free_cycle",
        "duplicate_school",
        "bad_school",
        "bad_next",
        "wrong_free_school",
    ],
)
def test_interest_graph_rejects_structural_corruption(case):
    data = interest_fixture()
    heads = {0: 0}
    free = None
    if case == "cycle":
        struct.pack_into(">h", data, 10, 0)
    elif case == "shared":
        heads[1] = 1
    elif case == "free_alias":
        free = 1
    elif case == "free_cycle":
        heads = {}
        free = 2
        struct.pack_into(">h", data, 26, 2)
    elif case == "duplicate_school":
        struct.pack_into(">h", data, 8, 1)
    elif case == "bad_school":
        struct.pack_into(">h", data, 0, 3)
    elif case == "bad_next":
        struct.pack_into(">h", data, 2, 16000)
    else:
        heads = {}
        free = 0
    with pytest.raises(ValueError):
        inspect_interest_graph(data, heads, school_count=3, free_head=free)


def test_interest_score_order_mismatch_reported_without_guessing_score_semantics():
    data = interest_fixture()
    struct.pack_into(">h", data, 12, 101)
    assert not inspect_interest_graph(data, {0: 0}, school_count=3)["chains"][0][
        "descending_score_order"
    ]


@pytest.mark.parametrize(
    "nodes,heads,count,free",
    [
        (bytes(1), {}, 3, None),
        (10**1000, {}, 3, None),
        (None, {True: 0}, 3, None),
        (None, {0: True}, 3, None),
        (None, {0: 16000}, 3, None),
        (None, {}, True, None),
        (None, {}, 0, None),
        (None, [], 3, None),
        (None, {}, 3, True),
    ],
)
def test_invalid_interest_inputs_rejected(nodes, heads, count, free):
    if nodes is None:
        nodes = interest_fixture()
    with pytest.raises(ValueError):
        inspect_interest_graph(nodes, heads, school_count=count, free_head=free)


def test_cli_audit_writes_report_preserves_input_and_rejects_source_outputs(
    tmp_path, monkeypatch
):
    from choops_py import cli
    from choops_py.archive import manifests

    output = tmp_path / "out"
    output.mkdir()
    monkeypatch.setattr(manifests, "OUTPUT", output)
    data, _ = pool_fixture()
    source = output / "source.rost"
    source.write_bytes(data)
    destination = output / "report.json"
    report = cli.execute(
        cli.parser().parse_args(["inspect-recruit-pool", str(source), str(destination)])
    )
    assert report["source_kind"] == "raw-rost"
    assert json.loads(destination.read_text())["allocated_slots"] == 3
    assert source.read_bytes() == data
    with pytest.raises(ValueError, match="overwrite"):
        cli.execute(
            cli.parser().parse_args(["inspect-recruit-pool", str(source), str(source)])
        )
    with pytest.raises(ValueError, match="requires"):
        cli.execute(
            cli.parser().parse_args(
                [
                    "inspect-recruit-pool",
                    str(source),
                    str(destination),
                    "--free-head",
                    "0",
                ]
            )
        )


def test_cli_interest_dependency_source_protected_and_bad_block_rejected(
    tmp_path, monkeypatch
):
    from choops_py import cli
    from choops_py.archive import manifests

    output = tmp_path / "out"
    output.mkdir()
    monkeypatch.setattr(manifests, "OUTPUT", output)
    data, start = pool_fixture()
    struct.pack_into(">H", data, start + RECRUIT_STRIDE + 0x4A, 0)
    # The synthetic roster has one school, so live nodes must use school zero.
    nodes = interest_fixture()
    struct.pack_into(">hhhBB", nodes, 0, 0, -1, 10, 2, 3)
    source = output / "source.rost"
    source.write_bytes(data)
    dependency = output / "nodes.bin"
    dependency.write_bytes(nodes)
    args = [
        "inspect-recruit-pool",
        str(source),
        str(output / "report.json"),
        "--interest-nodes",
        str(dependency),
    ]
    report = cli.execute(cli.parser().parse_args(args))
    assert report["interest_graph"]["live_nodes"] == 1
    args[2] = str(dependency)
    with pytest.raises(ValueError, match="overwrite"):
        cli.execute(cli.parser().parse_args(args))
    assert dependency.read_bytes() == nodes
    dependency.write_bytes(b"bad")
    args[2] = str(output / "report.json")
    with pytest.raises(ValueError, match="16000"):
        cli.execute(cli.parser().parse_args(args))


def state_fixture():
    state = bytearray(RECRUITING_STATE_SIZE)
    struct.pack_into(">ii", state, 0, 0, -1)
    for index in range(INTEREST_CAPACITY):
        struct.pack_into(
            ">hhhBB",
            state,
            0x28 + index * 8,
            0x7FFF,
            index + 1 if index + 1 < INTEREST_CAPACITY else -1,
            0,
            0,
            0,
        )
    return state


def test_serialized_section_offsets_full_free_chain_and_opaque_tail_preserved():
    data, _ = pool_fixture()
    state = state_fixture()
    struct.pack_into(">I", state, 8, 1)
    struct.pack_into(">5I", state, 0x3E828, 7, 0x100, 0x200, 0x300, 0xABCDEF)
    state[-10:] = b"KEEP OPAQE"
    before = bytes(state)
    result = inspect_recruiting_section(state, data)
    assert result["interest_graph"]["free_nodes_traced"] == 16000
    assert result["interest_graph"]["unowned_nodes"] == 0
    assert result["native_aggregate_relative_offset"] == 0x11418
    assert result["queue_counts"] == (1, 0, 0, 0)
    assert result["queues"][0]["roster_relative_words"] == (0x100, 0x200, 0x300)
    assert result["queues"][0]["references_within_roster"]
    assert not result["queues"][0]["referent_types_established"]
    assert not result["userdata_offset_established"]
    assert not result["secondary_node_ownership_validated"]
    assert not result["full_native_state_semantics_established"]
    assert bytes(state) == before


def test_section_uses_native_flag_filter_not_every_nonzero_record():
    data, start = pool_fixture()
    at = start + RECRUIT_STRIDE
    data[at + 0x2D] = 1  # Outside the native &4 ownership traversal.
    struct.pack_into(">H", data, at + 0x4A, 0)
    # Head aliases the free list, but is deliberately inactive under native rules.
    result = inspect_recruiting_section(state_fixture(), data)
    assert result["interest_graph"]["live_nodes"] == 0
    assert result["interest_graph"]["free_nodes_traced"] == 16000


@pytest.mark.parametrize(
    "case", ["size", "queue_count", "secondary_head", "live_free_alias"]
)
def test_invalid_serialized_section_rejected(case):
    data, start = pool_fixture()
    state = state_fixture()
    if case == "size":
        state = state[:-1]
    elif case == "queue_count":
        struct.pack_into(">I", state, 8, 129)
    elif case == "secondary_head":
        struct.pack_into(">i", state, 4, 16000)
    else:
        struct.pack_into(">H", data, start + RECRUIT_STRIDE + 0x4A, 0)
    with pytest.raises(ValueError):
        inspect_recruiting_section(state, data)


def test_serialized_secondary_and_queue_references_are_diagnostics_not_repaired():
    data, _ = pool_fixture()
    state = state_fixture()
    struct.pack_into(">I", state, 0x1F428, len(data) + 1)
    struct.pack_into(">I", state, 8, 1)
    struct.pack_into(">I", state, 0x3E828 + 4, len(data) + 1)
    before = bytes(state)
    report = inspect_recruiting_section(state, data)
    assert report["secondary_references_outside_roster"] == 1
    assert not report["queues"][0]["references_within_roster"]
    assert bytes(state) == before


def test_cli_serialized_section_and_all_dependency_outputs_protected(
    tmp_path, monkeypatch
):
    from choops_py import cli
    from choops_py.archive import manifests

    output = tmp_path / "out"
    output.mkdir()
    monkeypatch.setattr(manifests, "OUTPUT", output)
    source = output / "roster.bin"
    source.write_bytes(pool_fixture()[0])
    section = output / "state.bin"
    section.write_bytes(state_fixture())
    args = [
        "inspect-recruit-pool",
        str(source),
        str(output / "report.json"),
        "--recruiting-state",
        str(section),
    ]
    assert (
        cli.execute(cli.parser().parse_args(args))["recruiting_state"]["bytes"]
        == RECRUITING_STATE_SIZE
    )
    args[2] = str(section)
    with pytest.raises(ValueError, match="overwrite"):
        cli.execute(cli.parser().parse_args(args))
    with pytest.raises(SystemExit):
        cli.parser().parse_args(args + ["--interest-nodes", str(section)])


def test_legacy_wrapper_pool_read_keeps_outer_state_opaque_and_unchanged():
    from test_legacy_save_adapter import legacy_fixture

    from choops_py.roster.adapters import LEGACY_SAVE_ROSTER_OFFSET, load_bytes

    data = bytearray(legacy_fixture())
    base = LEGACY_SAVE_ROSTER_OFFSET
    # Correct this synthetic fixture's uniform placement so it does not overlap
    # the newly established recruit table; production inputs are never moved.
    struct.pack_into(">Ii", data, base + 0x70, 988, 0x343778 - 0x74 + 1)
    struct.pack_into(">Ii", data, base + 0x48, 2000, 0x2ABFC8 - 0x4C + 1)
    before = bytes(data)
    source = load_bytes(before)
    assert source.kind == "legacy-save"
    report = inspect_recruit_pool(source.payload)
    assert report["allocated_slots"] == report["blank_records"] == 2000
    assert source.encode(source.payload) == before
    assert bytes(data) == before
