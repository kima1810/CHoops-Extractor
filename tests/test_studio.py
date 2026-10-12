import pytest
pytestmark = pytest.mark.integration
import os
import uuid
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import pytest
from pathlib import Path
from choops_py.studio.app import Window, Rows, selected
from choops_py.studio.services import extract, JobContext, stage_folder
from choops_py.archive.usrdir_reader import Archive
from choops_py.archive.manifests import OUTPUT
from support import game_fixture, iff_fixture


def test_streaming_cancellation_and_collision(tmp_path):
    source=game_fixture(tmp_path/'game',iff_fixture(records=[(0xa7701f00,[0])]))
    archive=Archive(source)
    job=JobContext()
    job.cancelled.set()
    output=OUTPUT/'temp'/(tmp_path.name+uuid.uuid4().hex)/'cancel'
    result=extract(archive,archive.entries,output,job)
    assert result['status']=='cancelled'
    assert result['completed']==0
    assert not list(output.glob('.extract_*'))
    with pytest.raises(ValueError,match='destination'):
        extract(archive,archive.entries,output)


def test_exclusive_extraction_and_folder_stage(tmp_path):
    source=game_fixture(tmp_path/'game',iff_fixture(records=[(0xa7701f00,[0])]))
    archive=Archive(source)
    out=OUTPUT/'temp'/(tmp_path.name+uuid.uuid4().hex)/'rip'
    result=extract(archive,archive.entries,out)
    assert result['completed']==1
    assert (out/'ua000.iff').read_bytes()==archive.read(archive.entries[0])
    with pytest.raises(ValueError,match='existing'):
        extract(archive,archive.entries,out)
    mod=OUTPUT/'temp'/(tmp_path.name+uuid.uuid4().hex)/'mod'
    assert stage_folder(source,out,mod)['staged']==1
    assert (mod/'source_preconditions.json').exists()


@pytest.mark.gui
def test_qt_game_model_and_navigation(qtbot,tmp_path):
    source=game_fixture(tmp_path/'game',iff_fixture())
    window=Window()
    qtbot.addWidget(window)
    window.show()
    window.open_game(source)
    qtbot.waitUntil(lambda: window.active is None,timeout=10000)
    assert window.archive is not None
    assert window.audio_state.text()=="Audio catalog has not been loaded for this JB."
    assert window.audio_tables["Soundtrack"].model() is None
    assert window.explorer.model().rowCount()==1
    window.search.setText('no matching entry')
    assert window.explorer.model().rowCount()==0
    window.search.setText('ua000')
    assert window.explorer.model().rowCount()==1
    window.explorer.selectRow(0)
    window.inspect_selected()
    qtbot.waitUntil(lambda: window.active is None,timeout=10000)
    assert window.nested.topLevelItemCount()==1
    for i in range(8):
        window.navigation.setCurrentItem(window.navigation.topLevelItem(i))
        assert window.pages.currentIndex()==i
    assert window.audio_tabs.tabText(0)=="Licensed Music"
    assert window.audio_tabs.tabText(1)=="Fight Songs"
    window.close()


@pytest.mark.gui
def test_audio_workspace_separates_licensed_and_fight_tracks(qtbot, monkeypatch):
    from PySide6.QtCore import Qt
    from choops_py.audio_tools import workflow

    audio_catalog = {
        "tracks": [
            {
                "title": "Licensed track",
                "artist": "Artist",
                "bank": "cribmusic",
                "index": 0,
                "seconds": 10,
                "category": "Soundtrack",
                "cover_record": "000",
            },
            {
                "title": "Fight song",
                "artist": "School",
                "bank": "cribmusic",
                "index": 23,
                "seconds": 20,
                "category": "Fight song",
                "cover_record": "021",
            },
        ],
        "soundtrack_count": 1,
        "fight_song_count": 1,
    }
    monkeypatch.setattr(workflow, "catalog", lambda archive, job: audio_catalog)
    window = Window()
    qtbot.addWidget(window)
    window.archive = object()
    window.audio_refresh()
    qtbot.waitUntil(lambda: window.active is None, timeout=10000)
    assert window.audio_tables["Soundtrack"].model().rowCount() == 1
    assert window.audio_tables["Fight song"].model().rowCount() == 1
    assert "1 licensed tracks" in window.audio_state.text()
    assert not (
        window.audio_tables["Soundtrack"]
        .model()
        .flags(window.audio_tables["Soundtrack"].model().index(0, 0))
        & Qt.ItemFlag.ItemIsEditable
    )
    window.close()


def test_roster_redo_and_new_edit_clears_future():
    from support import roster_fixture
    model=roster_fixture()
    model.edit('players',0,'jersey_number',20)
    model.undo()
    assert model.rows['players'][0]['jersey_number']==10
    model.redo()
    assert model.rows['players'][0]['jersey_number']==20
    model.undo()
    model.edit('players',0,'jersey_number',30)
    model.redo()
    assert model.rows['players'][0]['jersey_number']==30


