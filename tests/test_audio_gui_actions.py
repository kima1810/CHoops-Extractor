"""Regression checks for preview navigation and real audio action routing."""
from pathlib import Path

import pytest

from choops_py.studio.app import Window, set_rows

pytestmark = pytest.mark.gui


@pytest.mark.parametrize('kind', ['scene', 'shoes'])
def test_model_preview_actions_open_models_after_audio_insertion(qtbot, monkeypatch, kind):
    window = Window()
    qtbot.addWidget(window)
    if kind == 'scene':
        window.asset_path = Path('synthetic.scne')
        monkeypatch.setattr(window, 'run_job', lambda *args, **kwargs: None)
        window.inspect_scene()
    else:
        from types import SimpleNamespace
        window.archive = SimpleNamespace(entries=[{'index': 0}])
        window.scene_shoes.addItem('Synthetic shoe', 0)
        window.scene_shoes.setCurrentIndex(window.scene_shoes.count() - 1)
        monkeypatch.setattr(window, 'show_scene_preview', lambda *args: None)
        monkeypatch.setattr(window, 'run_job', lambda label, work, callback, **kwargs: callback((Path('shoe.iff'), {})))
        window.preview_shoes()
    assert window.navigation.currentItem().text(0) == 'Models / Courts'
    assert window.pages.currentIndex() == window.navigation.indexOfTopLevelItem(window.navigation.currentItem())


def test_cover_export_uses_fight_song_shared_record(qtbot, monkeypatch, tmp_path):
    from choops_py.audio_tools import workflow
    window = Window()
    qtbot.addWidget(window)
    archive = object()
    window.archive = archive
    row = dict(title='Fight song', category='Fight song', cover_record='021', bank='cribmusic', index=10)
    set_rows(window.audio_tables['Fight song'], [row], [('title', 'Title')])
    window.audio_tabs.setCurrentIndex(1)
    window.audio_tables['Fight song'].selectRow(0)
    output = tmp_path / 'cover.dds'
    monkeypatch.setattr(window, 'audio_output_path', lambda *args: output)
    calls = []
    monkeypatch.setattr(workflow, 'export_cover', lambda *args: calls.append(args) or {})
    monkeypatch.setattr(window, 'run_job', lambda label, work, **kwargs: work(None))
    window.audio_export_cover()
    assert calls == [(archive, '021', output)]


def test_cancelled_audio_output_dialog_starts_no_job(qtbot, monkeypatch):
    window = Window()
    qtbot.addWidget(window)
    window.archive = object()
    monkeypatch.setattr(window, 'audio_output_path', lambda *args: None)
    def unexpected(*args, **kwargs):
        pytest.fail('Cancelled output choice must not start audio export')
    monkeypatch.setattr(window, 'run_job', unexpected)
    window.audio_export_rows([dict(category='Soundtrack')])
