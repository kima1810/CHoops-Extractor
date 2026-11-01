"""Auto-detected TOCs preserve game-specific serialization and shared previews."""
import json
import struct
import zlib

import pytest

from support import game_fixture, iff_fixture
from test_nba2k9_research import nba_fixture
from test_scene_preview import scene_fixture
from choops_py.archive import add_assets, build_copy, repack
from choops_py.archive.layouts import CH2K, NBA2K, decode_toc, pack_row
from choops_py.archive.manifests import digest
from choops_py.archive.usrdir_reader import Archive
from choops_py.formats.scne import preview_meshes
from choops_py.formats.standard_iff import StandardIFF


def test_automatic_layout_detection_keeps_college_hoops_extents(tmp_path):
    ch = Archive(game_fixture(tmp_path/'ch', iff_fixture()))
    nba = Archive(nba_fixture(tmp_path/'nba', [('ua000.iff', iff_fixture(), 1)]))
    assert ch.toc_layout == CH2K and nba.toc_layout == NBA2K
    assert ch.entries[0]['size'] == 2048
    assert nba.entries[0]['size'] == len(iff_fixture())


@pytest.mark.parametrize('layout', [CH2K, NBA2K])
def test_layout_pack_roundtrip_and_ambiguous_layout_rejection(layout):
    raw = bytearray(16)
    pack_row(raw, 0, [0x12345678, 1, 0, 100], layout)
    actual, rows = decode_toc(raw, 2048, 100, 4096)
    assert actual == layout
    assert rows[0]['hash'] == 0x12345678 and rows[0]['stored_size'] == 100
    # Both schemas can be valid for crafted tiny fields; never guess a winner.
    ambiguous = struct.pack('>4I', 0, 100, 1, 200)
    with pytest.raises(ValueError, match='ambiguous'):
        decode_toc(ambiguous, 1, 10, 1000)


@pytest.mark.parametrize('builder', [add_assets.build, repack.build])
def test_growing_nba_writers_keep_size64_schema_and_untouched_assets(tmp_path, builder):
    old = iff_fixture([b'old'])
    source = nba_fixture(tmp_path/'source', [('ua000.iff', old, 1), ('uh000.iff', old, 2)])
    arc = Archive(source)
    before = {p['name']: (arc.path/p['name']).read_bytes() for p in arc.parts}
    replacement = iff_fixture([b'new'*3000])
    out = tmp_path/'rebuilt'
    builder(source, {}, out, {'ua000.iff': replacement})
    result = Archive(out)
    assert result.toc_layout == NBA2K
    entries = {e['name']: e for e in result.entries}
    assert result.read(entries['ua000.iff']) == replacement
    assert result.read(entries['uh000.iff']) == old
    for name, data in before.items():assert (arc.path/name).read_bytes() == data


@pytest.mark.parametrize('grow', [False, True])
def test_shared_builder_and_preflight_accept_nba_layout(tmp_path, grow):
    original = iff_fixture([b'old'])
    source = nba_fixture(tmp_path/'source', [('ua000.iff', original, 1)])
    replacement = iff_fixture([b'new'*(3000 if grow else 1)])
    mod = tmp_path/'mod';mod.mkdir();(mod/'asset.iff').write_bytes(replacement)
    row = dict(archive='ua000.iff', subfile=None, kind='archive', path='asset.iff',
               size=len(replacement), sha256=digest(replacement))
    (mod/'overrides.json').write_text(json.dumps([row]), encoding='utf8')
    (mod/'import_options.json').write_text(json.dumps(dict(schema=1, allow_archive_growth=True)), encoding='utf8')
    out = tmp_path/'manual'/'NBA build'
    build_copy.build(source, mod, out)
    arc = Archive(out)
    assert arc.toc_layout == NBA2K
    assert arc.read(arc.entries[0]) == replacement


def test_internal_record_names_recover_crc_labels_without_type_guessing():
    raw = bytearray(iff_fixture([b'geometry'], [(0xe26c9b5d, [0])]))
    # The fixture descriptor follows its one record pointer at byte 68.
    struct.pack_into('>I', raw, 68, zlib.crc32(b'floor'))
    record = StandardIFF(bytes(raw)).records[0]
    assert record['name'] == 'floor' and record['type'] == 'SCNE'


def test_half4_uv_and_half4_color_preview_like_nba_arena():
    head, old = scene_fixture()
    head = bytearray(head)
    struct.pack_into('>I', head, 0x54+0x94, 3)
    head[472:480] = bytes.fromhex('200c000003040800')
    head[536:544] = bytes.fromhex('2014000003040300')
    struct.pack_into('>II', head, 332, 28, 4*28)
    data = old[:8]
    for i in range(4):
        xyzuv = struct.unpack_from('>3f2e', old, 8+i*16)
        data += struct.pack('>3f4e4e', *xyzuv[:3], *xyzuv[3:], 0., 0., .5, .25, 1., 1.)
    result = preview_meshes([bytes(head), data])
    assert not result['warnings']
    vertices = result['meshes'][0]['vertices']
    assert vertices[0][3:5] == (0., 0.)
    assert vertices[0][5:9] == (.5, .25, 1., 1.)


