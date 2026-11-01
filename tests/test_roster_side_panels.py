import pytest
from PySide6.QtWidgets import QPushButton, QInputDialog
from support import roster_fixture
from choops_py.studio.app import Window
from test_roster_semantics import header_roster
from choops_py.roster.editor_model import EditorModel
from choops_py.roster.adapters import load_bytes

pytestmark = pytest.mark.gui


def test_each_category_has_side_editor_and_removed_toolbar_actions(qtbot):
    window = Window()
    qtbot.addWidget(window)
    data, _ = header_roster()
    window.display_roster(EditorModel(load_bytes(bytes(data))))
    for name, panel in window.record_panels.items():
        view = window.roster_views[name]
        window.roster_tabs.setCurrentWidget(view)
        view.selectRow(0)
        assert window.roster_detail_stack.currentWidget() is panel and panel.isEnabled()
        assert panel.general.topLevelItemCount() > 0
    texts = [b.text() for b in window.findChildren(QPushButton)]
    assert (
        "Edit selected…" not in texts
        and "Team palette…" not in texts
        and "Shoes…" not in texts
    )
    teams = window.record_panels["teams"]
    assert [teams.tabText(i) for i in range(teams.count())] == [
        "School",
        "References",
        "Players",
        "Palette",
        "Shoes",
        "Jersey",
    ]
    assert teams.palette_view.topLevelItemCount() == 31


def test_palette_and_uniform_fields_edit_through_panels(qtbot, monkeypatch):
    window = Window()
    qtbot.addWidget(window)
    data, _ = header_roster()
    model = EditorModel(load_bytes(bytes(data)))
    window.display_roster(model)
    window.roster_tabs.setCurrentWidget(window.roster_views["teams"])
    window.roster_views["teams"].selectRow(0)
    panel = window.record_panels["teams"]
    monkeypatch.setattr(window, "pick_rgba", lambda *args: "#123456FF")
    panel.edit_item(panel.palette_view.topLevelItem(2), 1)
    assert model.rows["teams"][0]["palette_colors"][2] == "#123456FF"
    assert panel.index == 0
    window.roster_tabs.setCurrentWidget(window.roster_views["uniforms"])
    window.roster_views["uniforms"].selectRow(0)
    panel = window.record_panels["uniforms"]
    panel.apply("jersey_shape_code", 4)
    assert model.rows["uniforms"][0]["jersey_shape_code"] == 4


def test_coach_string_edit_preserves_old_functionality_and_selection(
    qtbot, monkeypatch
):
    import struct

    model = roster_fixture()
    data = bytearray(model.data)
    field = model.row_offset("coaches", 0) + 0x14
    struct.pack_into(">i", data, field, 0xE00 - field)
    data[0xE00:0xE0C] = "Coach".encode("utf-16-le") + b"\0\0"
    model = EditorModel(load_bytes(bytes(data)), model.tables)
    window = Window()
    qtbot.addWidget(window)
    window.display_roster(model)
    window.roster_tabs.setCurrentWidget(window.roster_views["coaches"])
    window.roster_views["coaches"].selectRow(0)
    panel = window.record_panels["coaches"]
    monkeypatch.setattr(
        'choops_py.studio.text_edit.edit_roster_text', lambda *args, **kwargs: ("Smith", True)
    )
    item = next(
        panel.general.topLevelItem(i)
        for i in range(panel.general.topLevelItemCount())
        if panel.general.topLevelItem(i).text(0) == "Coach Name"
    )
    panel.edit_item(item, 1)
    assert model.rows["coaches"][0]["coach_name"] == "Smith" and panel.index == 0


def test_jersey_side_panel_all_numbers_and_preview_only_selection(qtbot,monkeypatch):
    from choops_py.studio.roster_panels import JerseyTab
    window=Window();qtbot.addWidget(window)
    data,_=header_roster();model=EditorModel(load_bytes(bytes(data)))
    window.display_roster(model);window.archive=object()
    panel=JerseyTab(window);qtbot.addWidget(panel)
    assert [panel.number.itemData(i) for i in range(1,102)]==list(range(101))
    panel.player_index=0;panel.uniform.addItem('Home',dict(uniform_asset_id=256,variant_code=0,jersey_shape_code=0))
    captured=[];monkeypatch.setattr(window,'preview_jersey',lambda *args:captured.append(args))
    panel.number.setCurrentIndex(panel.number.findData(99));panel.preview()
    assert captured[-1][0]['preview_number']==99 and captured[-1][0]['preview_player_index'] is None
    assert captured[-1][0]['preview_name']=='Reborn'
    panel.number.setCurrentIndex(0);panel.preview()
    assert captured[-1][0]['preview_player_index']==0
    assert captured[-1][0]['preview_number']==model.rows['players'][0]['jersey_number']
