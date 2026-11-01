import struct

import pytest
from test_motion_bind import header, rig

from choops_py.formats.embedded_motion import NativeELF
from choops_py.formats.motion_frames import (
    channel_offset,
    encode_quaternion,
    resample_nba11_frames,
    resample_nba11_root,
)
from choops_py.research.motion_sampling import MotionSampler, key_interval


def source_files(tmp_path, frames=3):
    donor, _ = rig("nba-2k11")
    target, _ = rig("college-hoops-2k8")
    first = (len(donor) + 255) & ~255
    base = 0x20000
    timing = bytes((1, 2, 255)) if frames == 3 else bytes(frames)
    pose_at = (0x100 + frames + 15) & ~15
    root_at = pose_at + 144 * frames
    size = root_at + frames * 8
    donor.extend(bytes(first + size - len(donor)))
    struct.pack_into(">HH", donor, 54, 56, 2)
    struct.pack_into(">II6Q", donor, 120, 1, 4, first, base, base, size, size + 64, 16)
    h = header("nba-2k11")[:56]
    flags = struct.unpack_from(">I", h, 0x10)[0] | 60 << 24
    struct.pack_into(">II", h, 0x10, flags, 0x21640000 | frames)
    struct.pack_into(">ff", h, 0x1C, 1, sum(x + 1 for x in timing[:-1]) / 60)
    struct.pack_into(
        ">5I", h, 0x24, base + 0x100, base + pose_at, base + root_at, base + 0x80, 0
    )
    donor[first : first + 56] = h
    donor[first + 0x80 : first + 0x84] = struct.pack(">i", -0x80000000)
    donor[first + 0x100 : first + 0x100 + frames] = timing
    root = b"".join(
        struct.pack(">4h", i * 8, -i * 3, i * 2, i * 10) for i in range(frames)
    )
    donor[first + root_at : first + root_at + len(root)] = root
    import math

    pose = bytearray(144 * frames)
    for frame in range(frames):
        for channel in range(23):
            at = channel_offset(frame, channel, 144)
            angle = frame * 0.05 + channel * 0.01
            words = (
                encode_quaternion((math.cos(angle), math.sin(angle), 0, 0), "nba-2k11")
                if channel < 17
                else (frame, channel * 10, 65535 - frame)
            )
            for axis, word in enumerate(words):
                struct.pack_into(">H", pose, at + axis * 8, word)
    donor[first + pose_at : first + pose_at + len(pose)] = pose
    source_path, target_path = tmp_path / "nba.elf", tmp_path / "ch.elf"
    source_path.write_bytes(donor)
    target_path.write_bytes(target)
    return source_path, target_path, base, pose, timing, root


def test_native_sampling_cli_never_overwrites_either_elf(tmp_path, monkeypatch):
    import json

    from choops_py.archive import manifests
    from choops_py.cli import execute, parser

    source, target, address, *_ = source_files(tmp_path)
    monkeypatch.setattr(manifests, "OUTPUT", tmp_path)
    args = ["sample-native-motion", str(source), str(target), hex(address), "0.025"]
    output = tmp_path / "sample.json"
    execute(parser().parse_args([*args, str(output)]))
    report = json.loads(output.read_text())
    assert len(bytes.fromhex(report["packed_pose_hex"])) == 144
    assert not report["runtime_hook_installed"]
    with pytest.raises(ValueError, match="overwrite input"):
        execute(parser().parse_args([*args, str(target)]))