def test_size64_values_are_not_truncated_to_32_bits():
    size = 0x101000001
    raw = bytearray(16)
    pack_row(raw, 0, [0x12345678, 1, 0, size], NBA2K)
    layout, rows = decode_toc(raw, 2048, 100, 8*1024**3)
    assert layout == NBA2K and rows[0]['content_size'] == size


def test_cdf_standard_texture_hash_and_shared_record_label():
    from support import pair_fixture
    from choops_py.formats.cdf_backed_iff import CDFPair
    meta, data = pair_fixture();meta = bytearray(meta)
    struct.pack_into('>II', meta, 120, zlib.crc32(b'logo523'), 0x5c369069)
    row = CDFPair(bytes(meta), data).records[0]
    assert row['type'] == 'TXTR' and row['name'] == 'logo523'


def write_sfo(source, title):
    keys = b'TITLE\0TITLE_ID\0'
    text = title.encode()+b'\0';identity = b'TEST00000\0'
    values = 52+len(keys)
    header = struct.pack('<5I', 0x46535000, 0x101, 52, values, 2)
    header += struct.pack('<HHIII', 0, 0x0204, len(text), len(text), 0)
    header += struct.pack('<HHIII', 6, 0x0204, len(identity), len(identity), len(text))
    (source/'PS3_GAME/PARAM.SFO').write_bytes(header+keys+text+identity)


@pytest.mark.gui
def test_gui_auto_indexes_nba_and_preserves_college_roster_boundary(qtbot, tmp_path, monkeypatch):
    from choops_py.studio.app import Window
    source = nba_fixture(tmp_path/'source', [('ua000.iff', iff_fixture(), 1)])
    write_sfo(source, 'NBA 2K9')
    window = Window();qtbot.addWidget(window)
    window.open_game(source)
    qtbot.waitUntil(lambda: window.active is None, timeout=10000)
    assert window.archive.toc_layout == NBA2K
    assert 'NBA 2K9' in window.identity.text()
    assert window.scene_uniforms.count() == 2
    errors = []
    monkeypatch.setattr(window, 'show_error', errors.append)
    window.load_game_roster()
    assert len(errors) == 1 and 'Roster identity is missing' in errors[0]
    assert window.roster is None
    window.archive.game_info={}
    window.load_game_roster()
    assert len(errors)==2  # USRDIR-only sources have no SFO, but still must not use the wrong roster schema.


def test_gui_extraction_keeps_iff_suffix_for_unresolved_hash(tmp_path, monkeypatch):
    from choops_py.studio import services
    source = nba_fixture(tmp_path/'source', [('unresolved_research_asset.iff', iff_fixture(), 1)])
    arc = Archive(source);assert arc.entries[0]['name'] is None
    monkeypatch.setattr(services, 'safe_output', lambda p, _: p)
    monkeypatch.setattr(services, 'save_json', lambda p, data, _: p.write_text(json.dumps(data), encoding='utf8'))
    output = tmp_path/'export'
    report = services.extract(arc, arc.entries, output)
    name = report['entries'][0]['output']
    assert name.endswith('.iff') and (output/name).read_bytes() == iff_fixture()


def test_nba_dds_override_preview_and_rebuild_share_detected_source(tmp_path):
    import shutil
    import uuid
    from support import txtr_fixture
    from choops_py.archive.manifests import OUTPUT
    from choops_py.studio.services import stage_folder
    from choops_py.studio.preview_source import PreviewArchive
    from choops_py.formats.standard_iff_writer import record_blocks
    from choops_py.formats.txtr import TXTR
    from choops_py.texture_tools import dds
    from choops_py.texture_tools.builtin_converter import to_dds
    root = OUTPUT/'temp'/('nba_override_'+uuid.uuid4().hex);root.mkdir(parents=True)
    try:
        txtr = txtr_fixture()
        original = bytearray(iff_fixture(txtr))
        struct.pack_into('>I', original, 68, zlib.crc32(b'unif'))
        source = nba_fixture(root/'source', [('uh000.iff', bytes(original), 1)])
        folder = root/'overrides'/'uh000';folder.mkdir(parents=True)
        artwork = dds.linear_l8(4, 4, 1, b'\xc0'*16)
        (folder/'unif.dds').write_bytes(artwork)
        result = stage_folder(source, folder.parent, root/'prepared', workers=1)
        base = Archive(source);overlay = PreviewArchive(base, result['mod'])
        assert overlay.toc_layout == NBA2K
        changed = overlay.read(overlay.entries[0])
        assert changed != base.read(base.entries[0])
        iff = StandardIFF(changed);texture = TXTR([b[3] for b in record_blocks(iff, iff.records[0])])
        assert to_dds(texture.gtf())[128:] == artwork[128:]
        build_copy.build(source, result['mod'], root/'build')
        rebuilt = Archive(root/'build')
        assert rebuilt.toc_layout == NBA2K
        assert rebuilt.read(rebuilt.entries[0]) == changed
    finally:
        assert root.resolve().is_relative_to((OUTPUT/'temp').resolve())
        shutil.rmtree(root)
