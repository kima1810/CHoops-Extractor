import pytest
from test_roster_semantics import header_roster

from choops_py.archive.catalog import record_references
from choops_py.core.errors import ToolError
from choops_py.roster.adapters import load_bytes
from choops_py.roster.conference_assets import logo_record
from choops_py.roster.editor_model import EditorModel


def test_logo_routes_use_conference_index_not_tournament_index():
    data, _ = header_roster()
    model = EditorModel(load_bytes(bytes(data)))
    model.rows['conferences'][0]['conference_name'] = 'Conference A'
    model.rows['conferences'][0]['presentation_id'] = 55
    result = record_references('teamselectlogo.iff', [{'name': 'logo900'}, {'name': 'logo955'}], model)
    assert result[0]['references'] == 'Conference A'
    assert result[1]['references'] == ''
    assert logo_record(38) == 'logo938'
    for index in (-1, 39, True):
        with pytest.raises(ValueError):
            logo_record(index)


def test_tournament_link_is_protected_until_bracket_writer_exists():
    data, _ = header_roster()
    model = EditorModel(load_bytes(bytes(data)))
    before = bytes(model.data)
    with pytest.raises(ToolError):
        model.edit('conferences', 0, 'presentation_id', 55)
    assert bytes(model.data) == before


@pytest.mark.gui
def test_conference_logo_shortcut_selects_exact_record_and_current_source(qtbot, monkeypatch):
    from pathlib import Path
    from types import SimpleNamespace

    from choops_py.studio.app import Window, selected
    window = Window()
    qtbot.addWidget(window)
    archive = SimpleNamespace(entries=[{'index': 3, 'name': 'teamselectlogo.iff'}])
    monkeypatch.setattr(window, 'preview_archive', lambda: archive)
    source = Path('teamselectlogo.iff')
    monkeypatch.setattr('choops_py.studio.app.materialize', lambda chosen, entry: source if chosen is archive else None)
    result = {'path': source, 'records': [], 'hex': b'', 'warning': '', 'textures': [
        {'name': name, 'kind': 'TXTR', 'editable': True, 'metadata': {'width': 4, 'height': 4}}
        for name in ('logo900', 'logo901')]}
    monkeypatch.setattr('choops_py.studio.app.inspect_asset', lambda path: result)
    monkeypatch.setattr(window, 'run_job', lambda label, work, display, **kwargs: display(work(None)))
    decoded = []
    monkeypatch.setattr(window, 'decode_texture_preview', lambda name, target: decoded.append(name))
    window._scene_record_index = 1
    window.open_conference_logo(1)
    assert selected(window.textures)[0]['name'] == 'logo901'
    assert window._scene_record_index is None
    qtbot.waitUntil(lambda: len(decoded) > 0)
    assert all(name == 'logo901' for name in decoded)
