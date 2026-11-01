import json
import struct

import pytest

from choops_py.formats.motion_events import (
    curve_timing_contract,
    inspect_auxiliary_pairs,
    inspect_events,
    inspect_payload_consumers,
    mirrored_marker_contract,
    transcode_events,
)

NBA = "nba-2k11"
CH = "college-hoops-2k8"
END = struct.pack(">i", -0x80000000)


def test_native_curve_cache_roles_retain_their_times_including_nonuniform_enum_shift():
    # Native cache offsets 0x20/0x30/0x34/0x38 are anchor/start/knot/end.
    nba_roles = {0x20: 20, 0x30: 37, 0x34: 46, 0x38: 38}
    ch_roles = {0x20: 19, 0x30: 36, 0x34: 40, 0x38: 37}
    times = {20: 0.5, 37: 0.1, 46: 0.4, 38: 0.9}
    raw = (
        b"".join(struct.pack(">ifI", key, value, 0) for key, value in times.items())
        + END
    )
    source = inspect_events(raw, NBA)
    converted, _ = transcode_events(source, curve_timing_contract())
    target = inspect_events(converted, CH)
    source_times = {row["id"]: row["time_bits"] for row in source["entries"]}
    target_times = {row["id"]: row["time_bits"] for row in target["entries"]}
    assert {field: source_times[marker] for field, marker in nba_roles.items()} == {
        field: target_times[marker] for field, marker in ch_roles.items()
    }
    assert 40 in target_times and 45 not in target_times
    with pytest.raises(ValueError, match="No explicit mapping"):
        transcode_events(
            inspect_events(struct.pack(">ifI", 47, 0, 0) + END, NBA),
            curve_timing_contract(),
        )


@pytest.mark.parametrize("mirrored", [False, True])
def test_verified_marker_map_commutes_with_native_mirror_selector(mirrored):
    # Native selectors swap the first two markers; the third remains invariant.
    nba = [22, 21, 23] if mirrored else [21, 22, 23]
    ch = [21, 20, 22] if mirrored else [20, 21, 22]
    raw = (
        b"".join(
            struct.pack(">ifI", marker, i * 0.25, 0) for i, marker in enumerate(nba)
        )
        + END
    )
    output, _ = transcode_events(inspect_events(raw, NBA), mirrored_marker_contract())
    assert [row["id"] for row in inspect_events(output, CH)["entries"]] == ch
    unknown = struct.pack(">ifI", 24, 0, 0) + END
    with pytest.raises(ValueError, match="No explicit mapping"):
        transcode_events(inspect_events(unknown, NBA), mirrored_marker_contract())


def contract(*rules):
    return dict(
        schema=1,
        rules=[
            dict(
                source_id=a,
                target_id=b,
                payload_word=c,
                evidence="Synthetic fixture only; no game semantic assertion",
            )
            for a, b, c in rules
        ],
    )


def test_event_bridge_preserves_duplicate_order_and_float_bits():
    # Equal timestamps, negative zero and repeated marker IDs must not be sorted
    # or deduplicated, nor reconstructed through decimal JSON float formatting.
    raw = (
        b"".join(
            struct.pack(">iII", a, b, 0)
            for a, b in [(23, 0x80000000), (17, 0x3EAAAAAB), (23, 0x3EAAAAAB)]
        )
        + END
    )
    before = bytes(raw)
    report = inspect_events(raw, NBA)
    output, info = transcode_events(report, contract((23, 22, None), (17, 16, None)))
    assert (
        output
        == b"".join(
            struct.pack(">iI", a, b)
            for a, b in [(22, 0x80000000), (16, 0x3EAAAAAB), (22, 0x3EAAAAAB)]
        )
        + END
    )
    assert info["events"] == 3 and not info["gameplay_ready"]
    assert info["time_bits_preserved"] and not info["complete_motion"]
    assert raw == before


@pytest.mark.parametrize("word", [0, 7, 0xFFFFFFFF])
def test_known_payload_consumer_needs_exact_rule_including_zero(word):
    raw = struct.pack(">iII", 90, 0x3F000000, 9) + END + struct.pack(">I", word)
    report = inspect_events(raw, NBA)
    assert report["entries"][0]["payload"] == 16
    assert report["entries"][0]["payload_word"] == word
    with pytest.raises(ValueError, match="No explicit mapping"):
        transcode_events(report, contract((90, 89, None)))
    output, _ = transcode_events(report, contract((90, 95, word)))
    assert inspect_events(output, CH)["entries"][0]["id"] == 95


def test_unknown_payload_never_silently_dropped():
    raw = struct.pack(">iII", 92, 0, 9) + END + bytes(4)
    report = inspect_events(raw, NBA)
    assert report["opaque_payloads"] == 1
    assert report["entries"][0]["payload_word"] is None
    with pytest.raises(ValueError, match="Opaque payload"):
        transcode_events(report, contract((92, 39, None)))


def test_traced_consumed_fields_do_not_establish_a_portable_payload():
    # Event 94 has two native table indices. Inspecting both must not allow the
    # event bridge to drop its payload or map those indices across games.
    raw = struct.pack(">iII", 94, 0, 9) + END + struct.pack(">ii", 7, 3)
    report = inspect_events(raw, NBA)
    fields = inspect_payload_consumers(raw, 94, 16)
    assert [field["value"] for field in fields["fields"]] == [7, 3]
    assert not fields["portable_semantics"] and not fields["complete_payload"]
    report["entries"][0]["consumed_fields"] = fields
    with pytest.raises(ValueError, match="Opaque payload"):
        transcode_events(report, contract((94, 93, None)))
    with pytest.raises(ValueError):
        inspect_payload_consumers(raw[:-1], 94, 16)