def test_source_precondition_rejects_changed_original(tmp_path):
    from choops_py.archive.build_copy import preflight
    source=game_fixture(tmp_path/'game',iff_fixture(records=[(0xa7701f00,[0])]))
    archive=Archive(source)
    out=OUTPUT/'temp'/(tmp_path.name+uuid.uuid4().hex)/'rip'
    extract(archive,archive.entries,out)
    mod=OUTPUT/'temp'/(tmp_path.name+uuid.uuid4().hex)/'mod'
    stage_folder(source,out,mod)
    part=source/'PS3_GAME'/'USRDIR'/'0A'
    raw=bytearray(part.read_bytes())
    raw[4095]^=1
    part.write_bytes(raw)
    with pytest.raises(ValueError,match='changed'):
        preflight(source,mod)


@pytest.mark.gui
def test_actual_cli_gui_launch():
    import subprocess,sys
    code="from PySide6.QtCore import QTimer; from PySide6.QtWidgets import QApplication; from choops_py.cli import main; app=QApplication([]); QTimer.singleShot(100,app.quit); raise SystemExit(main(['gui']))"
    result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stderr


def test_archive_rejects_toc_overlap(tmp_path):
    import struct
    source=game_fixture(tmp_path/'game',iff_fixture())
    path=source/'PS3_GAME'/'USRDIR'/'0A'
    raw=bytearray(path.read_bytes());struct.pack_into('>I',raw,44,0);path.write_bytes(raw)
    with pytest.raises(ValueError,match='overlaps'):
        Archive(source)


def test_difference_patch_roundtrip_and_rejects_traversal(tmp_path):
    import zipfile,json
    from choops_py.archive.build_copy import preflight
    from choops_py.modding.patch_package import export_patch,import_patch
    source=game_fixture(tmp_path/'game',iff_fixture(records=[(0xa7701f00,[0])]))
    archive=Archive(source)
    work=OUTPUT/'temp'/('patch_'+uuid.uuid4().hex)
    edits=work/'edits';edits.mkdir(parents=True)
    original=archive.read(archive.entries[0]);new=bytearray(original);new[84]^=1
    (edits/'ua000.iff').write_bytes(new)
    stage_folder(source,edits,work/'mod')
    package=work/'mod.chpatch'
    assert export_patch(source,work/'mod',package)['entries']==1
    with zipfile.ZipFile(package) as z:
        assert set(z.namelist())=={'manifest.json','0000.xor'}
        delta=z.read('0000.xor')
        assert sum(b!=0 for b in delta)==1
    import_patch(source,package,work/'imported')
    assert preflight(source,work/'imported')[1][0][1]==bytes(new)
    malicious=work/'bad.chpatch'
    with zipfile.ZipFile(package) as src,zipfile.ZipFile(malicious,'w') as dst:
        for info in src.infolist():dst.writestr(info,src.read(info))
        dst.writestr('../escape',b'x')
    with pytest.raises(ValueError,match='Unexpected'):
        import_patch(source,malicious,work/'blocked')
    assert not (work/'blocked').exists()


def test_cancel_copy_removes_only_owned_staging(tmp_path):
    from choops_py.archive.build_copy import build
    from choops_py.studio.services import Cancelled
    source=game_fixture(tmp_path/'game',iff_fixture(records=[(0xa7701f00,[0])]))
    archive=Archive(source)
    work=OUTPUT/'temp'/('cancel_copy_'+uuid.uuid4().hex)
    extract(archive,archive.entries,work/'edits')
    stage_folder(source,work/'edits',work/'mod')
    output=OUTPUT/'builds'/('cancel_copy_'+uuid.uuid4().hex)
    job=JobContext()
    job.progress=lambda done,total,message:job.cancelled.set()
    with pytest.raises(Cancelled):
        build(source,work/'mod',output,job=job)
    assert not output.exists()
    assert (source/'PS3_GAME'/'USRDIR'/'0A').stat().st_size==4096


