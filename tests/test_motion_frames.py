import math
import random
import struct

import pytest

from choops_py.formats.motion_frames import (
    channel_offset,
    decode_frame,
    decode_quaternion,
    layout,
    transcode_frames,
)

CH = "college-hoops-2k8"
NBA = "nba-2k11"


@pytest.mark.parametrize("selector", range(4))
def test_native_axis_quaternion_permutation_conventions(selector):
    # Zero stored components isolate the omitted unit component. Native CH uses
    # LVSL selector*4; NBA11 uses 12-selector*4 before VPERM.
    words = ((selector >> 1) * 32768, (selector & 1) * 32768, 0)
    ch = decode_quaternion(words, CH)
    nba = decode_quaternion(words, NBA)
    assert ch[3 - selector] == 1 and sum(ch) == 1
    assert nba[selector] == 1 and sum(nba) == 1


def fixture_stream():
    rng = random.Random(914)
    stride, size = layout(5, 6, 3)
    raw = bytearray(rng.randbytes(size))
    for frame in range(3):
        for channel in range(5):
            at = channel_offset(frame, channel, stride)
            for component in range(3):
                value = rng.randint(-8000, 8000) & 0x7FFF
                value |= rng.randrange(2) << 15
                struct.pack_into(">H", raw, at + component * 8, value)
    return bytes(raw)


def test_transcode_preserves_every_nonselector_bit_and_pose_and_roundtrips():
    raw = fixture_stream()
    before = bytes(raw)
    converted = transcode_frames(raw, 5, 6, 3, NBA, CH)
    allowed = set()
    stride, _ = layout(5, 6, 3)
    for frame in range(3):
        a = decode_frame(raw, 5, 6, 3, frame, NBA)
        b = decode_frame(converted, 5, 6, 3, frame, CH)
        assert a == b
        assert all(math.isclose(sum(v * v for v in q), 1) for q in a["rotations"])
        for channel in range(5):
            at = channel_offset(frame, channel, stride)
            allowed.update((at, at + 8))
    for at, (old, new) in enumerate(zip(raw, converted, strict=True)):
        assert old ^ new == (0x80 if at in allowed else 0)
    assert transcode_frames(converted, 5, 6, 3, CH, NBA) == raw
    assert transcode_frames(raw, 5, 6, 3, NBA, NBA) == raw
    assert raw == before


def test_signed_translation_scale_and_partial_group_padding():
    raw = bytearray(24)
    struct.pack_into(">h", raw, 0, -128)
    struct.pack_into(">h", raw, 8, 256)
    struct.pack_into(">h", raw, 16, -32768)
    assert decode_frame(raw, 0, 1, 1, 0, CH)["translations"] == [(-1, 2, -256)]
    assert transcode_frames(raw, 0, 1, 1, CH, NBA) == raw


def test_unsupported_or_malformed_data_cannot_be_transcoded():
    raw = fixture_stream()
    for counts in [(64, 0, 1), (0, 0, 1), (1, 0, 65536), (True, 0, 1)]:
        with pytest.raises(ValueError):
            layout(*counts)
    with pytest.raises(ValueError, match="not established"):
        transcode_frames(raw, 5, 6, 3, "nba-2k14", CH)
    with pytest.raises(ValueError, match="extent"):
        transcode_frames(raw[:-1], 5, 6, 3, NBA, CH)
    with pytest.raises(ValueError, match="Frame index"):
        decode_frame(raw, 5, 6, 3, -1, CH)
    with pytest.raises(ValueError, match="omitted"):
        decode_quaternion((0x3FFF, 0x3FFF, 0x3FFF), CH)


def test_cli_writes_separate_stream_and_blocks_source_overwrite(tmp_path, monkeypatch):
    from choops_py import cli
    from choops_py.archive import manifests

    monkeypatch.setattr(manifests, "OUTPUT", tmp_path)
    source = tmp_path / "source.bin"
    target = tmp_path / "converted.bin"
    raw = fixture_stream()
    source.write_bytes(raw)
    args = ["transcode-motion-frames", str(source), NBA, CH, "5", "6", "3"]
    result = cli.execute(cli.parser().parse_args([*args, str(target)]))
    assert target.read_bytes() == transcode_frames(raw, 5, 6, 3, NBA, CH)
    assert source.read_bytes() == raw
    assert result["gameplay_ready"] is False
    with pytest.raises(ValueError):
        cli.execute(cli.parser().parse_args([*args, str(source)]))


def test_native_identity_is_w_first_in_both_profiles():
    # Both native frame decoders initialize an absent rotation to (1,0,0,0).
    assert decode_quaternion((0x8000, 0x8000, 0), CH) == (1, 0, 0, 0)
    assert decode_quaternion((0, 0, 0), NBA) == (1, 0, 0, 0)


def test_quaternion_encoder_preserves_rotation_with_bounded_quantization():
    from choops_py.formats.motion_frames import encode_quaternion

    rng = random.Random(113)
    for _ in range(200):
        q = [rng.gauss(0, 1) for _ in range(4)]
        norm = math.sqrt(sum(v * v for v in q))
        q = [v / norm for v in q]
        for profile in (CH, NBA):
            decoded = decode_quaternion(encode_quaternion(q, profile), profile)
            dot = abs(sum(x * y for x, y in zip(q, decoded, strict=True)))
            assert 2 * math.acos(min(1, dot)) < 0.0002
    with pytest.raises(ValueError):
        encode_quaternion((0, 0, 0, 0), CH)
    with pytest.raises(ValueError):
        encode_quaternion((math.nan, 0, 0, 1), CH)


