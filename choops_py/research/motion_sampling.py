"""Bounded offline reference for sampling NBA11 keys without expanding a bank.

This is not a PS3 runtime hook. Poses are before mirror/world/auxiliary transforms;
event dispatch and authoring metadata must be adapted separately.
"""

from __future__ import annotations

import math
import mmap
import struct
from collections import OrderedDict
from contextlib import ExitStack
from pathlib import Path

from ..formats.embedded_motion import NativeELF
from ..formats.motion_bind import canonical_channels, verify_canonical_bind
from ..formats.motion_frames import (
    _slerp,
    channel_offset,
    decode_frame,
    encode_quaternion,
    layout,
    transcode_frames,
)


def key_interval(timing, tick):
    """Native interval-minus-one bytes; terminal byte is not a duration.

    No expanded frame list or per-key Python index is allocated. Endpoint clamp
    is explicit; this function does not decide the engine's clip loop policy.
    """
    if (
        not isinstance(timing, (bytes, bytearray))
        or not 1 <= len(timing) <= 32767
        or not isinstance(tick, (int, float))
        or not math.isfinite(tick)
    ):
        raise ValueError("Invalid bounded motion timeline")
    if tick <= 0 or len(timing) == 1:
        return 0, 0, 0.0
    left_tick = 0
    for right in range(1, len(timing)):
        right_tick = left_tick + timing[right - 1] + 1
        if tick < right_tick:
            return right - 1, right, (tick - left_tick) / (right_tick - left_tick)
        if tick == right_tick:
            return right, right, 0.0
        left_tick = right_tick
    return len(timing) - 1, len(timing) - 1, 0.0


def interpolate_frame(left, right, rotations, translations, fraction):
    """Preserve exact authored endpoints; use the existing reference interpolation."""
    stride, _ = layout(rotations, translations, 1)
    if len(left) != stride or len(right) != stride or not 0 <= fraction <= 1:
        raise ValueError("Invalid packed frame pair/fraction")
    if fraction in (0, 1):
        return transcode_frames(
            left if fraction == 0 else right,
            rotations,
            translations,
            1,
            "nba-2k11",
            "college-hoops-2k8",
        )
    a = decode_frame(left, rotations, translations, 1, 0, "nba-2k11")
    b = decode_frame(right, rotations, translations, 1, 0, "nba-2k11")
    output = bytearray(stride)
    for channel in range(rotations + translations):
        at = channel_offset(0, channel, stride)
        if channel < rotations:
            words = encode_quaternion(
                _slerp(a["rotations"][channel], b["rotations"][channel], fraction),
                "college-hoops-2k8",
            )
        else:
            index = channel - rotations
            words = tuple(
                round(((1 - fraction) * x + fraction * y) * 128) & 65535
                for x, y in zip(
                    a["translations"][index], b["translations"][index], strict=True
                )
            )
        for component, word in enumerate(words):
            struct.pack_into(">H", output, at + component * 8, word)
    return bytes(output)


