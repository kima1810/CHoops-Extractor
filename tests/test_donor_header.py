import hashlib
import struct

import pytest
from test_motion_sampling import source_files

from choops_py.formats.embedded_motion import NativeELF
from choops_py.formats.motion_events import curve_timing_contract
from choops_py.formats.motion_frames import resample_nba11_frames, resample_nba11_root
from choops_py.research.donor_header import translate_donor_motion
from choops_py.research.target_motion import relocate_target_image


def inputs(tmp_path):
    a, b, address, *_ = source_files(tmp_path)
    return a.read_bytes(), b.read_bytes(), address


def contract(donor, target, address):
    header = NativeELF(donor).read(address, 56)
    return dict(
        schema=1,
        source_sha256=hashlib.sha256(donor).hexdigest(),
        target_sha256=hashlib.sha256(target).hexdigest(),
        source_header_address=address,
        source_header_sha256=hashlib.sha256(header).hexdigest(),
        target_mode_high16=0x2164,
        target_state_bits=0x12345678,
        authored_planar=[5, 3, 4],
        evidence={
            k: "Synthetic authoring assertion; not real-game metadata proof"
            for k in ("mode", "state", "planar")
        },
    )


def translated(donor, target, address, metadata=None, **kwargs):
    return translate_donor_motion(
        donor,
        target,
        address,
        metadata or contract(donor, target, address),
        curve_timing_contract(),
        **kwargs,
    )


def test_translation_rebuilds_target_layout_tracks_and_timing_without_template(
    tmp_path,
):
    donor, target, address = inputs(tmp_path)
    before = donor, target
    image, r = translated(donor, target, address)
    assert r["target_frame_count"] == 6 and r["source_key_count"] == 3
    assert (
        not r["metadata_automatically_established"] and not r["native_loader_installed"]
    )
    assert struct.unpack_from(">4I", image) == (0, 0x1DF7DD, 0, 0x49244)
    assert struct.unpack_from(">II", image, 20) == (0x21640006, 0x12345678)
    assert struct.unpack_from(">3f", image, 36) == (5, 3, 4)
    elf = NativeELF(donor)
    h = elf.read(address, 56)
    assert image[28:36] == h[28:36]
    timing, poses, root, _, _ = struct.unpack_from(">5I", h, 36)
    deltas = elf.read(timing, 3)
    expected, _ = resample_nba11_frames(elf.read(poses, 432), deltas, 17, 6)
    roots = resample_nba11_root(elf.read(root, 24), deltas)
    for extent, wanted in zip(
        r["extents"], (expected, roots, struct.pack(">I", 0x80000000)), strict=True
    ):
        assert image[extent["offset"] : extent["offset"] + extent["bytes"]] == wanted
    native = relocate_target_image(image, [0], 0x30000000, source_state="relative")
    assert (
        relocate_target_image(native, [0], 0x30000000, source_state="native") == image
    )
    assert before == (donor, target)


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_header_sha256", "stale"),
        ("source_sha256", "stale"),
        ("target_sha256", "stale"),
        ("source_header_address", 0),
        ("target_mode_high16", 0x1164),
        ("target_state_bits", None),
        ("authored_planar", [float("nan"), 0, 0]),
        ("evidence", {}),
    ],
)
def test_explicit_metadata_contract_rejects_stale_unknown_and_incompatible_assertions(
    tmp_path, field, value
):
    donor, target, address = inputs(tmp_path)
    c = contract(donor, target, address)
    c[field] = value
    with pytest.raises(ValueError):
        translated(donor, target, address, c)


def test_missing_contract_and_budget_block_before_resampling(tmp_path, monkeypatch):
    donor, target, address = inputs(tmp_path)
    with pytest.raises(ValueError, match="contract"):
        translate_donor_motion(donor, target, address, None, curve_timing_contract())

    def forbid(*args, **kwargs):
        raise AssertionError("Must reject before expanded allocation")

    monkeypatch.setattr("choops_py.research.donor_header.resample_nba11_frames", forbid)
    with pytest.raises(ValueError, match="byte budget"):
        translated(donor, target, address, budget=64)


def test_opaque_events_auxiliary_extents_and_unpacked_layout_do_not_translate(tmp_path):
    original, target, address = inputs(tmp_path)
    elf = NativeELF(original)
    at = elf.target(address)["file_offset"]
    for delta, value, match in [
        (4, 0x10000, "auxiliary"),
        (52, 0x10000, "auxiliary"),
        (20, 0x21648003, "Unpacked"),
    ]:
        donor = bytearray(original)
        struct.pack_into(">I", donor, at + delta, value)
        with pytest.raises(ValueError, match=match):
            translated(donor, target, address)
    donor = bytearray(original)
    events = struct.unpack_from(">I", original, at + 48)[0]
    p = elf.target(events)["file_offset"]
    struct.pack_into(">ifI", donor, p, 17, 0.01, 0)
    struct.pack_into(">I", donor, p + 12, 0x80000000)
    with pytest.raises(ValueError, match="No explicit mapping"):
        translated(donor, target, address)


@pytest.mark.parametrize("which", ["donor", "target"])
def test_contract_fingerprint_covers_streams_and_target_revision_not_only_header(
    tmp_path, which
):
    donor, target, address = inputs(tmp_path)
    c = contract(donor, target, address)
    if which == "donor":
        changed = bytearray(donor)
        changed[-1] ^= 1
        donor = bytes(changed)
    else:
        changed = bytearray(target)
        changed[8] ^= 1
        target = bytes(changed)
    with pytest.raises(ValueError, match="fingerprint"):
        translated(donor, target, address, c)


def test_exact_aligned_component_budget_is_accepted(tmp_path):
    donor, target, address = inputs(tmp_path)
    data, _ = translated(donor, target, address)
    assert translated(donor, target, address, budget=len(data))[0] == data


def test_huge_integer_authoring_value_is_rejected_before_float_conversion(tmp_path):
    donor, target, address = inputs(tmp_path)
    c = contract(donor, target, address)
    c["authored_planar"] = [2**2048, 0, 0]
    with pytest.raises(ValueError, match="finite authored"):
        translated(donor, target, address, c)
