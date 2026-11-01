import struct
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QPushButton
from support import WorkspaceTest, roster_fixture, iff_fixture
from choops_py.roster.adapters import load_bytes
from choops_py.roster.editor_model import EditorModel
from choops_py.roster.workflow import export_userdata, export_game_roster
from choops_py.core.errors import ToolError
from choops_py.studio.app import Window


class RosterExportTests(WorkspaceTest):
    def test_external_iff_exports_userdata_and_iff_without_source_changes(self):
        original=roster_fixture()
        source=load_bytes(iff_fixture([original.original],[(0xc61649b2,[0])],compressed=True,padding=128))
        model=EditorModel(source,original.tables)
        model.edit('players',0,'jersey_number',42)
        output=self.work/'USERDATA'
        export_userdata(model,output)
        encoded=output.read_bytes()
        self.assertEqual(struct.unpack_from('>I',encoded)[0],len(encoded)-4)
        self.assertEqual(load_bytes(encoded).payload,bytes(model.data))
        self.assertEqual(load_bytes(encoded).kind,'userdata')
        iff=self.work/'edited.iff'
        export_game_roster(model,source.original,iff)
        self.assertEqual(load_bytes(iff.read_bytes()).payload,bytes(model.data))
        self.assertEqual(source.payload,original.original)

    def test_invalid_roster_cannot_export_savedata(self):
        model=roster_fixture()
        struct.pack_into('>i',model.data,0x40+0x10,0x7fffffff)
        output=self.work/'USERDATA'
        with self.assertRaises(ToolError):export_userdata(model,output)
        self.assertFalse(output.exists())


@pytest.mark.gui
def test_explicit_roster_sources_do_not_follow_preview_toggle(qtbot,monkeypatch):
    window=Window();qtbot.addWidget(window)
    entry=dict(index=0,name='roster_english.iff')
    base=SimpleNamespace(entries=[entry])
    overrides=SimpleNamespace(entries=[entry],replacements={0:object()})
    window.archive=base
    choices=[];jobs=[]
    monkeypatch.setattr(window,'preview_archive',lambda use_overrides=None:choices.append(use_overrides) or (overrides if use_overrides else base))
    monkeypatch.setattr(window,'run_job',lambda *args:jobs.append(args))
    window.load_game_roster()
    window.load_game_roster(True)
    assert choices==[False,True]
    assert [job[0] for job in jobs]==['Load source JB roster','Load overrides roster']
    errors=[]
    monkeypatch.setattr(window,'show_error',errors.append)
    overrides.replacements={}
    window.load_game_roster(True)
    assert len(jobs)==2 and 'no roster_english.iff replacement' in errors[0]
    buttons={button.text() for button in window.findChildren(QPushButton)}
    assert {'Open roster / Legacy save…','Load from JB','Load from overrides'}<=buttons


@pytest.mark.gui
def test_external_iff_export_uses_its_original_template_without_jb(qtbot,monkeypatch,tmp_path):
    from choops_py.studio import app
    window=Window();qtbot.addWidget(window)
    window.roster=SimpleNamespace(source=SimpleNamespace(kind='standard-iff',original=b'template'))
    monkeypatch.setattr(app.QFileDialog,'getSaveFileName',lambda *args:(str(tmp_path/'edited.iff'),''))
    captured=[]
    monkeypatch.setattr(window,'run_job',lambda *args:captured.append(args))
    monkeypatch.setattr('choops_py.roster.workflow.export_game_roster',lambda model,template,output:(template,output))
    window.export_game_roster()
    assert captured[0][1](None)==(b'template',str(tmp_path/'edited.iff'))
