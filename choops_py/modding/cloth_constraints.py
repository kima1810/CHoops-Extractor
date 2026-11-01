"""Bounded adaptation of the observed CH2K8 SPU cloth distance batches.

Eight packed edges and sixteen untouched response bytes occupy each 48-byte
batch. Preserve authored slack/prestrain, not an assumed geometric rest length.
Collision and render-binding streams are outside this writer's scope.
"""

import math
import struct

from ..formats.binary import Binary


def retarget_distances(original, edited):
    """Scale stored edge lengths by the change in their particle separation.

The native solver addresses particles with aligned vector loads: bits 20..31
select A, bits 0..9 add the index delta to obtain B, and bits 10..19 store
length in 1/32 units. Self edges are authored padding and remain untouched.
Both stretch and bend batches use this packing; their authored length ratios
can differ, so recomputing all lengths as geometric distance is incorrect.
"""
    if len(original) != len(edited):
        raise ValueError("Cloth extent changed")
    h = Binary(original)
    size, start = h.u16(0), h.u32(0xC0)
    if not size or size % 16 or h.u32(0xC8) != start + size:
        raise ValueError("Unsupported cloth particles for distance adaptation")
    h.slice(start, size)
    particles = size // 16
    ranges = []
    for pointer, count in ((0xD4, 4), (0xD8, 6)):
        batches, table = h.u16(count) >> 3, h.u32(pointer)
        if not batches and not table:
            continue
        if not batches or table < start + size or table % 16:
            raise ValueError("Unsupported cloth distance table")
        h.slice(table, batches * 48)
        if any(table < end and begin < table + batches * 48 for begin, end in ranges):
            raise ValueError("Overlapping cloth distance tables")
        ranges.append((table, table + batches * 48))
    result = bytearray(edited)
    changed = 0
    for begin, end in ranges:
        for batch in range(begin, end, 48):
            for offset in range(batch, batch + 32, 4):
                word = h.u32(offset)
                a, b = word >> 20, (word >> 20) + (word & 1023)
                if b >= particles:
                    raise ValueError("Cloth constraint particle outside table")
                if a == b:
                    continue
                aa, bb = start + a * 16, start + b * 16
                before = math.dist(
                    struct.unpack_from(">3f", original, aa),
                    struct.unpack_from(">3f", original, bb),
                )
                after = math.dist(
                    struct.unpack_from(">3f", edited, aa),
                    struct.unpack_from(">3f", edited, bb),
                )
                if not math.isfinite(before + after) or before <= 0 or after <= 0:
                    raise ValueError("Invalid cloth constraint separation")
                stored = (word >> 10) & 1023
                length = math.floor(stored * after / before + 0.5)
                if not 1 <= length <= 1023:
                    raise ValueError("Edited cloth distance exceeds native packing")
                if length != stored:
                    struct.pack_into(
                        ">I", result, offset,
                        (word & ~(1023 << 10)) | (length << 10),
                    )
                    changed += 1
    return bytes(result), changed
