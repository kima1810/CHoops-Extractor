"""CH native header/dependency and resident-image preparation.

Mirrors traced pointer fixups, not a native loader/hook or NBA header translator.
All authoring metadata comes from an existing validated CH header and is retained.
"""

import math
import struct
from collections import Counter

from ..formats.embedded_motion import NativeELF
from ..formats.motion_bind import canonical_channels
from ..formats.motion_events import inspect_events
from ..formats.motion_frames import layout

MAX_IMAGE = 16 * 1024 * 1024
POINTER_FIELDS = (0x30, 0x34, 0x38, 0x3C)


def inspect_target_motion(raw, address):
    """Inspect full file-backed track extents, retaining unresolved metadata bits."""
    elf = raw if isinstance(raw, NativeELF) else NativeELF(raw)
    if type(address) is not int or address < 0 or address % 4:
        raise ValueError("Target header must be word aligned")
    header = elf.read(address, 64)
    channels = canonical_channels(header, "college-hoops-2k8")
    flags, mode, state = struct.unpack_from(">3I", header, 16)
    frames, rate, count = mode & 0xFFFF, flags >> 24, flags & 63
    scale, duration, speed, x, z = struct.unpack_from(">5f", header, 28)
    if (
        not frames
        or not rate
        or not all(math.isfinite(f) for f in (scale, duration, speed, x, z))
    ):
        raise ValueError("Invalid target count/rate or nonfinite scalar metadata")
    if scale <= 0 or duration < 0 or speed < 0:
        raise ValueError("Invalid target timing or authored speed")
    # No donor root-endpoint approximation is used to fill these fields.
    metadata = dict(
        rate=rate,
        frames=frames,
        time_scale=scale,
        duration=duration,
        authored_planar_speed=speed,
        authored_planar_components=[x, z],
        raw_flags_0x10=flags,
        raw_flags_0x14=mode,
        raw_state_0x18=state,
        auxiliary_pointer_count=count,
        complete_flag_semantics=False,
        donor_derivation_established=False,
    )
    header = elf.read(address, 64 + count * 4)
    pose, root, events, extra = struct.unpack_from(">4I", header, 48)
    if not pose or not root or not events:
        raise ValueError("Resolved target pose/root/event dependencies are required")
    _, pose_size = layout(channels["rotations"], channels["translations"], frames)
    root_size = frames * (6 if mode & 0x80000000 else 8)
    event_report = inspect_events(elf.raw, "college-hoops-2k8", events, native=True)
    spans = [
        ("header", address, len(header)),
        ("poses", pose, pose_size),
        ("root", root, root_size),
        ("events", events, len(event_report["entries"]) * 8 + 4),
    ]
    dependencies = []
    for role, start, size in spans:
        if start % (4 if role in ("header", "events") else 2):
            raise ValueError("Unaligned target dependency")
        elf.file_span(start, size)
        owner = next(
            s
            for s in elf.segments
            if s["address"] <= start < s["address"] + s["file_bytes"]
        )
        dependencies.append(
            dict(
                role=role,
                address=start,
                bytes=size,
                segment_address=owner["address"],
                segment_flags=owner["flags"],
            )
        )
    unknown = []
    for field in (0x3C, *(0x40 + i * 4 for i in range(count))):
        pointer = struct.unpack_from(">I", header, field)[0]
        if pointer:
            elf.file_span(pointer, 1)
            unknown.append(dict(field=field, address=pointer, extent_established=False))
    return dict(
        header_address=address,
        channels=channels,
        metadata=metadata,
        dependencies=dependencies,
        unbounded_dependencies=unknown,
        resident_image_supported=not unknown and count == 0,
        gameplay_ready=False,
        native_registration_installed=False,
    )