@pytest.mark.gui
def test_native_roster_position_edit_and_copy_save(qtbot):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication,QDialog,QComboBox
    from support import roster_fixture
    from choops_py.roster.workflow import save_model
    from choops_py.roster.adapters import load_bytes
    from choops_py.roster.editor_model import EditorModel
    model=roster_fixture();window=Window();qtbot.addWidget(window)
    qapp=QApplication.instance();qapp.setQuitOnLastWindowClosed(False)
    window.show();window.navigation.setCurrentItem(window.navigation.topLevelItem(2));qtbot.wait(10)
    window.display_roster(model);window.roster_views['players'].selectRow(0)
    row_index=selected(window.roster_views['players'])[0]['index']
    def choose():
        dialog=QApplication.activeModalWidget();assert isinstance(dialog,QDialog)
        field=dialog.findChild(QComboBox,'rosterField');field.setCurrentText('position_code')
        value=dialog.findChild(QComboBox,'rosterValue');value.setCurrentIndex(value.findData(4))
        dialog.accept()
    assert window.roster_tabs.tabText(window.roster_tabs.currentIndex())=='Players'
    assert window.active is None
    timer=QTimer(window);timer.setSingleShot(True);timer.timeout.connect(choose);timer.start(100)
    window.edit_roster();timer.stop()
    qtbot.waitUntil(lambda:window.active is None,timeout=10000)
    assert model.rows['players'][row_index]['position_code']==4
    path=OUTPUT/'temp'/('qt_save_'+uuid.uuid4().hex)/'roster.rost'
    save_model(model,path)
    reopened=EditorModel(load_bytes(path.read_bytes()),model.tables)
    assert reopened.rows['players'][row_index]['position']=='C'
    assert sum(a!=b for a,b in zip(model.original,model.data))==1
    window.close()


def test_individual_0a_and_large_raw_inspection(tmp_path):
    from choops_py.studio.services import inspect_asset
    source=game_fixture(tmp_path/'game',iff_fixture())
    assert len(Archive(source/'PS3_GAME'/'USRDIR'/'0A').entries)==1
    path=OUTPUT/'temp'/('large_raw_'+uuid.uuid4().hex)/'large.bin';path.parent.mkdir(parents=True)
    with path.open('wb') as stream:stream.write(b'HEADER');stream.truncate(128*1024*1024+1)
    report=inspect_asset(path)
    assert report['hex'].startswith(b'HEADER') and len(report['hex'])==4096
    assert not report['textures'] and 'limit' in report['warning']
    path.unlink()


@pytest.mark.gui
def test_numeric_archive_columns_sort_as_numbers(qtbot):
    from choops_py.studio.app import table,set_rows
    from PySide6.QtCore import Qt
    view=table();qtbot.addWidget(view)
    proxy=set_rows(view,[{'index':10},{'index':2},{'index':100}],[('index','TOC index')])
    proxy.sort(0,Qt.SortOrder.AscendingOrder)
    assert [proxy.index(i,0).data() for i in range(3)]==['2','10','100']


def test_cross_part_stream_and_patch_preserve_original(tmp_path):
    import struct
    from choops_py.archive.hash_names import hash_name
    from choops_py.archive.importer import stage
    from choops_py.archive.build_copy import build
    source=tmp_path/'game';usr=source/'PS3_GAME'/'USRDIR';usr.mkdir(parents=True)
    left=bytearray(2048);right=bytearray(2048)
    struct.pack_into('>6I',left,0,0xaa00b3bf,512,2,0,1,0)
    for i,name in enumerate(('0A','0B')):
        struct.pack_into('>II8s',left,24+i*16,1,0,(name+'\0\0').encode('utf-16-be'))
    struct.pack_into('>4I',left,56,hash_name('frontend.bin'),3,0,1024)
    left[1536:]=b'X'*512;right[:512]=b'Y'*512
    (usr/'0A').write_bytes(left);(usr/'0B').write_bytes(right)
    archive=Archive(source);entry=archive.entries[0]
    assert b''.join(archive.chunks(entry,127))==b'X'*512+b'Y'*512
    work=OUTPUT/'temp'/('split_patch_'+uuid.uuid4().hex);work.mkdir()
    changed=work/'replacement.bin';changed.write_bytes(b'Z'*512+b'Q'*512)
    stage(work/'mod',changed,'frontend.bin')
    output=OUTPUT/'builds'/('split_patch_'+uuid.uuid4().hex)
    report=build(source,work/'mod',output)
    copied=Archive(output)
    assert copied.read(copied.entries[0])==changed.read_bytes()
    assert archive.read(entry)==b'X'*512+b'Y'*512
    assert report['validation']['all_unpatched_bytes_exact']


def test_cli_interrupt_records_cancelled_export(tmp_path):
    import json
    source=game_fixture(tmp_path/'game',iff_fixture());archive=Archive(source)
    output=OUTPUT/'temp'/('interrupt_'+uuid.uuid4().hex)
    job=JobContext()
    def interrupt(done,total,message):raise KeyboardInterrupt()
    job.progress=interrupt
    with pytest.raises(KeyboardInterrupt):extract(archive,archive.entries,output,job)
    report=json.loads((output/'extraction_manifest.json').read_text())
    assert report['status']=='cancelled' and report['completed']==0
    assert not list(output.glob('.extract_*'))


