import struct

import pytest

from choops_py.formats.motion_bind import (
    PARENTS,
    RIGS,
    canonical_channels,
    retarget_canonical_frames,
    verify_canonical_bind,
)
from choops_py.formats.motion_frames import decode_frame, layout, transcode_frames


def rig(profile):
    addresses = RIGS[profile]
    base = min(addresses.values()) & ~15
    length = (
        max(
            addresses["parents"] + 84,
            addresses["rest"] + 336,
            addresses["routing"] + 63,
        )
        - base
    )
    raw = bytearray(0x100 + length)
    raw[:7] = b"\x7fELF\x02\x02\x01"
    struct.pack_into(">HH", raw, 16, 2, 21)
    struct.pack_into(">Q", raw, 32, 64)
    struct.pack_into(">HH", raw, 54, 56, 1)
    struct.pack_into(">II6Q", raw, 64, 1, 4, 0x100, base, base, length, length, 16)
    # Format hierarchy with synthetic translations, not copied game assets.
    struct.pack_into(">21I", raw, 0x100 + addresses["parents"] - base, *PARENTS)
    for i in range(21):
        struct.pack_into(
            ">4f",
            raw,
            0x100 + addresses["rest"] - base + i * 16,
            i * 0.25,
            -i * 0.5,
            i * 0.125,
            0,
        )
    start = 0x100 + addresses["routing"] - base
    raw[start : start + 63] = bytes(v for i in range(21) for v in (0, i, i))
    return raw, base


def header(profile, translations=0x49244):
    raw = bytearray(64)
    struct.pack_into(">I", raw, 4 if profile == "college-hoops-2k8" else 8, 0x1DF7DD)
    struct.pack_into(">I", raw, 12, translations)
    struct.pack_into(
        ">I", raw, 16, (21 << 18) | (17 << 12) | (translations.bit_count() << 6)
    )
    return raw


def test_identity_bind_preserves_decoded_pose_padding_and_reverse_bytes():
    donor, _ = rig("nba-2k11")
    target, _ = rig("college-hoops-2k8")
    channels = canonical_channels(header("nba-2k11"), "nba-2k11")
    _, size = layout(17, 6, 2)
    raw = bytearray(size)
    # Distinguishable translation and unused fourth-channel padding bytes.
    for frame in range(2):
        for channel in range(17, 24):
            at = frame * 144 + channel // 4 * 24 + channel % 4 * 2
            for axis in range(3):
                struct.pack_into(">H", raw, at + axis * 8, 1000 + channel * 10 + axis)
    before = bytes(raw)
    output, report = retarget_canonical_frames(
        raw, header("nba-2k11"), 2, donor, target
    )
    assert report["bind_equivalent"] and not report["gameplay_ready"]
    assert report["translation_bones"] == channels["translation_bones"]
    for frame in range(2):
        assert decode_frame(
            output, 17, 6, 2, frame, "college-hoops-2k8"
        ) == decode_frame(raw, 17, 6, 2, frame, "nba-2k11")
    assert transcode_frames(output, 17, 6, 2, "college-hoops-2k8", "nba-2k11") == before
    assert raw == before


@pytest.mark.parametrize("field,offset", [("parents", 8), ("rest", 0), ("routing", 2)])
def test_changed_bind_or_route_blocks_retarget(field, offset):
    donor, base = rig("nba-2k11")
    target, _ = rig("college-hoops-2k8")
    donor[0x100 + RIGS["nba-2k11"][field] - base + offset] ^= 1
    with pytest.raises(ValueError):
        verify_canonical_bind(donor, target)


@pytest.mark.parametrize("mask", [299588, 299520, 299972, 266820, 299589])
def test_observed_translation_variants_keep_their_own_declared_channels(mask):
    result = canonical_channels(header("nba-2k11", mask), "nba-2k11")
    assert result["translations"] == mask.bit_count()
    assert result["translation_bones"] == [i for i in range(21) if mask >> i & 1]


def test_mask_count_mismatch_and_unknown_high_mask_rejected():
    raw = header("nba-2k11")
    raw[19] ^= 64
    with pytest.raises(ValueError, match="counts"):
        canonical_channels(raw, "nba-2k11")
    raw = header("college-hoops-2k8")
    raw[8] = 1
    with pytest.raises(ValueError, match="extended"):
        canonical_channels(raw, "college-hoops-2k8")


def test_unpacked_native_branch_is_never_read_as_packed_quaternions():
    donor, _ = rig("nba-2k11")
    target, _ = rig("college-hoops-2k8")
    raw = header("nba-2k11")
    struct.pack_into(">I", raw, 0x14, 0x8000)
    with pytest.raises(ValueError, match="unpacked pose"):
        retarget_canonical_frames(bytes(144), raw, 1, donor, target)


def test_bind_cli_inspects_both_sources_and_never_overwrites_target(
    tmp_path, monkeypatch
):
    import json

    from choops_py.archive import manifests
    from choops_py.cli import execute, parser

    monkeypatch.setattr(manifests, "OUTPUT", tmp_path)
    donor, _ = rig("nba-2k11")
    target, _ = rig("college-hoops-2k8")
    source_path, target_path = tmp_path / "donor.elf", tmp_path / "target.elf"
    source_path.write_bytes(donor)
    target_path.write_bytes(target)
    output = tmp_path / "bind.json"
    execute(
        parser().parse_args(
            ["inspect-motion-bind", str(source_path), str(target_path), str(output)]
        )
    )
    assert json.loads(output.read_text())["bind_equivalent"]
    with pytest.raises(ValueError, match="overwrite input"):
        execute(
            parser().parse_args(
                [
                    "inspect-motion-bind",
                    str(source_path),
                    str(target_path),
                    str(target_path),
                ]
            )
        )
    assert source_path.read_bytes() == donor and target_path.read_bytes() == target
