"""Bounded, read-only indexing of observed executable-held full-body motion rows.

This locates a confirmed mask family, not every animation or a playable library.
Absolute pointer targets are reported; no executable or clip is modified/exported.
"""

from __future__ import annotations

import hashlib
import math
import struct

from .motion_envelope import PROFILES

MAX_ELF = 256 * 1024 * 1024
FULL_BODY_MASK = bytes.fromhex("001df7dd")


class NativeELF:
    def __init__(self, raw):
        if len(raw) > MAX_ELF or len(raw) < 64:
            raise ValueError("Native analysis ELF exceeds bounds or is truncated")
        if raw[:7] != b"\x7fELF\x02\x02\x01":
            raise ValueError("Provide a decoded ELF64 big-endian analysis copy")
        if struct.unpack_from(">HH", raw, 16) != (2, 21):
            raise ValueError("Expected a PowerPC64 executable analysis copy")
        phoff = struct.unpack_from(">Q", raw, 32)[0]
        stride, count = struct.unpack_from(">HH", raw, 54)
        if stride != 56 or not 1 <= count <= 64 or phoff + stride * count > len(raw):
            raise ValueError("Invalid native ELF program-header table")
        self.raw = raw
        self.segments = []
        for i in range(count):
            typ, flags, pos, va, _, size, memory, _ = struct.unpack_from(
                ">II6Q", raw, phoff + i * stride
            )
            if typ != 1 or not memory:
                continue
            if size > memory or pos + size > len(raw) or va + memory > 1 << 32:
                raise ValueError("Invalid native ELF load range")
            if any(
                va < s["address"] + s["memory_bytes"] and s["address"] < va + memory
                for s in self.segments
            ):
                raise ValueError("Ambiguous native ELF load ranges")
            self.segments.append(
                dict(
                    address=va,
                    offset=pos,
                    file_bytes=size,
                    memory_bytes=memory,
                    flags=flags,
                )
            )
        if not self.segments:
            raise ValueError("Native ELF has no loadable analysis memory")

    def target(self, address):
        for s in self.segments:
            delta = address - s["address"]
            if 0 <= delta < s["memory_bytes"]:
                backed = delta < s["file_bytes"]
                return dict(
                    address=address,
                    file_backed=backed,
                    file_offset=s["offset"] + delta if backed else None,
                )
        raise ValueError("Motion dependency is outside native load memory")

    def file_span(self, address, size):
        """Validate a file-backed extent without allocating its payload."""
        if type(address) is not int or type(size) is not int or size < 0:
            raise ValueError("Invalid native dependency extent")
        for segment in self.segments:
            delta = address - segment['address']
            if 0 <= delta <= segment['file_bytes'] and delta + size <= segment['file_bytes']:
                start = segment['offset'] + delta
                return start, start + size
        raise ValueError("Native dependency extent is not fully file-backed")

    def read(self, address, size):
        """Read an entire file-backed range; never synthesize native BSS bytes."""
        start, end = self.file_span(address, size)
        return self.raw[start:end]


def inspect_embedded(raw, profile):
    if profile not in PROFILES:
        raise ValueError("Embedded motion profile is not established for this game")
    elf = NativeELF(raw)
    layout = PROFILES[profile]
    mask_field = 4 if profile == "college-hoops-2k8" else 8
    rows, rejected = [], []
    hits = 0
    for segment in elf.segments:
        if not segment["flags"] & 2 or not segment["file_bytes"]:
            continue
        first = segment["offset"]
        stop = first + segment["file_bytes"]
        search = first
        while True:
            hit = raw.find(FULL_BODY_MASK, search, stop)
            if hit < 0:
                break
            search = hit + 4
            at = hit - mask_field
            if (segment["address"] + hit - first) % 4:
                continue
            hits += 1
            try:
                if at < first or at + layout["minimum"] > stop:
                    raise ValueError("Embedded header crosses its file-backed segment")

                def word(offset):
                    return struct.unpack_from(">I", raw, at + offset)[0]

                count = word(0x10) & 0x3F
                if at + layout["tail"] + count * 4 > stop:
                    raise ValueError("Embedded pointer tail crosses its segment")
                scalar = struct.unpack_from(">f", raw, at + 0x20)[0]
                if not math.isfinite(scalar) or not 0 <= scalar <= 86400:
                    raise ValueError(
                        "Observed header scalar is outside inspection bounds"
                    )
                resolved = word(layout["resolved"])
                if not resolved:
                    raise ValueError(
                        "Unresolved embedded reference needs its native bank resolver"
                    )
                fields = (
                    *layout["fixups"],
                    *(layout["tail"] + i * 4 for i in range(count)),
                )
                pointers = []
                for field in fields:
                    address = word(field)
                    if address:
                        pointers.append(dict(field=field, **elf.target(address)))
                if len(pointers) < 3:
                    raise ValueError(
                        "Too few mapped dependencies for the observed envelope"
                    )
                rows.append(
                    dict(
                        address=segment["address"] + at - first,
                        file_offset=at,
                        raw_identifier=word(0),
                        raw_flags=word(0x10),
                        raw_scalar_0x20=scalar,
                        auxiliary_pointer_count=count,
                        pointers=pointers,
                    )
                )
            except ValueError as error:
                rejected.append(dict(file_offset=at, reason=str(error)))
    return dict(
        profile=profile,
        source_sha256=hashlib.sha256(raw).hexdigest(),
        mode="read-only",
        mask_family="0x001DF7DD",
        mask_hits=hits,
        candidates=rows,
        rejected=rejected,
        segments=elf.segments,
        complete_library=False,
        pose_decoded=False,
        import_supported=False,
        note=(
            "Observed full-body mask family only. A mapped header is not a "
            "decoded pose, a portable clip, or every animation in the game."
        ),
    )
