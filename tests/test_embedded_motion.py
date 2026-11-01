import struct

import pytest

from choops_py.formats.embedded_motion import NativeELF, inspect_embedded


def native_fixture(profile):
    raw = bytearray(0x600)
    raw[:7] = b"\x7fELF\x02\x02\x01"
    struct.pack_into(">HH", raw, 16, 2, 21)
    struct.pack_into(">Q", raw, 32, 64)
    struct.pack_into(">HH", raw, 54, 56, 2)
    struct.pack_into(">II6Q", raw, 64, 1, 6, 0x200, 0x10000, 0x10000, 0x200, 0x200, 16)
    struct.pack_into(">II6Q", raw, 120, 1, 4, 0x400, 0x20000, 0x20000, 0x200, 0x300, 16)
    mask = 4 if profile == "college-hoops-2k8" else 8
    struct.pack_into(">I", raw, 0x200 + mask, 0x1DF7DD)
    struct.pack_into(">I", raw, 0x210, 2)
    struct.pack_into(">f", raw, 0x220, 1.5)
    fields = (
        (0x30, 0x34, 0x38) if profile == "college-hoops-2k8" else (0x24, 0x28, 0x30)
    )
    for i, field in enumerate(fields):
        struct.pack_into(">I", raw, 0x200 + field, 0x20000 + i * 16)
    return raw


@pytest.mark.parametrize("profile", ["college-hoops-2k8", "nba-2k11"])
def test_absolute_embedded_headers_keep_source_and_report_partial_coverage(profile):
    raw = native_fixture(profile)
    before = bytes(raw)
    result = inspect_embedded(raw, profile)
    assert len(result["candidates"]) == 1
    assert result["candidates"][0]["address"] == 0x10000
    assert len(result["candidates"][0]["pointers"]) == 3
    assert result["complete_library"] is False and result["import_supported"] is False
    assert bytes(raw) == before
    struct.pack_into(">I", raw, 0x230, 0xF0000000)
    result = inspect_embedded(raw, profile)
    assert not result["candidates"] and result["rejected"]


def test_unbacked_native_dependency_is_explicit_not_extracted_as_bytes():
    raw = native_fixture("college-hoops-2k8")
    struct.pack_into(">I", raw, 0x230, 0x20280)
    row = inspect_embedded(raw, "college-hoops-2k8")["candidates"][0]
    assert row["pointers"][0]["file_backed"] is False
    assert row["pointers"][0]["file_offset"] is None


def test_native_elf_rejects_wrong_machine_overlap_and_unestablished_game():
    raw = native_fixture("college-hoops-2k8")
    with pytest.raises(ValueError, match="not established"):
        inspect_embedded(raw, "nba-2k14")
    struct.pack_into(">H", raw, 18, 62)
    with pytest.raises(ValueError, match="PowerPC64"):
        NativeELF(raw)
    struct.pack_into(">H", raw, 18, 21)
    struct.pack_into(">Q", raw, 120 + 16, 0x10080)
    with pytest.raises(ValueError, match="Ambiguous"):
        NativeELF(raw)
