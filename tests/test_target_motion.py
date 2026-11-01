import struct

import pytest
from test_motion_bind import header

from choops_py.research.target_motion import (
    inspect_target_motion,
    prepare_target_image,
    relocate_target_image,
)


def fixture():
    raw = bytearray(0x900)
    raw[:7] = b"\x7fELF\x02\x02\x01"
    struct.pack_into(">HH", raw, 16, 2, 21)
    struct.pack_into(">Q", raw, 32, 64)
    struct.pack_into(">HH", raw, 54, 56, 1)
    struct.pack_into(">II6Q", raw, 64, 1, 6, 0x100, 0x10000, 0x10000, 0x800, 0x900, 16)
    for offset in (0, 64):
        h = header("college-hoops-2k8")
        flags = struct.unpack_from(">I", h, 16)[0] | (15 << 24)
        struct.pack_into(">3I", h, 16, flags, 0x61640002, 0x12345678)
        # Authored metadata intentionally differs from root-endpoint estimates.
        struct.pack_into(">5f", h, 28, 0.75, 0.05, 5, -3, 4)
        struct.pack_into(">4I", h, 48, 0x10100, 0x10300, 0x10400, 0)
        raw[0x100 + offset : 0x140 + offset] = h
    raw[0x200:0x320] = bytes(i % 251 for i in range(288))
    struct.pack_into(">8h", raw, 0x400, *range(8))
    struct.pack_into(">ifI", raw, 0x500, 19, 0.025, 0x80000000)
    return raw


def test_owned_image_retains_metadata_deduplicates_tracks_and_roundtrips_bases():
    raw = fixture()
    original = bytes(raw)
    image, report = prepare_target_image(raw, [0x10000, 0x10040])
    assert report["role_counts"] == dict(header=2, poses=1, root=1, events=1)
    assert (
        report["source_header_metadata_preserved"] and not report["external_pointers"]
    )
    assert not report["native_registration_installed"]
    for offset in report["header_offsets"]:
        assert image[offset : offset + 48] == raw[0x100:0x130]
    for base in (0x20000000, 0x30000000):
        native = relocate_target_image(
            image, report["header_offsets"], base, source_state="relative"
        )
        for extent in report["extents"]:
            if extent["role"] == "header":
                offset = extent["offset"]
                for field in (0x30, 0x34, 0x38):
                    delta = struct.unpack_from(">i", image, offset + field)[0]
                    expected = base + offset + field + delta - 1
                    assert (
                        struct.unpack_from(">I", native, offset + field)[0] == expected
                    )
        assert (
            relocate_target_image(
                native, report["header_offsets"], base, source_state="native"
            )
            == image
        )
        with pytest.raises(ValueError, match="pointer state"):
            relocate_target_image(
                native, report["header_offsets"], base, source_state="relative"
            )
    assert raw == original


def test_target_audit_checks_later_frames_and_preserves_unknown_header_flags():
    raw = fixture()
    r = inspect_target_motion(raw, 0x10000)
    assert r["metadata"]["authored_planar_components"] == [-3, 4]
    assert r["metadata"]["raw_state_0x18"] == 0x12345678
    assert not r["metadata"]["complete_flag_semantics"]
    # First pose is file backed; the second crosses into BSS.
    struct.pack_into(">I", raw, 0x130, 0x10700)
    with pytest.raises(ValueError, match="fully file-backed"):
        inspect_target_motion(raw, 0x10000)


@pytest.mark.parametrize(
    "field,value", [(0x1C, float("nan")), (0x20, -1), (0x24, float("inf"))]
)
def test_bad_authoring_metadata_is_rejected(field, value):
    raw = fixture()
    struct.pack_into(">f", raw, 0x100 + field, value)
    with pytest.raises(ValueError):
        prepare_target_image(raw, [0x10000])


def test_missing_event_sentinel_budget_and_unknown_extents_fail_without_mutation():
    raw = fixture()
    struct.pack_into(">I", raw, 0x13C, 0x10600)
    before = bytes(raw)
    assert not inspect_target_motion(raw, 0x10000)["resident_image_supported"]
    with pytest.raises(ValueError, match="unknown dependency"):
        prepare_target_image(raw, [0x10000])
    assert raw == before
    raw = fixture()
    with pytest.raises(ValueError, match="byte budget"):
        prepare_target_image(raw, [0x10000], budget=64)
    # Sentinel omitted; all following rows fit until the actual image boundary.
    raw[0x508:] = bytes(len(raw) - 0x508)
    with pytest.raises(ValueError, match="fully file-backed"):
        prepare_target_image(raw, [0x10000])


@pytest.mark.parametrize("base", [0, 0x20000001, 0xFFFFFFF0])
def test_invalid_residency_ranges_fail(base):
    image, r = prepare_target_image(fixture(), [0x10000])
    with pytest.raises(ValueError, match="base/range"):
        relocate_target_image(image, r["header_offsets"], base, source_state="relative")


def test_aliases_wrong_state_and_overlapping_headers_are_rejected():
    raw = fixture()
    struct.pack_into(">I", raw, 0x138, 0)
    with pytest.raises(ValueError, match="Resolved"):
        prepare_target_image(raw, [0x10000])
    image, r = prepare_target_image(fixture(), [0x10000])
    with pytest.raises(ValueError, match="distinct"):
        relocate_target_image(image, [0, 0], 0x20000000, source_state="relative")
    with pytest.raises(ValueError, match="pointer state"):
        relocate_target_image(image, [0], 0x20000000, source_state="native")
    broken = bytearray(image)
    struct.pack_into(">i", broken, 0x30, 1 - 0x30)
    before = bytes(broken)
    with pytest.raises(ValueError, match="header storage"):
        relocate_target_image(broken, [0], 0x20000000, source_state="relative")
    assert broken == before


def test_relocation_checks_full_later_track_extent_before_returning_bytes():
    image, r = prepare_target_image(fixture(), [0x10000])
    bad = bytearray(image)
    struct.pack_into(">i", bad, 0x30, len(bad) - 16 - 0x30 + 1)
    before = bytes(bad)
    with pytest.raises(ValueError, match="fully file-backed"):
        relocate_target_image(
            bad, r["header_offsets"], 0x20000000, source_state="relative"
        )
    assert bad == before


def test_preparation_refuses_a_track_borrowing_another_selected_header():
    raw = fixture()
    struct.pack_into(">I", raw, 0x130, 0x10040)
    with pytest.raises(ValueError, match="overlaps header storage"):
        prepare_target_image(raw, [0x10000, 0x10040])