def test_payload_inspection_preserves_nonfinite_float_bits_without_json_nan():
    result = inspect_payload_consumers(struct.pack(">II", 1, 0x7FC01234), 92, 0)
    field = result["fields"][1]
    assert field["value"] is None and field["raw_bits"] == 0x7FC01234
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        bytes(11),
        struct.pack(">iII", 23, 0, 0),
        struct.pack(">iII", 90, 0, 8) + END,
        struct.pack(">iII", 90, 0, 1001) + END,
        struct.pack(">iII", 90, 0, 0) + END,
        struct.pack(">iII", 4, 0x7FC00000, 0) + END,
    ],
)
def test_event_parser_rejects_truncation_missing_sentinel_bad_payload_and_nan(raw):
    with pytest.raises(ValueError):
        inspect_events(raw, NBA)


def test_signed_relative_payload_can_point_before_table():
    raw = struct.pack(">I", 7) + struct.pack(">iII", 90, 0, 0xFFFFFFF5) + END
    report = inspect_events(raw, NBA, 4)
    assert report["entries"][0]["payload_word"] == 7
    assert report["sentinel"] == 16
    assert inspect_events(END, CH)["entries"] == []
    assert transcode_events(inspect_events(END, NBA), contract())[0] == END
    with pytest.raises(ValueError):
        inspect_events(raw, "nba-2k14")
    with pytest.raises(ValueError):
        inspect_events(raw, NBA, 1)


@pytest.mark.parametrize(
    "mapping",
    [
        dict(schema=2, rules=[]),
        dict(schema=1, rules={}),
        contract((23, 22, None), (23, 24, None)),
        contract((92, 39, 0)),
        dict(schema=1, rules=[dict(source_id=4, target_id=4, evidence="")]),
        contract((True, 4, None)),
        contract((4, -1, None)),
    ],
)
def test_mapping_contract_rejects_ambiguous_or_unsupported_rules(mapping):
    with pytest.raises(ValueError):
        transcode_events(inspect_events(END, NBA), mapping)


def test_native_addresses_and_full_payload_extent_must_be_file_backed():
    from test_embedded_motion import native_fixture

    raw = native_fixture(NBA)
    # Table in one file-backed range, payload in another, absolute pointers.
    struct.pack_into(">iIIi", raw, 0x280, 90, 0x3F000000, 0x20000, -0x80000000)
    struct.pack_into(">I", raw, 0x400, 7)
    assert (
        inspect_events(raw, NBA, 0x10080, native=True)["entries"][0]["payload_word"]
        == 7
    )
    struct.pack_into(">I", raw, 0x288, 0x20280)  # Native BSS, not file bytes.
    with pytest.raises(ValueError, match="file-backed"):
        inspect_events(raw, NBA, 0x10080, native=True)
    struct.pack_into(">I", raw, 0x288, 0x201FC)
    assert (
        inspect_events(raw, NBA, 0x10080, native=True)["entries"][0]["payload_word"]
        == 0
    )
    with pytest.raises(ValueError):
        inspect_events(raw, NBA, 0x101FC, native=True)


def test_auxiliary_membership_pairs_keep_second_word_opaque():
    raw = struct.pack(">5I", 2, 7, 0xDEADBEEF, 7, 0x12345678)
    report = inspect_auxiliary_pairs(raw, 0)
    assert report["entries"] == [
        dict(key=7, raw_value=0xDEADBEEF),
        dict(key=7, raw_value=0x12345678),
    ]
    assert not report["semantics_established"]
    for bad in (raw[:-1], struct.pack(">I", 0x7FFFFFFF), struct.pack(">i", -1)):
        with pytest.raises(ValueError):
            inspect_auxiliary_pairs(bad, 0)


def test_event_cli_validates_all_before_writing_and_protects_inputs(
    tmp_path, monkeypatch
):
    from choops_py import cli
    from choops_py.archive import manifests

    monkeypatch.setattr(manifests, "OUTPUT", tmp_path)
    source, mapping, target = [
        tmp_path / n for n in ("source.bin", "mapping.json", "target.bin")
    ]
    raw = struct.pack(">iII", 23, 0x3EAAAAAB, 0) + END
    source.write_bytes(raw)
    mapping.write_text(json.dumps(contract((23, 22, None))), encoding="utf-8")
    args = ["transcode-motion-events", str(source), NBA, "0", str(mapping)]
    for destination in (source, mapping):
        with pytest.raises(ValueError):
            cli.execute(cli.parser().parse_args([*args, str(destination)]))
    info = cli.execute(cli.parser().parse_args([*args, str(target)]))
    assert info["events"] == 1 and not info["gameplay_ready"]
    assert source.read_bytes() == raw
    target.unlink()
    mapping.write_text(json.dumps(contract()), encoding="utf-8")
    with pytest.raises(ValueError, match="No explicit mapping"):
        cli.execute(cli.parser().parse_args([*args, str(target)]))
    assert not target.exists()
    output = tmp_path / "events.json"
    cli.execute(
        cli.parser().parse_args(
            ["inspect-motion-events", str(source), NBA, "0", str(output)]
        )
    )
    assert json.loads(output.read_text(encoding="utf-8"))["entry_stride"] == 12