class MotionSampler:
    """Read-only mapped ELF inputs and a byte-budgeted LRU of bounded reads.

    The budget covers retained payload bytes, not total Python/OS RSS or PS3 RAM.
    Sampling holds at most two decoded key poses, irrespective of clip duration.
    A sampler belongs to one worker; sharing mutable cache state is unsupported.
    """

    def __init__(self, donor, target, *, cache_bytes=256 * 1024):
        if type(cache_bytes) is not int or not 65536 <= cache_bytes <= 64 * 1024 * 1024:
            raise ValueError("Choose a payload cache from 64 KiB to 64 MiB")
        self._stack = ExitStack()
        self._cache = OrderedDict()
        self._bytes = self._peak = self._reads = self._hits = self._evictions = 0
        self._limit = cache_bytes
        self._closed = False
        self._files = []
        try:
            views = []
            for path in (donor, target):
                path = Path(path)
                size = path.stat().st_size
                if not 64 <= size <= 256 * 1024 * 1024:
                    raise ValueError("Native analysis ELF exceeds sampling bounds")
                file = self._stack.enter_context(path.open("rb"))
                self._files.append((file, self._identity(file)))
                views.append(
                    self._stack.enter_context(
                        mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
                    )
                )
            self.bind = verify_canonical_bind(*views)
            self._elf = NativeELF(views[0])
        except BaseException:
            self.close()
            raise

    @staticmethod
    def _identity(file):
        import os

        stat = os.fstat(file.fileno())
        return stat.st_size, stat.st_mtime_ns, stat.st_ino

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self._cache.clear()
        self._bytes = 0
        self._closed = True
        self._stack.close()

    def _read(self, address, size):
        if self._closed:
            raise ValueError("Motion sampler is closed")
        for file, identity in self._files:
            if self._identity(file) != identity:
                self._cache.clear()
                self._bytes = 0
                raise ValueError("Analysis source changed; reopen the sampler")
        if type(size) is not int or not 0 <= size <= self._limit:
            raise ValueError("Single payload read exceeds sampler cache budget")
        key = address, size
        if key in self._cache:
            self._hits += 1
            self._cache.move_to_end(key)
            return self._cache[key]
        data = self._elf.read(address, size)
        self._reads += 1
        while self._bytes + size > self._limit:
            _, previous = self._cache.popitem(last=False)
            self._bytes -= len(previous)
            self._evictions += 1
        self._cache[key] = data
        self._bytes += len(data)
        self._peak = max(self._peak, self._bytes)
        return data

    def sample(self, address, seconds):
        """Return one CH-packed pose sample, before native mirror/auxiliary stages."""
        if type(address) is not int or address < 0 or address % 4:
            raise ValueError("Motion header must be word aligned")
        if (
            not isinstance(seconds, (int, float))
            or not math.isfinite(seconds)
            or seconds < 0
        ):
            raise ValueError("Sample time must be finite and nonnegative")
        header = self._read(address, 56)
        channels = canonical_channels(header, "nba-2k11")
        flags, mode = struct.unpack_from(">II", header, 0x10)
        self._elf.file_span(address, 56 + (flags & 63) * 4)
        if mode & 0x8000:
            raise ValueError("NBA11 unpacked pose sampling is not established")
        frames, rate = mode & 0x7FFF, flags >> 24
        scale, duration = struct.unpack_from(">ff", header, 0x1C)
        if (
            not frames
            or not rate
            or not math.isfinite(scale)
            or scale <= 0
            or not math.isfinite(duration)
            or duration < 0
        ):
            raise ValueError("Motion sampling time metadata is invalid")
        timing_ptr, pose_ptr, root_ptr, event_ptr, auxiliary_ptr = struct.unpack_from(
            ">5I", header, 0x24
        )
        if not timing_ptr or not pose_ptr or not event_ptr:
            raise ValueError(
                "Motion dependencies are null or this is an unresolved reference"
            )
        self._elf.file_span(event_ptr, 4)
        timing = self._read(timing_ptr, frames)
        last_tick = sum(value + 1 for value in timing[:-1])
        expected = duration * rate * scale
        if frames > 1 and not math.isclose(
            last_tick, expected, rel_tol=2e-6, abs_tol=0.002
        ):
            raise ValueError("Motion timing and duration metadata disagree")
        left, right, fraction = key_interval(timing, seconds * rate * scale)
        rotations, translations = channels["rotations"], channels["translations"]
        stride, size = layout(rotations, translations, frames)
        self._elf.file_span(pose_ptr, size)
        pose = interpolate_frame(
            self._read(pose_ptr + left * stride, stride),
            self._read(pose_ptr + right * stride, stride),
            rotations,
            translations,
            fraction,
        )
        root = None
        if root_ptr:
            components = 3 if mode & 0x80000000 else 4
            root_stride = components * 2
            self._elf.file_span(root_ptr, frames * root_stride)
            a = struct.unpack(
                ">" + "h" * components,
                self._read(root_ptr + left * root_stride, root_stride),
            )
            b = struct.unpack(
                ">" + "h" * components,
                self._read(root_ptr + right * root_stride, root_stride),
            )
            root = tuple(
                round((1 - fraction) * x + fraction * y)
                for x, y in zip(a, b, strict=True)
            )
        return pose, dict(
            left_key=left,
            right_key=right,
            fraction=fraction,
            channels=channels,
            root_signed_words=root,
            mirror_flag=bool(mode & 0x40000000),
            event_pointer=event_ptr,
            auxiliary_pointer=auxiliary_ptr,
            rate=rate,
            time_scale=scale,
            duration=duration,
            raw_flags_0x14=mode,
            raw_word_0x18=struct.unpack_from(">I", header, 0x18)[0],
            auxiliary_track_count=flags & 63,
            transforms_applied="packed-pose-before-mirror-world-auxiliary",
            events_dispatched=False,
            loop_policy_applied=False,
            gameplay_ready=False,
            runtime_hook_installed=False,
        )

    def stats(self):
        return dict(
            payload_budget=self._limit,
            retained_payload_bytes=self._bytes,
            peak_retained_payload_bytes=self._peak,
            reads=self._reads,
            hits=self._hits,
            evictions=self._evictions,
            max_decoded_key_poses=2,
            expanded_bank_allocated=False,
            total_process_memory_bounded=False,
            ps3_runtime_certified=False,
        )
