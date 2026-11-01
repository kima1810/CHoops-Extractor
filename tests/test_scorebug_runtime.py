import json
import struct

import pytest

from choops_py.research.scorebug_runtime import (
    POPUP_COUNT,
    POPUP_TABLE,
    inspect_runtime,
)

pytestmark = pytest.mark.unit


def fixture():
    raw = bytearray(0xC00)
    raw[:7] = b"\x7fELF\x02\x02\x01"
    struct.pack_into(">HH", raw, 16, 2, 21)
    struct.pack_into(">Q", raw, 32, 64)
    struct.pack_into(">HH", raw, 54, 56, 4)
    for i, (flags, pos, va, size) in enumerate([
        (5, 0x200, 0x500000, 16), (6, 0x300, 0xA30000, 32),
        (6, 0x400, 0xA64A94, 16), (6, 0x500, POPUP_TABLE, POPUP_COUNT * 20),
    ]):
        struct.pack_into(">II6Q", raw, 64 + i * 56,
                         1, flags, pos, va, va, size, size + 16, 4)
    for i in range(3):
        struct.pack_into(">II", raw, 0x300 + i * 8, 0x500000 + i * 4, 0xA64A94)
    for i in range(POPUP_COUNT):
        # Priority deliberately does not encode provider count.
        struct.pack_into(">5I", raw, 0x500 + i * 20,
                         i % 4, 2, 0xA30000, 0, 0)
    struct.pack_into(">II", raw, 0x500 + 37 * 20 + 12, 0xA30008, 0xA30010)
    return raw


def test_catalog_preserves_input_and_distinguishes_priority_from_lines():
    raw = fixture()
    before = bytes(raw)
    result = inspect_runtime(raw)
    assert bytes(raw) == before
    assert len(result["rows"]) == 83 and result["unique_providers"] == 3
    assert result["rows"][79]["priority"] == 2
    assert sum(p is not None for p in result["rows"][79]["providers"]) == 1
    assert len([p for p in result["rows"][37]["providers"] if p]) == 3
    assert result["runtime_state_observed"] is False
    assert result["patch_supported"] is False


@pytest.mark.parametrize("failure", [
    "priority", "queue", "missing", "alignment", "code", "toc", "unbacked",
    "crossing", "non-executable",
])
def test_invalid_dispatch_dependencies_fail_closed(failure):
    raw = fixture()
    if failure == "priority":
        struct.pack_into(">I", raw, 0x504, 0)
    if failure == "queue":
        struct.pack_into(">I", raw, 0x500, 4)
    if failure == "missing":
        struct.pack_into(">I", raw, 0x508, 0)
    if failure == "alignment":
        struct.pack_into(">I", raw, 0x508, 0xA30001)
    if failure == "code":
        struct.pack_into(">I", raw, 0x300, 0x500001)
    if failure == "toc":
        struct.pack_into(">I", raw, 0x304, 0xB00000)
    if failure == "unbacked":
        struct.pack_into(">I", raw, 0x508, 0xA30020)
    if failure == "crossing":
        struct.pack_into(">Q", raw, 64 + 3 * 56 + 32, POPUP_COUNT * 20 - 1)
    if failure == "non-executable":
        struct.pack_into(">I", raw, 68, 4)
    with pytest.raises(ValueError):
        inspect_runtime(raw)


def test_cli_catalog_and_source_output_guard(tmp_path, monkeypatch):
    from choops_py.archive import manifests
    from choops_py.cli import execute, parser

    monkeypatch.setattr(manifests, "OUTPUT", tmp_path)
    source = tmp_path / "analysis.elf"
    source.write_bytes(fixture())
    output = tmp_path / "report.json"
    execute(parser().parse_args(["inspect-scorebug-runtime", str(source), str(output)]))
    assert len(json.loads(output.read_text())["rows"]) == 83
    before = source.read_bytes()
    with pytest.raises(ValueError):
        execute(parser().parse_args([
            "inspect-scorebug-runtime", str(source), str(source),
        ]))
    assert source.read_bytes() == before