def prepare_target_image(raw, addresses, *, budget=MAX_IMAGE):
    """Materialize existing CH headers/tracks in one bounded owned relative image.

    Preserves every nonpointer header byte. Auxiliary/unknown extents are refused.
    No executable bytes, allocator calls, bank registration or donor metadata are
    synthesized. The caller must keep the whole image resident while referenced.
    """
    if type(budget) is not int or not 64 <= budget <= MAX_IMAGE:
        raise ValueError("Resident image budget must be 64 bytes..16 MiB")
    if not 1 <= len(addresses) <= 4096 or len(set(addresses)) != len(addresses):
        raise ValueError("Choose 1..4096 distinct target headers")
    elf = NativeELF(raw)
    reports = [inspect_target_motion(elf, address) for address in addresses]
    if any(not r["resident_image_supported"] for r in reports):
        raise ValueError(
            "Auxiliary or unknown dependency extents prevent resident image preparation"
        )
    header_ranges = [
        (r["header_address"], r["header_address"] + r["dependencies"][0]["bytes"])
        for r in reports
    ]
    for report in reports:
        for dependency in report["dependencies"]:
            if dependency["role"] == "header":
                continue
            start = dependency["address"]
            end = start + dependency["bytes"]
            if any(start < z and a < end for a, z in header_ranges):
                raise ValueError("Source motion track overlaps header storage")
    output = bytearray()
    locations = {}
    extents = []
    for report in reports:
        for dep in report["dependencies"]:
            key = dep["address"], dep["bytes"]
            if key in locations:
                continue
            offset = (len(output) + 15) & ~15
            if offset + dep["bytes"] > budget:
                raise ValueError("Resident motion image exceeds byte budget")
            output.extend(bytes(offset - len(output)))
            locations[key] = offset
            output.extend(elf.read(*key))
            extents.append(dict(offset=offset, bytes=dep["bytes"], role=dep["role"]))
    offsets = []
    for report in reports:
        deps = {d["role"]: d for d in report["dependencies"]}
        h = deps["header"]
        offset = locations[h["address"], h["bytes"]]
        offsets.append(offset)
        for field, role in ((0x30, "poses"), (0x34, "root"), (0x38, "events")):
            dep = deps[role]
            target = locations[dep["address"], dep["bytes"]]
            struct.pack_into(
                ">i", output, offset + field, target - (offset + field) + 1
            )
    return bytes(output), dict(
        schema=1,
        pointer_state="relative",
        header_offsets=offsets,
        bytes=len(output),
        budget=budget,
        extents=extents,
        source_header_metadata_preserved=True,
        external_pointers=False,
        ownership="whole-image-must-remain-resident-while-any-consumer-references-it",
        role_counts=dict(Counter(d["role"] for d in extents)),
        native_registration_installed=False,
        gameplay_ready=False,
    )


def relocate_target_image(raw, header_offsets, base, *, source_state):
    """Offline oracle for CH 0x1E9C0/0x1EAA0 pointer fixup/unfixup.

    State is explicit. Validation is complete before writing; targets cannot
    escape the owned image, wrap 32-bit pointers, or point into header storage.
    This models relocation only, not native allocation/registration or residency.
    """
    if (
        not 64 <= len(raw) <= MAX_IMAGE
        or type(base) is not int
        or base < 0x10000
        or base % 16
        or base + len(raw) > 1 << 32
    ):
        raise ValueError("Invalid resident image base/range")
    if source_state not in ("relative", "native"):
        raise ValueError("Declare source pointer state as relative or native")
    if not 1 <= len(header_offsets) <= 4096 or len(set(header_offsets)) != len(
        header_offsets
    ):
        raise ValueError("Choose distinct bounded header offsets")
    ranges, fields = [], []
    for offset in header_offsets:
        if (
            type(offset) is not int
            or offset < 0
            or offset % 4
            or offset + 64 > len(raw)
        ):
            raise ValueError("Invalid image header offset")
        canonical_channels(raw[offset : offset + 64], "college-hoops-2k8")
        count = struct.unpack_from(">I", raw, offset + 16)[0] & 63
        end = offset + 64 + count * 4
        if end > len(raw) or any(offset < z and a < end for a, z in ranges):
            raise ValueError("Overlapping or truncated resident headers")
        ranges.append((offset, end))
        fields.extend(
            offset + f for f in (*POINTER_FIELDS, *(0x40 + i * 4 for i in range(count)))
        )
    updates = []
    for field in fields:
        value = struct.unpack_from(">I", raw, field)[0]
        if not value:
            continue
        if source_state == "relative":
            delta = value if value < 1 << 31 else value - (1 << 32)
            target = field + delta - 1
            encoded = base + target
        else:
            target = value - base
            encoded = (target - field + 1) & 0xFFFFFFFF
        if not 0 <= target < len(raw) or any(a <= target < z for a, z in ranges):
            raise ValueError(
                "Motion pointer escapes image or overlaps header storage; wrong pointer state?"
            )
        updates.append((field, encoded))
    result = bytearray(raw)
    for field, value in updates:
        struct.pack_into(">I", result, field, value)
    # Validate complete mandatory track extents in the resulting native view,
    # not just the first pointed-to byte. This is an analysis-only ELF wrapper.
    native = result if source_state == "relative" else raw
    wrapper = bytearray(256 + len(native))
    wrapper[:7] = b"\x7fELF\x02\x02\x01"
    struct.pack_into(">HH", wrapper, 16, 2, 21)
    struct.pack_into(">Q", wrapper, 32, 64)
    struct.pack_into(">HH", wrapper, 54, 56, 1)
    struct.pack_into(
        ">II6Q", wrapper, 64, 1, 6, 256, base, base, len(native), len(native), 16
    )
    wrapper[256:] = native
    elf = NativeELF(wrapper)
    for offset in header_offsets:
        report = inspect_target_motion(elf, base + offset)
        for dependency in report["dependencies"]:
            if dependency["role"] == "header":
                continue
            start = dependency["address"] - base
            end = start + dependency["bytes"]
            if any(start < z and a < end for a, z in ranges):
                raise ValueError("Motion track extent overlaps header storage")
    return bytes(result)
