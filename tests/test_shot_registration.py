import struct

import pytest

from choops_py.formats.embedded_motion import NativeELF
from choops_py.research.shot_registration import (
    CAP_INSTRUCTION,
    LABEL_END_SLOT,
    LABEL_START_SLOT,
    READ_REGISTERS,
    READERS,
    STOCK_TABLE,
    TABLE_SLOT,
    inspect_registration,
    registration_padding,
)


def registration_fixture():
    ranges = [
        (0x11000, 64, 64, 4),
        (0x321000, 0xB000, 0xB000, 5),
        (0x694000, 0xB000, 0xB000, 5),
        (0x8A0000, 0x1CC550, 0x1CC550, 6),
        (0x10000000, 16, 16, 4),
        (0x12F3ABF4, 0, 448, 6),
    ]
    raw = bytearray(0x31D000)
    raw[:7] = b"\x7fELF\x02\x02\x01"
    struct.pack_into(">HH", raw, 16, 2, 21)
    struct.pack_into(">Q", raw, 32, 64)
    struct.pack_into(">HH", raw, 54, 56, len(ranges) + 1)
    pos = 0x1000
    for i, (address, size, memory, flags) in enumerate(ranges):
        if address == 0x10000000:
            pos = 0x310000
        struct.pack_into(
            ">II6Q", raw, 64 + i * 56, 1, flags, pos, address, address, size, memory, 16
        )
        pos = (pos + size + 0xFFF) & ~0xFFF
    struct.pack_into(
        ">II6Q", raw, 64 + len(ranges) * 56, 7, 4, 0, 0xA6C550, 0xA6C550, 0, 0xA8, 16
    )
    elf = NativeELF(raw)

    def word(address, value):
        struct.pack_into(">I", raw, elf.target(address)["file_offset"], value)

    word(0x11004, 0x1DF7DD)
    word(0x1100C, 0x49244)
    word(0x11010, (21 << 18) | (17 << 12) | (6 << 6))
    for i in range(112):
        word(STOCK_TABLE + i * 40 + 32, 0x11000)
        word(STOCK_TABLE + i * 40 + 36, 0x11000)
    for address, register in zip(READERS, READ_REGISTERS, strict=True):
        word(address, 32 << 26 | register << 21 | 2 << 16 | 0x3B40)
    for address, value in [
        (CAP_INSTRUCTION, 0x3800006F),
        (0x69E938, 0x88630073),
        (0x69E94C, 0x98830073),
        (TABLE_SLOT, STOCK_TABLE),
        (LABEL_START_SLOT, 0x12F3ABF4),
        (LABEL_END_SLOT, 0x12F3ADB4),
        (0x696A5C, 0x81221838),
        (0xA66200, 0x12F3ABF4),
        (0xA66118, 0x12F3ADB4),
        (0x694CF0, 0x83A21768),
        (0x694D08, 0x80021838),
    ]:
        word(address, value)
    for i in range(112):
        word(0x696A60 + i * 4, 0x90690000 | (i * 4))
    return raw, word


def test_original_registration_and_tls_safe_plan_are_read_only():
    raw, _ = registration_fixture()
    before = bytes(raw)
    report = inspect_registration(raw)
    plan = registration_padding(raw, 113)
    assert report["count"] == 112 and report["original_records_preserved"]
    assert plan["table"] >= 0xA6C5F8 and plan["table"] % 16 == 0
    assert plan["bytes_required"] <= plan["bytes_available"]
    assert not report["runtime_tested"] and not plan["runtime_tested"]
    assert raw == before


@pytest.mark.parametrize(
    "address,value",
    [
        (CAP_INSTRUCTION, 0x38000100),
        (READERS[0], 0x81623B44),
        (LABEL_END_SLOT, 0x12F3ADB8),
        (0x696A60, 0),
        (STOCK_TABLE + 32, 0x11001),
        (0x69E94C, 0x98830074),
    ],
)
def test_registration_fails_closed_on_changed_consumers_or_structures(address, value):
    raw, word = registration_fixture()
    word(address, value)
    with pytest.raises(ValueError):
        inspect_registration(raw)


def test_padding_never_overwrites_nonzero_data():
    raw, _ = registration_fixture()
    plan = registration_padding(raw, 113)
    raw[plan["file_start"]] = 1
    with pytest.raises(ValueError, match="nonpadding"):
        registration_padding(raw, 113)


def test_owned_motion_image_plan_reserves_bytes_after_names_and_tls():
    raw, _ = registration_fixture()
    empty = registration_padding(raw, 113)
    plan = registration_padding(raw, 113, motion_bytes=512)
    assert plan["motion_image"] == empty["end"]
    assert plan["bytes_required"] == empty["bytes_required"] + 512
    assert plan["end"] == empty["end"] + 512
    for size in (-1, 16 * 1024 * 1024 + 1, True):
        with pytest.raises(ValueError, match="bounded allocation"):
            registration_padding(raw, 113, motion_bytes=size)
    with pytest.raises(ValueError, match="nonpadding"):
        registration_padding(raw, 113, motion_bytes=16 * 1024 * 1024)


def test_deep_registration_checks_reject_a_header_with_missing_tracks():
    raw, _ = registration_fixture()
    # Shallow registration checks masks only; deep validation reaches timing/tracks.
    assert inspect_registration(raw)["motion_extents_validated"] is False
    with pytest.raises(ValueError, match="count/rate"):
        inspect_registration(raw, motion_extents=True)


def test_padding_plan_rejects_virtual_collision_even_when_file_padding_is_free():
    raw, _ = registration_fixture()
    plan = registration_padding(raw, 113, motion_bytes=512)
    count = struct.unpack_from(">H", raw, 56)[0]
    struct.pack_into(">H", raw, 56, count + 1)
    address = plan["end"] - 16
    struct.pack_into(
        ">II6Q", raw, 64 + count * 56, 1, 4, 0x315000, address, address, 16, 16, 16
    )
    with pytest.raises(ValueError, match="overlaps native load memory"):
        registration_padding(raw, 113, motion_bytes=512)
