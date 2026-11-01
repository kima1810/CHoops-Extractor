import json
import shutil
import uuid
from pathlib import Path

import pytest
from PySide6.QtWidgets import QPushButton, QMessageBox

from choops_py.archive.manifests import OUTPUT
from choops_py.studio.services import stage_folder
from choops_py.studio.app import Window
from support import game_fixture, iff_fixture


@pytest.fixture
def workspace():
    work = OUTPUT / 'temp' / ('override_destination_' + uuid.uuid4().hex)
    work.mkdir(parents=True)
    yield work
    shutil.rmtree(work)


def fixture_inputs(work):
    source = game_fixture(work / 'game', iff_fixture(records=[(0xa7701f00, [0])]))
    folder = work / 'overrides'
    folder.mkdir()
    (folder / 'ua000.iff').write_bytes(iff_fixture([b'new!'], [(0xa7701f00, [0])]))
    return source, folder


def test_repeat_selection_preserves_old_workspace_and_compiles_new_snapshot(workspace):
    source, folder = fixture_inputs(workspace)
    mod = workspace / 'mod'
    first = stage_folder(source, folder, mod)
    original = {str(p.relative_to(mod)): p.read_bytes() for p in mod.rglob('*') if p.is_file()}
    (folder / 'ua000.iff').write_bytes(iff_fixture([b'next'], [(0xa7701f00, [0])]))
    (workspace / 'mod_2').mkdir()
    (workspace / 'mod_2' / 'personal.txt').write_text('keep', encoding='utf8')
    report = stage_folder(source, folder, mod)
    assert report['workspace_changed'] and Path(report['mod']) == workspace / 'mod_3'
    assert first['workspace_changed'] is False
    assert original == {str(p.relative_to(mod)): p.read_bytes() for p in mod.rglob('*') if p.is_file()}
    assert (workspace / 'mod_2' / 'personal.txt').read_text(encoding='utf8') == 'keep'
    rows = json.loads((Path(report['mod']) / 'overrides.json').read_text(encoding='utf8'))
    assert (Path(report['mod']) / rows[0]['path']).read_bytes() == (folder / 'ua000.iff').read_bytes()


def test_failed_selection_keeps_existing_workspace_and_removes_partial(workspace, monkeypatch):
    source, folder = fixture_inputs(workspace)
    mod = workspace / 'mod'
    mod.mkdir()
    (mod / 'keep.txt').write_bytes(b'keep')
    def reject(*args):
        raise ValueError('synthetic compatibility failure')
    monkeypatch.setattr('choops_py.archive.build_copy.preflight', reject)
    with pytest.raises(ValueError, match='compatibility failure'):
        stage_folder(source, folder, mod)
    assert (mod / 'keep.txt').read_bytes() == b'keep'
    assert not (workspace / 'mod_2').exists()
    assert not list(workspace.glob('.mod_*'))


@pytest.mark.gui
def test_completed_selection_updates_build_and_preview_workspace(qtbot, monkeypatch):
    window = Window()
    qtbot.addWidget(window)
    messages = []
    monkeypatch.setattr(QMessageBox, 'information', lambda *args: messages.append(args[2]))
    window.builder_completed(dict(mod=str(OUTPUT / 'builds' / 'my_mod_2'),
                                  staged=1, workspace_changed=True), 'staging')
    assert window.mod_path.text() == window.preview_mod
    assert window.mod_path.text().endswith('my_mod_2')
    assert any(b.text() == 'Select overrides folder…' for b in window.findChildren(QPushButton))
    assert 'staging' not in messages[0].lower()
    assert 'preserved' in messages[0]


@pytest.mark.gui
def test_new_override_folder_refreshes_lists_when_overrides_already_selected(qtbot, monkeypatch):
    from types import SimpleNamespace
    window=Window();qtbot.addWidget(window)
    entries=[dict(index=0,name='s258.iff'),dict(index=1,name='uh258.iff'),dict(index=2,name='shoe_1.iff')]
    window.archive=SimpleNamespace(entries=entries)
    old=SimpleNamespace(entries=entries,replacements={})
    new=SimpleNamespace(entries=entries,replacements={0:object(),1:object()})
    monkeypatch.setattr(window,'preview_archive',lambda:old)
    window.preview_overrides.setChecked(True)
    assert '[JB fallback]' in window.scene_stadiums.itemText(1)
    # Result callbacks run before the worker's finished signal.
    window.active=object()
    pending=[]
    monkeypatch.setattr('choops_py.studio.app.QTimer.singleShot',lambda *args:pending.append(args))
    monkeypatch.setattr(window,'preview_archive',lambda:new)
    monkeypatch.setattr(QMessageBox,'information',lambda *args:None)
    window.builder_completed(dict(mod=str(OUTPUT/'builds'/'fresh_overrides'),staged=2),'staging')
    assert '[Override]' in window.scene_stadiums.itemText(1)
    assert '[Override]' in window.scene_uniforms.itemText(1)
    assert '[JB fallback]' in window.scene_shoes.itemText(1)
    assert window.preview_source_info.text()=='2 prepared overrides — select folder again for live files'
    assert pending and pending[-1][0]==0
    window.active=None


@pytest.mark.gui
def test_preview_uses_visible_workspace_not_previous_cached_path(qtbot, monkeypatch, tmp_path):
    window=Window();qtbot.addWidget(window)
    window.archive=object()
    window.preview_mod=str(tmp_path/'old')
    current=tmp_path/'current';current.mkdir()
    (current/'overrides.json').write_text('[]',encoding='utf8')
    (current/'source_preconditions.json').write_text('{}',encoding='utf8')
    window.mod_path.setText(str(current))
    window.preview_overrides.blockSignals(True)
    window.preview_overrides.setChecked(True)
    window.preview_overrides.blockSignals(False)
    calls=[]
    monkeypatch.setattr('choops_py.studio.preview_source.PreviewArchive',lambda archive,mod:calls.append(mod))
    window.preview_archive()
    assert calls==[str(current)]


@pytest.mark.gui
def test_unavailable_override_workspace_is_not_labelled_jb_fallback(qtbot, monkeypatch):
    from types import SimpleNamespace
    window=Window();qtbot.addWidget(window)
    window.archive=SimpleNamespace(entries=[dict(index=0,name='s258.iff')])
    window.preview_overrides.blockSignals(True)
    window.preview_overrides.setChecked(True)
    window.preview_overrides.blockSignals(False)
    def invalid():
        raise ValueError('Missing source preconditions')
    monkeypatch.setattr(window,'preview_archive',invalid)
    window.refresh_preview_lists()
    assert '[Overrides unavailable]' in window.scene_stadiums.itemText(1)
    assert '[JB fallback]' not in window.scene_stadiums.itemText(1)
    assert window.preview_source_info.text()=='Overrides unavailable'
