import pytest
from PySide6.QtCore import Qt,QItemSelectionModel
from PySide6.QtWidgets import QSpinBox,QApplication
from choops_py.studio.app import Window
from support import roster_fixture

pytestmark=pytest.mark.gui


def test_comparison_selection_survives_filter_and_sort(qtbot):
    from choops_py.studio.roster_bulk import ChangeReview
    changes = [dict(table='players', index=i, school=school, record=name,
                    field='weight_lbs', slot=None, old=180, value=190)
               for i, (school, name) in enumerate((('Alpha', 'Zed'), ('Beta', 'Amy'), ('Alpha', 'Ben')))]
    dialog = ChangeReview(None, changes);qtbot.addWidget(dialog)
    dialog.filter('Alpha');dialog.mark(Qt.CheckState.Checked)
    assert dialog.table_model.checked == {0, 2}
    dialog.filter('Beta');dialog.mark(Qt.CheckState.Checked)
    dialog.proxy.sort(0, Qt.SortOrder.DescendingOrder)
    dialog.mark(Qt.CheckState.Unchecked)
    assert dialog.table_model.checked == {0, 2}
    dialog.filter('');assert dialog.proxy.rowCount() == 3


def test_rating_double_click_uses_inline_box(qtbot):
    window=Window();qtbot.addWidget(window);window.show()
    model=roster_fixture();window.display_roster(model);window.roster_views['players'].selectRow(0)
    panel=window.player_details;panel.setCurrentIndex(1)
    item=panel.ratings.topLevelItem(0);panel.ratings.editItem(item,1)
    editor=panel.ratings.findChild(QSpinBox)
    assert editor is not None
    editor.setValue(88);qtbot.keyClick(editor,Qt.Key.Key_Return)
    qtbot.waitUntil(lambda:model.rows['players'][0]['attribute_ratings'][0]==88)
    assert panel.player_index==0


def test_rating_paste_remains_available_for_multiple_players(qtbot):
    window=Window();qtbot.addWidget(window);model=roster_fixture();window.display_roster(model)
    view=window.roster_views['players'];view.selectRow(0)
    model.edit('players',0,'attribute_ratings',91,slot=0)
    window.player_details.copy_ratings()
    assert QApplication.clipboard().text()
    for i in range(view.model().rowCount()):
        view.selectionModel().select(view.model().index(i,0),QItemSelectionModel.SelectionFlag.Select|QItemSelectionModel.SelectionFlag.Rows)
    assert window.player_details.isEnabled()
    window.player_details.paste_ratings()
    qtbot.waitUntil(lambda:window.active is None)
    assert model.rows['players'][1]['attribute_ratings'][0]==91


def test_source_toggle_reloads_scene_and_explorer_textures(qtbot,monkeypatch,tmp_path):
    window=Window();qtbot.addWidget(window)
    window.asset_path=tmp_path/'s000.iff';window.scene_source=window.asset_path
    window._scene_record_index=2;window._jersey_preview_row=None
    called=[]
    monkeypatch.setattr(window,'run_job',lambda title,*args,**kwargs:called.append(title))
    window.navigate_to('Models / Courts')
    window.preview_overrides.setChecked(True)
    assert called==['Reload scene from selected preview source']
    window.navigate_to('Texture Editor')
    window._scene_record_index=None;window.preview_overrides.setChecked(False)
    assert called[-1]=='Reload textures from selected preview source'