def test_sparse_sampling_matches_full_reference_at_every_integer_tick(tmp_path):
    source, target, base, pose, timing, root = source_files(tmp_path)
    before = source.read_bytes(), target.read_bytes()
    full, info = resample_nba11_frames(pose, timing, 17, 6)
    full_root = resample_nba11_root(root, timing)
    with MotionSampler(source, target, cache_bytes=65536) as sampler:
        for tick in range(info["output_frames"]):
            result, metadata = sampler.sample(base, tick / 60)
            assert result == full[tick * 144 : (tick + 1) * 144]
            assert metadata["root_signed_words"] == struct.unpack_from(
                ">4h", full_root, tick * 8
            )
            assert (
                not metadata["events_dispatched"]
                and not metadata["runtime_hook_installed"]
            )
        stats = sampler.stats()
        assert stats["peak_retained_payload_bytes"] <= stats["payload_budget"]
        assert stats["hits"] > 0 and not stats["expanded_bank_allocated"]
    with pytest.raises(ValueError, match="closed"):
        sampler.sample(base, 0)
    assert (source.read_bytes(), target.read_bytes()) == before


def test_cache_evicts_under_a_long_scrub_instead_of_growing_with_bank(tmp_path):
    source, target, base, *_ = source_files(tmp_path, 600)
    with MotionSampler(source, target, cache_bytes=65536) as sampler:
        for frame in range(599):
            sampler.sample(base, (frame + 0.5) / 60)
        stats = sampler.stats()
        assert stats["evictions"] > 0
        assert stats["retained_payload_bytes"] <= 65536
        assert stats["max_decoded_key_poses"] == 2
        assert not stats["total_process_memory_bounded"]


def test_complete_extent_validation_blocks_a_truncated_later_key_at_time_zero(tmp_path):
    source, target, base, *_ = source_files(tmp_path)
    raw = bytearray(source.read_bytes())
    elf = NativeELF(raw)
    header_at = elf.file_span(base, 56)[0]
    # First key remains file-backed; last key would extend into native BSS.
    struct.pack_into(">I", raw, header_at + 0x28, base + 0x200)
    source.write_bytes(raw)
    with MotionSampler(source, target) as sampler:
        with pytest.raises(ValueError, match="fully file-backed"):
            sampler.sample(base, 0)


@pytest.mark.parametrize(
    "tick,expected",
    [
        (-1, (0, 0, 0)),
        (0, (0, 0, 0)),
        (1, (0, 1, 0.5)),
        (2, (1, 1, 0)),
        (3.5, (1, 2, 0.5)),
        (5, (2, 2, 0)),
        (100, (2, 2, 0)),
    ],
)
def test_native_timeline_boundary_and_terminal_byte(tick, expected):
    assert key_interval(bytes((1, 2, 255)), tick) == expected


def test_sampler_rejects_bad_header_timing_and_unsupported_pose_encoding(tmp_path):
    source, target, base, *_ = source_files(tmp_path)
    raw = bytearray(source.read_bytes())
    header_at = NativeELF(raw).file_span(base, 56)[0]
    struct.pack_into(">f", raw, header_at + 0x20, 100)
    source.write_bytes(raw)
    with MotionSampler(source, target) as sampler:
        with pytest.raises(ValueError, match="duration metadata"):
            sampler.sample(base, 0)
    struct.pack_into(">I", raw, header_at + 0x14, 0x21648003)
    source.write_bytes(raw)
    with MotionSampler(source, target) as sampler:
        with pytest.raises(ValueError, match="unpacked"):
            sampler.sample(base, 0)


def test_target_timestamp_change_invalidates_even_a_hot_payload_cache(tmp_path):
    import os

    source, target, base, *_ = source_files(tmp_path)
    with MotionSampler(source, target) as sampler:
        sampler.sample(base, 0)
        stat = target.stat()
        os.utime(target, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))
        with pytest.raises(ValueError, match="source changed"):
            sampler.sample(base, 0)
        assert sampler.stats()["retained_payload_bytes"] == 0


@pytest.mark.parametrize(
    "timing,tick", [(b"", 0), ("abc", 0), (bytes(32768), 0), (b"\x00", float("inf"))],
    ids=['empty','wrong-type','oversize','nonfinite']
)
def test_bad_timeline_is_rejected_without_expansion(timing, tick):
    with pytest.raises(ValueError, match="timeline"):
        key_interval(timing, tick)
