"""Translate observed packed pose channels, not skeletons or gameplay banks.

The profiles differ in the two-bit quaternion permutation selector. Frame data
is four-channel XYZ SoA groups; 15-bit quaternion values and 16-bit translations
are preserved exactly. Runtime bone maps, mirrors and events are separate.
"""

from __future__ import annotations

import math
import struct

PROFILES = ("college-hoops-2k8", "nba-2k11")
QUAT_SCALE = 23 / (32 * 16384)
MAX_STREAM = 64 * 1024 * 1024


def layout(rotations, translations, frames):
    if any(type(x) is not int for x in (rotations, translations, frames)):
        raise ValueError("Motion counts must be integers")
    if not 0 <= rotations <= 63 or not 0 <= translations <= 63:
        raise ValueError("Native channel counts exceed six-bit fields")
    if rotations + translations == 0 or not 1 <= frames <= 65535:
        raise ValueError("Motion stream needs channels and bounded frames")
    stride = ((rotations + translations + 3) // 4) * 24
    size = stride * frames
    if size > MAX_STREAM:
        raise ValueError("Motion stream exceeds inspection bounds")
    return stride, size


def _profile(profile):
    if profile not in PROFILES:
        raise ValueError("Packed motion frame profile is not established")


def channel_offset(frame, channel, stride):
    return frame * stride + (channel // 4) * 24 + (channel % 4) * 2


def decode_quaternion(words, profile):
    """Return WXYZ in native channel order, before mirror/bone-map transforms.

    Native sqrt uses reciprocal-square-root estimates and one refinement. This
    offline decoder uses mathematical sqrt; it does not claim bit-exact SIMD FP.
    """
    _profile(profile)
    if len(words) != 3 or any(type(w) is not int or not 0 <= w <= 65535 for w in words):
        raise ValueError("Quaternion channel needs three unsigned 16-bit words")
    selector = ((words[0] >> 15) << 1) | (words[1] >> 15)
    values = [w & 0x7FFF for w in words]
    values = [(v if v < 0x4000 else v - 0x8000) * QUAT_SCALE for v in values]
    remainder = 1 - sum(v * v for v in values)
    if remainder <= 0:
        raise ValueError("Packed quaternion has no positive omitted component")
    values.append(math.sqrt(remainder))
    shift = selector if profile == "college-hoops-2k8" else 3 - selector
    return tuple(values[shift:] + values[:shift])


def decode_frame(raw, rotations, translations, frames, frame, profile):
    _profile(profile)
    stride, size = layout(rotations, translations, frames)
    if len(raw) != size:
        raise ValueError("Packed frame extent does not match supplied counts")
    if type(frame) is not int or not 0 <= frame < frames:
        raise ValueError("Frame index is outside motion extent")
    quaternions, positions = [], []
    for channel in range(rotations + translations):
        at = channel_offset(frame, channel, stride)
        words = tuple(struct.unpack_from(">H", raw, at + i * 8)[0] for i in range(3))
        if channel < rotations:
            quaternions.append(decode_quaternion(words, profile))
        else:
            positions.append(
                tuple((v if v < 32768 else v - 65536) / 128 for v in words)
            )
    return dict(rotations=quaternions, translations=positions)


def transcode_frames(
    raw, rotations, translations, frames, source_profile, target_profile
):
    """Lossless native selector conversion; preserve padding and all other bits.

    Counts must come from a confirmed packed stream. This is not an IFF/EBOOT
    writer or a retargeter; never install its result as an entire donor bank.
    """
    _profile(source_profile)
    _profile(target_profile)
    stride, size = layout(rotations, translations, frames)
    if len(raw) != size:
        raise ValueError("Packed frame extent does not match supplied counts")
    output = bytearray(raw)
    for frame in range(frames):
        for channel in range(rotations):
            at = channel_offset(frame, channel, stride)
            words = tuple(
                struct.unpack_from(">H", raw, at + i * 8)[0] for i in range(3)
            )
            decode_quaternion(words, source_profile)
            if source_profile != target_profile:
                output[at] ^= 0x80
                output[at + 8] ^= 0x80
    return bytes(output)


def encode_quaternion(quaternion, profile):
    """Quantize a native WXYZ quaternion into the established three-word layout."""
    _profile(profile)
    if len(quaternion) != 4 or any(not math.isfinite(v) for v in quaternion):
        raise ValueError("Quaternion needs four finite components")
    norm = math.sqrt(sum(v * v for v in quaternion))
    if norm <= 0:
        raise ValueError("Cannot encode a zero quaternion")
    q = [v / norm for v in quaternion]
    omitted = max(range(4), key=lambda i: abs(q[i]))
    if q[omitted] < 0:
        q = [-v for v in q]
    shift = (3 - omitted) % 4
    # Decoder rotates [a,b,c,missing] left by shift.
    values = q[-shift:] + q[:-shift] if shift else q
    packed = [round(v / QUAT_SCALE) for v in values[:3]]
    if any(not -16384 <= v <= 16383 for v in packed):
        raise ValueError("Quaternion exceeds native quantization range")
    selector = shift if profile == "college-hoops-2k8" else 3 - shift
    words = [v & 0x7FFF for v in packed]
    words[0] |= (selector >> 1) << 15
    words[1] |= (selector & 1) << 15
    return tuple(words)


def nba11_key_ticks(deltas):
    """Native byte deltas encode interval minus one; last byte is unused here."""
    if not isinstance(deltas, (bytes, bytearray)):
        raise ValueError("NBA11 timing table must contain bytes")
    if not 1 <= len(deltas) <= 32767:
        raise ValueError("NBA11 timing table exceeds native keyframe count")
    ticks = [0]
    for delta in deltas[:-1]:
        ticks.append(ticks[-1] + delta + 1)
    return ticks


def _slerp(a, b, fraction):
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    if dot < 0:
        b = tuple(-v for v in b)
        dot = -dot
    dot = min(1, dot)
    if dot > 0.9995:
        q = [(1 - fraction) * x + fraction * y for x, y in zip(a, b, strict=True)]
        norm = math.sqrt(sum(v * v for v in q))
        return tuple(v / norm for v in q)
    angle = math.acos(dot)
    factor_a = math.sin((1 - fraction) * angle) / math.sin(angle)
    factor_b = math.sin(fraction * angle) / math.sin(angle)
    return tuple(factor_a * x + factor_b * y for x, y in zip(a, b, strict=True))


def resample_nba11_frames(raw, deltas, rotations, translations):
    """Expand native irregular key ticks to fixed CH frames at the same tick rate.

    Keep the source rate and time-scale when constructing future container headers.
    This produces pose channels only. Mathematical SLERP approximates the native
    VMX polynomial evaluation; root/events/auxiliary tracks are NOT converted.
    """
    frames = len(deltas)
    stride, size = layout(rotations, translations, frames)
    if len(raw) != size:
        raise ValueError("Packed frame extent does not match timing table")
    ticks = nba11_key_ticks(deltas)
    output_frames = ticks[-1] + 1
    _, output_size = layout(rotations, translations, output_frames)
    output = bytearray(output_size)
    converted = transcode_frames(
        raw, rotations, translations, frames, "nba-2k11", "college-hoops-2k8"
    )
    left = 0
    endpoints = {}
    for tick in range(output_frames):
        while left + 1 < frames and ticks[left + 1] <= tick:
            left += 1
        if tick == ticks[left]:
            output[tick * stride : (tick + 1) * stride] = converted[
                left * stride : (left + 1) * stride
            ]
            continue
        right = left + 1
        endpoints = {
            i: endpoints.get(i)
            or decode_frame(raw, rotations, translations, frames, i, "nba-2k11")
            for i in (left, right)
        }
        fraction = (tick - ticks[left]) / (ticks[right] - ticks[left])
        for channel in range(rotations + translations):
            at = channel_offset(tick, channel, stride)
            if channel < rotations:
                a = endpoints[left]["rotations"][channel]
                b = endpoints[right]["rotations"][channel]
                words = encode_quaternion(_slerp(a, b, fraction), "college-hoops-2k8")
            else:
                i = channel - rotations
                a = endpoints[left]["translations"][i]
                b = endpoints[right]["translations"][i]
                words = tuple(
                    round(((1 - fraction) * x + fraction * y) * 128) & 65535
                    for x, y in zip(a, b, strict=True)
                )
            for component, word in enumerate(words):
                struct.pack_into(">H", output, at + component * 8, word)
    return bytes(output), dict(
        source_frames=frames,
        output_frames=output_frames,
        last_tick=ticks[-1],
        tick_rate_changed=False,
        interpolation="mathematical-slerp-linear-translation",
        root_converted=False,
        gameplay_ready=False,
    )


def resample_nba11_root(raw, deltas, *, has_heading=True):
    """Resample the established signed-halfword root track on the same key ticks.

    Native XYZ scale is 1/8. The optional fourth word feeds native angle conversion;
    interpolate authored signed words directly, as the sampler does. Mirror flags
    and runtime angle conversion remain in the future container/runtime adapter.
    """
    if type(has_heading) is not bool:
        raise ValueError("Root heading mode must be explicit")
    ticks = nba11_key_ticks(deltas)
    components = 4 if has_heading else 3
    stride = components * 2
    if len(raw) != len(ticks) * stride:
        raise ValueError("Root extent does not match timing table and heading mode")
    frames = ticks[-1] + 1
    if frames > 65535:
        raise ValueError("Fixed root frames exceed destination frame-count field")
    output = bytearray(frames * stride)
    left = 0
    for tick in range(frames):
        while left + 1 < len(ticks) and ticks[left + 1] <= tick:
            left += 1
        if ticks[left] == tick:
            output[tick * stride : (tick + 1) * stride] = raw[
                left * stride : (left + 1) * stride
            ]
            continue
        a = struct.unpack_from(">" + "h" * components, raw, left * stride)
        b = struct.unpack_from(">" + "h" * components, raw, (left + 1) * stride)
        fraction = (tick - ticks[left]) / (ticks[left + 1] - ticks[left])
        values = [
            round((1 - fraction) * x + fraction * y) for x, y in zip(a, b, strict=True)
        ]
        struct.pack_into(">" + "h" * components, output, tick * stride, *values)
    return bytes(output)