@pytest.mark.windows
@pytest.mark.skipif(os.name!='nt',reason='Windows legacy path limit')
def test_report_at_deep_windows_path():
    import json
    from choops_py.core.reports import save_json
    base=OUTPUT/'temp';base.mkdir(parents=True,exist_ok=True)
    # Directory stays below the legacy directory limit; the old long temp name did not.
    folder=base/('r'+uuid.uuid4().hex[:8]+'x'*max(0,230-len(str(base.resolve()))-10))
    assert len(str(folder.resolve()))<=230
    output=folder/'state.json'
    save_json(output,{'valid':True})
    assert json.loads(output.read_text())['valid']
    assert not list(folder.glob('.r_*.tmp'))


@pytest.mark.gui
def test_explorer_previews_archive_textures_without_manual_export(qtbot, tmp_path):
    from support import txtr_fixture
    payload = iff_fixture(txtr_fixture(), [(0x5c369069, [0])])
    source = game_fixture(tmp_path / 'preview_game', payload)
    original = (source / 'PS3_GAME' / 'USRDIR' / '0A').read_bytes()
    window = Window()
    qtbot.addWidget(window)
    window.open_game(source)
    qtbot.waitUntil(lambda: window.active is None, timeout=10000)
    window.explorer.selectRow(0)
    window.inspect_selected()
    qtbot.waitUntil(lambda: not window.explorer_image.pixmap().isNull(), timeout=10000)
    assert window.explorer_texture.count() == 1
    assert window.explorer_image._original.width() == 4
    assert window.explorer_image._original.height() == 4
    assert window.explorer_image.pixmap().width() <= window.explorer_image.width()
    assert window.explorer_image.pixmap().height() <= window.explorer_image.height()
    assert window.pages.currentIndex() == 0
    assert (source / 'PS3_GAME' / 'USRDIR' / '0A').read_bytes() == original
    qtbot.waitUntil(lambda: window.active is None, timeout=10000)
    window.display_asset({'path': window.asset_path, 'records': [], 'textures': [], 'hex': b'', 'warning': ''})
    assert window.explorer_image.pixmap().isNull()
    assert not window.explorer_texture.isEnabled()
    assert 'No supported textures' in window.explorer_image.text()
    window.close()


@pytest.mark.gui
def test_alternate_checkboxes_and_opt_in_d1(qtbot,monkeypatch):
    from PySide6.QtWidgets import QDialog,QCheckBox
    from test_roster_semantics import header_roster
    from choops_py.roster.editor_model import EditorModel
    from choops_py.roster.adapters import load_bytes
    import struct
    data,starts=header_roster()
    struct.pack_into('>II',data,starts['uniforms'],(12<<12)|(2<<8),0)
    struct.pack_into('>II',data,starts['uniforms']+8,(13<<12)|(1<<8),0)
    window=Window();qtbot.addWidget(window)
    window.display_roster(EditorModel(load_bytes(bytes(data))))
    window.roster_tabs.setCurrentWidget(window.roster_views['teams'])
    window.roster_views['teams'].selectRow(0)
    def inspect_alternates(dialog):
        boxes=dialog.findChildren(QCheckBox)
        assert [b.text() for b in boxes]==['Alternate 1','Alternate 2','Alternate 3']
        assert boxes[0].isChecked() and boxes[0].isEnabled()
        assert not boxes[1].isChecked() and not boxes[1].isEnabled()
        boxes[0].setChecked(False)
        return QDialog.DialogCode.Accepted
    monkeypatch.setattr(QDialog,'exec',inspect_alternates)
    window.edit_alternate_availability()
    assert len(window.roster.rows['uniforms'])==1
    window.roster_views['teams'].selectRow(0)
    def inspect_conversion(dialog):
        box=dialog.findChildren(QCheckBox)[0]
        assert not box.isChecked()
        return QDialog.DialogCode.Rejected
    monkeypatch.setattr(QDialog,'exec',inspect_conversion)
    window.move_school();window.close()


@pytest.mark.gui
def test_shoe_picker_names_colors_and_scene_display(qtbot):
    window=Window();qtbot.addWidget(window)
    from types import SimpleNamespace
    window.archive=SimpleNamespace(entries=[{'index':0,'name':'shoe_100_00.iff'},{'index':1,'name':'shoe_300_09.iff'}])
    window.refresh_shoe_list()
    assert window.scene_shoes.count()==3
    assert 'Nike' in window.scene_shoes.itemText(1) and 'White' in window.scene_shoes.itemText(1)
    assert 'Adidas' in window.scene_shoes.itemText(2) and 'Black / Black' in window.scene_shoes.itemText(2)
    window.show_scene_preview({'meshes':[],'images':{},'textures':[],'warnings':[]},Path('shoe_mesh.iff'))
    assert window.scene_parts.count()==1
    window.close()