def test_irregular_timing_resamples_pose_and_preserves_keyframes_exactly():
    from choops_py.formats.motion_frames import (
        encode_quaternion,
        nba11_key_ticks,
        resample_nba11_frames,
    )

    raw = bytearray(48)
    angle = math.pi / 4
    for frame, q in enumerate([(1, 0, 0, 0), (math.cos(angle), 0, 0, math.sin(angle))]):
        words = encode_quaternion(q, NBA)
        for component, word in enumerate(words):
            struct.pack_into(">H", raw, frame * 24 + component * 8, word)
        struct.pack_into(">h", raw, frame * 24 + 2, frame * 512)
    before = bytes(raw)
    assert nba11_key_ticks(bytes([3, 0])) == [0, 4]
    output, report = resample_nba11_frames(raw, bytes([3, 0]), 1, 1)
    assert report["output_frames"] == 5 and report["gameplay_ready"] is False
    mid = decode_frame(output, 1, 1, 5, 2, CH)
    assert mid["translations"] == [(2, 0, 0)]
    assert mid["rotations"][0] == pytest.approx(
        (math.cos(math.pi / 8), 0, 0, math.sin(math.pi / 8)), abs=0.0001
    )
    converted = transcode_frames(raw, 1, 1, 2, NBA, CH)
    assert output[:24] == converted[:24]
    assert output[-24:] == converted[-24:]
    assert bytes(raw) == before
    assert nba11_key_ticks(bytes([0, 1, 99])) == [0, 1, 3]
    with pytest.raises(ValueError):
        resample_nba11_frames(raw[:-1], bytes([3, 0]), 1, 1)
    with pytest.raises(ValueError):
        nba11_key_ticks(b"")


def test_resample_cli_guards_both_source_files(tmp_path, monkeypatch):
    from choops_py import cli
    from choops_py.archive import manifests
    from choops_py.formats.motion_frames import nba11_key_ticks

    monkeypatch.setattr(manifests, "OUTPUT", tmp_path)
    source = tmp_path / "pose.bin"
    timing = tmp_path / "timing.bin"
    target = tmp_path / "fixed.bin"
    source.write_bytes(bytes(48))
    timing.write_bytes(bytes([1, 0]))
    args = ["resample-motion-frames", str(source), str(timing), "1", "0"]
    result = cli.execute(cli.parser().parse_args([*args, str(target)]))
    assert len(target.read_bytes()) == 72 and result["output_frames"] == 3
    for destination in (source, timing):
        with pytest.raises(ValueError):
            cli.execute(cli.parser().parse_args([*args, str(destination)]))
    assert source.read_bytes() == bytes(48) and timing.read_bytes() == bytes([1, 0])
    with pytest.raises(ValueError):
        nba11_key_ticks([-1, 0])


@pytest.mark.parametrize("heading", [False, True])
def test_root_irregular_resampling_preserves_keys_and_native_signed_values(heading):
    from choops_py.formats.motion_frames import resample_nba11_root

    components = 4 if heading else 3
    first = [-128, 256, -30000, 8190][:components]
    last = [128, -256, 30000, 8200][:components]
    raw = struct.pack(">" + "h" * components * 2, *(first + last))
    output = resample_nba11_root(raw, bytes([3, 0]), has_heading=heading)
    stride = components * 2
    assert len(output) == 5 * stride
    assert output[:stride] == raw[:stride] and output[-stride:] == raw[-stride:]
    assert struct.unpack_from(">" + "h" * components, output, 2 * stride) == tuple(
        round((a + b) / 2) for a, b in zip(first, last, strict=True)
    )
    with pytest.raises(ValueError):
        resample_nba11_root(raw[:-1], bytes([3, 0]), has_heading=heading)


def test_resample_cli_root_output_validation_precedes_any_write(tmp_path, monkeypatch):
    from choops_py import cli
    from choops_py.archive import manifests

    monkeypatch.setattr(manifests, "OUTPUT", tmp_path)
    source = tmp_path / "pose.bin"
    timing = tmp_path / "timing.bin"
    root = tmp_path / "root.bin"
    target = tmp_path / "fixed.bin"
    root_output = tmp_path / "fixed-root.bin"
    source.write_bytes(bytes(48))
    timing.write_bytes(bytes([1, 0]))
    root.write_bytes(bytes(16))
    args = [
        "resample-motion-frames",
        str(source),
        str(timing),
        "1",
        "0",
        str(target),
        "--root-track",
        str(root),
    ]
    with pytest.raises(ValueError):
        cli.execute(cli.parser().parse_args([*args, "--root-output", str(source)]))
    assert not target.exists() and source.read_bytes() == bytes(48)
    result = cli.execute(
        cli.parser().parse_args([*args, "--root-output", str(root_output)])
    )
    assert result["root_converted"] is True
    assert len(root_output.read_bytes()) == 24 and root.read_bytes() == bytes(16)
