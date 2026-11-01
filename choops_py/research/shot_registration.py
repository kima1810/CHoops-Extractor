"""Read-only CH2K8 shot registration audit; no executable patch application."""

import struct

from ..formats.embedded_motion import NativeELF
from ..formats.motion_bind import canonical_channels

STOCK_TABLE = 0x9DD5F0
TABLE_SLOT = 0xA58608
LABEL_START_SLOT = 0xA662CC
LABEL_END_SLOT = 0xA661FC
CAP_INSTRUCTION = 0x69D410
READERS = (0x3213D4, 0x321454, 0x321538, 0x3247DC, 0x326404, 0x32BE20)
READ_REGISTERS = (11, 11, 9, 8, 10, 10)


def inspect_registration(raw, *, motion_extents=False):
    elf = NativeELF(raw)

    def word(address):
        return struct.unpack(">I", elf.read(address, 4))[0]

    instruction = word(CAP_INSTRUCTION)
    if instruction & 0xFFFF0000 != 0x38000000:
        raise ValueError("Unrecognized jump-shot range initializer")
    count = (instruction & 0xFFFF) + 1
    if not 112 <= count <= 256:
        raise ValueError(
            "Registered shot count exceeds the established byte-index range"
        )
    # All confirmed consumers must still load this same pointer slot through R2.
    for address, register in zip(READERS, READ_REGISTERS, strict=True):
        instruction = word(address)
        if instruction != (32 << 26 | register << 21 | 2 << 16 | 0x3B40):
            raise ValueError("A native shot-table consumer changed")
    if word(0x69E938) != 0x88630073 or word(0x69E94C) != 0x98830073:
        raise ValueError("Jump-shot getter/setter byte field changed")
    if word(0x694CF0) != 0x83A21768 or word(0x694D08) != 0x80021838:
        raise ValueError("Shot-name destructor range loads changed")
    table, start, end = word(TABLE_SLOT), word(LABEL_START_SLOT), word(LABEL_END_SLOT)
    if table % 4 or start % 4 or end - start != count * 4:
        raise ValueError("Playback/name table ranges disagree")
    records = elf.read(table, count * 40)
    stock = elf.read(STOCK_TABLE, 112 * 40)
    if records[: 112 * 40] != stock:
        raise ValueError("Original 112 shot records were not preserved")
    if start != 0x12F3ABF4:
        elf.read(start, count * 4)
        if word(0xA66200) != 0x12F3ABF4 or word(0xA66118) != 0x12F3ADB4:
            raise ValueError("Adjacent property-name ranges changed")
    else:
        elf.target(start)
        elf.target(end - 1)
    rows = []
    motions = {}
    for index in range(count):
        pointers = struct.unpack_from(">II", records, index * 40 + 32)
        for pointer in pointers:
            if pointer % 4:
                raise ValueError("Unaligned registered motion pointer")
            canonical_channels(elf.read(pointer, 64), "college-hoops-2k8")
            if motion_extents and pointer not in motions:
                from .target_motion import inspect_target_motion

                motions[pointer] = inspect_target_motion(elf, pointer)
        rows.append(dict(index=index, motions=list(pointers)))
    # The name initializer is unrolled. It writes exactly the original 112 cells
    # via R9; a separately initialized appended tagged name is not overwritten.
    if word(0x696A5C) != 0x81221838:
        raise ValueError("Shot-name initializer base load changed")
    offsets = []
    for address in range(0x696A60, 0x6970EC, 4):
        instruction = word(address)
        if instruction >> 26 == 36 and (instruction >> 16) & 31 == 9:
            offset = instruction & 65535
            offsets.append(offset - 65536 if offset & 32768 else offset)
    if sorted(offsets) != list(range(0, 112 * 4, 4)):
        raise ValueError("Shot-name initializer no longer covers exactly 112 cells")
    return dict(
        mode="read-only",
        stock_count=112,
        count=count,
        stride=40,
        playback_table=table,
        label_start=start,
        label_end=end,
        readers=list(READERS),
        original_records_preserved=True,
        original_name_initializer_cells=112,
        entries=rows,
        motion_extents_validated=motion_extents,
        motions=list(motions.values()),
        gameplay_ready=False,
        runtime_tested=False,
        note="Validates observed registration structures; does not install donor motions or certify gameplay.",
    )


def registration_padding(raw, count, *, motion_bytes=0):
    """Plan a bounded data allocation without changing bytes or consuming TLS.

    This reserves table, names and optional resident-image payload bytes within
    proven padding. It does not place a motion library or grant a native heap
    budget. Original section/segment offsets stay put.
    """
    if type(count) is not int or not 113 <= count <= 256:
        raise ValueError("Choose a total shot count from 113 to 256")
    if type(motion_bytes) is not int or not 0 <= motion_bytes <= 16 * 1024 * 1024:
        raise ValueError("Motion image size exceeds the bounded allocation plan")
    elf = NativeELF(raw)
    candidates = [
        s for s in elf.segments if s["address"] == 0x8A0000 and s["flags"] == 6
    ]
    if len(candidates) != 1:
        raise ValueError("Observed writable data segment is missing")
    segment = candidates[0]
    if segment["memory_bytes"] != segment["file_bytes"]:
        raise ValueError("Do not allocate over an existing data-segment BSS")
    old_end = segment["offset"] + segment["file_bytes"]
    limit = min(s["offset"] for s in elf.segments if s["offset"] > segment["offset"])
    phoff = struct.unpack_from(">Q", raw, 32)[0]
    stride, phcount = struct.unpack_from(">HH", raw, 54)
    tls_end = segment["address"] + segment["memory_bytes"]
    for i in range(phcount):
        typ, _, _, address, _, _, memory, _ = struct.unpack_from(
            ">II6Q", raw, phoff + i * stride
        )
        if typ == 7:  # PT_TLS must retain its original zero-filled template.
            tls_end = max(tls_end, address + memory)
    table = (tls_end + 15) & ~15
    labels = (table + count * 40 + 15) & ~15
    motion_image = (labels + count * 4 + 15) & ~15
    end = (motion_image + motion_bytes + 15) & ~15
    file_start = segment["offset"] + table - segment["address"]
    file_end = segment["offset"] + end - segment["address"]
    if any(
        s is not segment
        and segment["address"] < s["address"] + s["memory_bytes"]
        and s["address"] < end
        for s in elf.segments
    ):
        raise ValueError("Registration allocation overlaps native load memory")
    if file_start < old_end or file_end > limit or any(raw[old_end:file_end]):
        raise ValueError("Registration allocation would overwrite nonpadding data")
    return dict(
        table=table,
        labels=labels,
        motion_image=motion_image if motion_bytes else None,
        motion_bytes=motion_bytes,
        end=end,
        file_start=file_start,
        file_end=file_end,
        segment_address=segment["address"],
        new_segment_size=end - segment["address"],
        tls_end=tls_end,
        bytes_available=limit - file_start,
        bytes_required=file_end - file_start,
        mode="allocation-plan-only",
        runtime_tested=False,
    )
