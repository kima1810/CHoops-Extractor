from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QPushButton
from choops_py.studio.app import Window
from choops_py.studio import services
from choops_py.formats.cdf_backed_iff_writer import name_trailer
from support import iff_fixture


@pytest.mark.gui
def test_uniform_selection_starts_jersey_without_open_iff_or_existing_mesh(qtbot, monkeypatch):
    window = Window();qtbot.addWidget(window)
    window.archive = SimpleNamespace(entries=[dict(index=0, name='uh256.iff')])
    window.refresh_uniform_list();window.scene_uniforms.setCurrentIndex(1)
    calls=[]
    monkeypatch.setattr(window,'preview_jersey',lambda *args:calls.append(args))
    window.select_scene_uniform()
    assert calls[0][0]['uniform_asset_id']==256
    assert calls[0][0]['variant_code']==0
    assert not window.scene_meshes
    assert any(b.text()=='Preview selected jersey' for b in window.findChildren(QPushButton))


@pytest.mark.gui
@pytest.mark.parametrize('overrides',[False,True])
def test_stadium_selector_uses_captured_source_and_reloads_on_toggle(qtbot, monkeypatch, overrides):
    window=Window();qtbot.addWidget(window)
    entry=dict(index=0,name='s256.iff')
    window.archive=SimpleNamespace(entries=[entry])
    selected_archive=SimpleNamespace(entries=[entry]) if overrides else window.archive
    window.refresh_stadium_list();window.scene_stadiums.setCurrentIndex(1)
    monkeypatch.setattr(window,'preview_archive',lambda:selected_archive)
    calls=[]
    monkeypatch.setattr(services,'inspect_stadium_preview',lambda *args:calls.append(args))
    monkeypatch.setattr(window,'run_job',lambda title,work,display,**kwargs:work(None))
    window.preview_stadium()
    assert calls[0][0] is selected_archive and calls[0][1] is entry
    window._direct_stadium_active=True
    window.navigate_to('Models / Courts')
    window.reload_preview_source()
    assert len(calls)==2


@pytest.mark.parametrize('mode,name,all_scenes',[(0,'floor',True),(1,'floor',False),(2,'arena',False)])
def test_stadium_record_resolved_from_selected_archive(tmp_path,monkeypatch,mode,name,all_scenes):
    path=tmp_path/'s256.iff'
    path.write_bytes(iff_fixture([b'floor',b'arena'],[(0xE26C9B5D,[0]),(0xE26C9B5D,[1])])+name_trailer([dict(name='floor',type='SCNE'),dict(name='arena',type='SCNE')]))
    archive=object();entry=dict(index=7,name='s256.iff')
    calls=[]
    monkeypatch.setattr(services,'materialize',lambda a,e:path if a is archive and e is entry else None)
    monkeypatch.setattr(services,'inspect_scene_with_game_layers',lambda *args,**kwargs:calls.append((args,kwargs)))
    services.inspect_stadium_preview(archive,entry,mode)
    assert calls[0][0][0]==path
    assert calls[0][0][2] is archive
    assert calls[0][0][3] is all_scenes
    assert calls[0][1]['record_name']==name


@pytest.mark.gui
def test_shared_source_dropdown_and_pick_only_category_lists(qtbot, monkeypatch):
    window=Window();qtbot.addWidget(window)
    entries=[dict(index=0,name=None),dict(index=1,name='uh258.iff'),
             dict(index=2,name='shoe_1.iff'),dict(index=3,name='s258.iff')]
    base=SimpleNamespace(entries=entries)
    overlay=SimpleNamespace(entries=entries,replacements={1:object(),3:object()})
    window.archive=base
    monkeypatch.setattr(window,'preview_archive',lambda:overlay if window.preview_overrides.isChecked() else base)
    window.refresh_preview_lists()
    for combo in (window.scene_uniforms,window.scene_shoes,window.scene_stadiums):
        assert not combo.isEditable() and combo.count()==2
        combo.setCurrentIndex(1)
    window.preview_source_selector.activated.emit(1)
    assert window.preview_overrides.isChecked()
    assert window.preview_source_selector.currentIndex()==1
    assert '[Override]' in window.scene_uniforms.currentText()
    assert '[Override]' in window.scene_stadiums.currentText()
    assert '[JB fallback]' in window.scene_shoes.currentText()
    assert window.scene_asset_tabs.count()==3
    window.preview_source_selector.activated.emit(0)
    assert not window.preview_overrides.isChecked()
    assert '[Override]' not in window.scene_uniforms.currentText()
    assert window.scene_stadiums.currentData()==3


def test_stock_reference_lookup_skips_unnamed_archive_entries(tmp_path,monkeypatch):
    source=tmp_path/'s258.iff';source.write_bytes(b'')
    reference=tmp_path/'s256.iff';reference.write_bytes(b'')
    entry=dict(index=1,name='s256.iff')
    archive=SimpleNamespace(entries=[dict(index=0,name=None),entry])
    result=dict(meshes=[dict(court_surface=True,vertices=[],batches=[])],images={},warnings=[])
    monkeypatch.setattr(services,'inspect_scene_preview',lambda *args,**kwargs:result)
    monkeypatch.setattr(services,'materialize',lambda a,e:reference)
    monkeypatch.setattr('choops_py.formats.standard_iff.StandardIFF',lambda raw:SimpleNamespace(records=[dict(index=0,type='SCNE',name=None),dict(index=1,type='SCNE',name='floor')]))
    assert services.inspect_scene_with_game_layers(source,0,archive)['meshes']==result['meshes']


@pytest.mark.gui
def test_source_switch_does_not_navigate_from_texture_category(qtbot,monkeypatch):
    window=Window();qtbot.addWidget(window)
    window.navigate_to('Texture Editor')
    window._direct_stadium_active=True
    calls=[]
    monkeypatch.setattr(window,'preview_stadium',lambda:calls.append('stadium'))
    window.reload_preview_source()
    assert calls==[]
    assert window.navigation.currentItem().text(0)=='Texture Editor'
