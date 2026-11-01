import json
import struct

import pytest
from support import iff_fixture

from choops_py.formats.cdf_backed_iff_writer import name_trailer
from choops_py.formats.standard_iff import StandardIFF
from choops_py.formats.standard_iff_writer import record_blocks
from choops_py.modding import uniform_mesh as mesh

pytestmark = pytest.mark.unit


def garment_fixture(constraints=False):
    raw = bytearray(4096)

    def u(p, v):
        struct.pack_into(">I", raw, p, v)

    def ptr(p, target):
        u(p, target - p + 1)

    u(0x44, 1)
    ptr(0x48, 128)
    u(0x3C, 1)
    ptr(0x40, 384)
    struct.pack_into(">16f", raw, 384, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)
    ptr(128, 700)
    raw[700:714] = "player\0".encode("utf-16-be")
    u(128 + 0x84, 1)
    ptr(128 + 0x88, 544)
    u(560, 4)
    u(564, 3)
    for i, (stride, start) in enumerate(((4, 2048), (24, 2112), (4, 2240))):
        e = 572 + i * 16
        u(e, 0x40000002)
        u(e + 4, stride)
        u(e + 8, 4 * stride)
        ptr(e + 12, start)
    u(128 + 0x94, 6)
    ptr(128 + 0x9C, 1024)
    for i, code in enumerate(
        (
            "2000010002030000",
            "200c010006010f00",
            "2010010006010200",
            "2014010006010e00",
            "2000000001020800",
            "2000020202010a00",
        )
    ):
        raw[1032 + i * 64 : 1040 + i * 64] = bytes.fromhex(code)
    u(128 + 0xA4, 0x10)
    u(128 + 0xA8, 4)
    ptr(128 + 0xAC, 1600)
    u(128 + 0x7C, 1)
    ptr(128 + 0x80, 1536)
    u(1536, 6)
    u(1544, 4)
    struct.pack_into(">4H", raw, 1600, 0, 1, 2, 3)
    positions = [
        (-10.0, 10.0, 0.0),
        (10.0, 10.0, 0.0),
        (-10.0, 30.0, 0.0),
        (10.0, 30.0, 0.0),
    ]
    for i, v in enumerate(positions):
        struct.pack_into(">3f", raw, 2112 + i * 24, *v)
        raw[2112 + i * 24 + 12 : 2112 + (i + 1) * 24] = bytes(range(12))
        struct.pack_into(">2h", raw, 2048 + i * 4, (i % 2) * 32767, (i // 2) * 32767)
    raw[3000:3008] = b"KEEPDATA"
    cloth = bytearray(1536)
    struct.pack_into(">H", cloth, 0, 80)
    struct.pack_into(">I", cloth, 0xC0, 1024)
    struct.pack_into(">I", cloth, 0xC8, 1104)
    for i, v in enumerate([(1.0, 2.0, 3.0), *positions]):
        struct.pack_into(">4f", cloth, 1024 + i * 16, *v, 1.0)
    cloth[1200:1208] = b"SOLVER!!"
    if constraints:
        struct.pack_into(">HH", cloth, 4, 8, 8)
        struct.pack_into(">II", cloth, 0xD4, 1232, 1280)
        for table, length in ((1232, 640), (1280, 512)):
            for i in range(8):
                struct.pack_into(">I", cloth, table + i * 4,
                                 (1 << 20) | (length << 10) | 1)
    names = [
        {"name": "jersey_u_reg", "type": "SCNE"},
        {"name": "jersey_u_reg", "type": "Clth"},
        {"name": "unknown", "type": "UNKNOWN"},
    ]
    return iff_fixture(
        [bytes(raw) + bytes(cloth) + b"UNCHANGED"],
        [(0xE26C9B5D, [0]), (0xE1124F13, [4096]), (0x12345678, [5632])],
    ) + name_trailer(names)


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    from choops_py.archive import manifests

    monkeypatch.setattr(manifests, "OUTPUT", tmp_path)
    source = tmp_path / "cloth_u_reg.iff"
    source.write_bytes(garment_fixture())
    return source, tmp_path


def test_noop_obj_roundtrip_is_byte_identical(workspace):
    source, root = workspace
    mesh.export_iff(source, root / "export")
    result = mesh.import_iff(source, root / "export", root / "reimport.iff")
    assert result["changed_vertices"] == 0
    assert source.read_bytes() == (root / "reimport.iff").read_bytes()


def test_rest_edit_preserves_every_other_byte_and_unknown_record(workspace):
    source, root = workspace
    mesh.export_iff(source, root / "export")
    iff = StandardIFF(source.read_bytes())
    pairs = mesh._pairs(iff)
    r, c, sb, cb, layout, start, mapping = pairs[0]
    positions = [
        tuple(x * 0.96 if k == 0 else x for k, x in enumerate(v))
        for v in layout["positions"]
    ]
    mesh.write_obj(
        root / "export/jersey_u_reg.obj", positions, layout["uvs"], layout["faces"]
    )
    mesh.import_iff(source, root / "export", root / "new.iff")
    changed = StandardIFF((root / "new.iff").read_bytes())
    after_s = record_blocks(changed, changed.records[0])[0][3]
    after_c = record_blocks(changed, changed.records[1])[0][3]
    allowed_s = {
        layout["position_start"] + i * 24 + j for i in range(4) for j in range(12)
    }
    allowed_c = {start + p * 16 + j for p in mapping for j in range(12)}
    assert all(a == b or i in allowed_s for i, (a, b) in enumerate(zip(sb, after_s)))
    assert all(a == b or i in allowed_c for i, (a, b) in enumerate(zip(cb, after_c)))
    assert record_blocks(changed, changed.records[2])[0][3] == b"UNCHANGED"
    assert source.read_bytes() == garment_fixture()


def test_import_adapts_solver_distances_as_well_as_rest_mesh(workspace):
    source, root = workspace
    source.write_bytes(garment_fixture(constraints=True))
    mesh.export_iff(source, root / "export")
    pairs = mesh._pairs(StandardIFF(source.read_bytes()))
    layout = pairs[0][4]
    positions = [(x * 0.5, y, z) for x, y, z in layout["positions"]]
    mesh.write_obj(root / "export/jersey_u_reg.obj",
                   positions, layout["uvs"], layout["faces"])
    report = mesh.import_iff(source, root / "export", root / "new.iff")
    assert report["changed_constraints"] == 16
    result = StandardIFF((root / "new.iff").read_bytes())
    cloth = record_blocks(result, result.records[1])[0][3]
    for table, length in ((1232, 320), (1280, 256)):
        for i in range(8):
            assert struct.unpack_from(">I", cloth, table + i * 4)[0] == (
                (1 << 20) | (length << 10) | 1)
    assert cloth[1200:1208] == b"SOLVER!!"


@pytest.mark.parametrize("change", ["faces", "uvs", "count", "nan", "far", "inverted"])
def test_unsafe_obj_edits_rejected(workspace, change):
    source, root = workspace
    mesh.export_iff(source, root / "export")
    path = root / "export/jersey_u_reg.obj"
    text = path.read_text()
    if change == "faces":
        text = text.replace("f 1/1 2/2 3/3", "f 2/2 1/1 3/3")
    if change == "uvs":
        text = text.replace("vt 0 0", "vt 0.1 0")
    if change == "count":
        text += "\nv 1 2 3\n"
    if change == "nan":
        text = text.replace("v -10 10 0", "v nan 10 0")
    if change == "far":
        text = text.replace("v -10 10 0", "v -100 10 0")
    if change == "inverted":
        text = text.replace("v -10 10 0", "v 10 25 0")
    path.write_text(text)
    with pytest.raises(ValueError):
        mesh.import_iff(source, root / "export", root / "bad.iff")
    assert not (root / "bad.iff").exists()


def test_stale_manifest_and_existing_output_rejected(workspace):
    source, root = workspace
    mesh.export_iff(source, root / "export")
    path = root / "export/manifest.json"
    doc = json.loads(path.read_text())
    doc["source_sha256"] = "0" * 64
    path.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="original IFF"):
        mesh.import_iff(source, root / "export", root / "bad.iff")
    with pytest.raises(ValueError):
        mesh.import_iff(source, root / "export", source)


def test_ambiguous_and_missing_cloth_vertices_rejected():
    pairs = mesh._pairs(StandardIFF(garment_fixture()))
    r, c, sb, cb, layout, start, mapping = pairs[0]
    raw = bytearray(cb)
    raw[start : start + 12] = raw[start + 16 : start + 28]
    with pytest.raises(ValueError, match="ambiguous"):
        mesh._cloth(raw, layout["positions"])
    raw = bytearray(cb)
    raw[start + 16 : start + 28] = struct.pack(">3f", 22, 23, 24)
    with pytest.raises(ValueError, match="missing"):
        mesh._cloth(raw, layout["positions"])


def test_preset_preserves_attachment_regions_and_shortens_hem():
    vertices = [(-10.0, float(y), 10.0) for y in range(101)]
    top = mesh.modern_positions(vertices)
    shorts = mesh.modern_positions(vertices, True)
    assert top[0] == vertices[0] and top[-1] == vertices[-1]
    assert top[40][0] == pytest.approx(-9.3)
    assert shorts[0][1] == 20 and shorts[80:] == vertices[80:]
    assert all(b[1] > a[1] for a, b in zip(shorts, shorts[1:]))


def test_split_stream_layout_remains_read_only():
    pair = mesh._pairs(StandardIFF(garment_fixture()))[0]
    raw = bytearray(pair[2])
    struct.pack_into(">I", raw, 128 + 0xA4, 0x20000010)
    with pytest.raises(ValueError, match="layout"):
        mesh._layout(raw)


def test_split_sewn_vertices_cannot_be_imported(workspace):
    source, root = workspace
    raw = bytearray(source.read_bytes())
    iff = StandardIFF(raw)
    block, offset, end, scene = record_blocks(iff, iff.records[0])[0]
    start = iff.blocks[block]["start"] + offset + 2112
    raw[start + 24 : start + 36] = raw[start : start + 12]
    source.write_bytes(raw)
    mesh.export_iff(source, root / "export")
    obj = root / "export/jersey_u_reg.obj"
    text = obj.read_text().replace("v -10 10 0", "v -10 10 1", 1)
    obj.write_text(text)
    with pytest.raises(ValueError, match="sewn"):
        mesh.import_iff(source, root / "export", root / "split.iff")


@pytest.mark.gui
def test_uniform_menu_dispatches_all_workflows(qtbot, monkeypatch):
    from PySide6.QtWidgets import QPushButton

    from choops_py.studio.app import Window

    calls = []
    monkeypatch.setattr(
        Window, "uniform_mesh_export", lambda self, modern: calls.append(modern)
    )
    monkeypatch.setattr(
        Window, "uniform_mesh_import", lambda self: calls.append("import")
    )
    window = Window()
    qtbot.addWidget(window)
    button = next(
        b for b in window.findChildren(QPushButton) if b.text() == "Uniform meshes…"
    )
    for action in button.menu().actions():
        action.trigger()
    assert calls == [False, True, "import"]
    window.close()


@pytest.mark.gui
def test_uniform_export_uses_selected_preview_source(qtbot, monkeypatch):
    from choops_py.studio.app import Window
    from choops_py.studio.services import JobContext

    window = Window()
    qtbot.addWidget(window)
    base, selected = object(), object()
    window.archive = base
    monkeypatch.setattr(window, "preview_archive", lambda: selected)
    calls = []
    monkeypatch.setattr(
        mesh,
        "export_archive",
        lambda archive, out, modern, job: calls.append((archive, out, modern)),
    )
    monkeypatch.setattr(
        window,
        "run_job",
        lambda label, function, callback, cancellable: function(JobContext()),
    )
    window.uniform_mesh_export(True)
    assert calls[0][0] is selected and calls[0][2] is True
    assert calls[0][1].parent.name == "uniform-models"
    window.archive = None
    window.close()
