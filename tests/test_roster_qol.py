import struct

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

from support import roster_fixture
from choops_py.roster.presentation import height_inches, height_text
from choops_py.studio.app import Window, Rows


def test_height_and_position_display_keep_numeric_sort_values():
    rows = Rows(
        [{"height_inches": 75, "position_code": 2}],
        [("height_inches", "Height"), ("position_code", "Position")],
    )
    assert rows.data(rows.index(0, 0)) == "6 ft 3 in"
    assert rows.data(rows.index(0, 0), Qt.ItemDataRole.UserRole) == 75
    assert rows.data(rows.index(0, 1)) == "SF"
    assert height_inches(height_text(75)) == 75
    with pytest.raises(ValueError):
        height_inches("6 ft 12 in")


def test_scholarship_preserves_weight_and_all_neighboring_flags():
    model = roster_fixture()
    offset = model.row_offset("players", 0) + 0x9C
    struct.pack_into(">I", model.data, offset, 0x356AB789)
    model.reload()
    before = bytes(model.data)
    weight = model.rows["players"][0]["weight_lbs"]
    model.edit("players", 0, "scholarship_status", 1)
    expected = bytearray(before)
    struct.pack_into(">I", expected, offset, 0xB56AB789)
    assert bytes(model.data) == bytes(expected)
    assert model.rows["players"][0]["weight_lbs"] == weight
    model.undo()
    assert bytes(model.data) == before
    model.redo()
    assert model.rows["players"][0]["scholarship_status"] == 1


@pytest.mark.gui
def test_player_details_visible_without_properties_button_and_editable_scholarship(
    qtbot,
):
    window = Window()
    qtbot.addWidget(window)
    model = roster_fixture()
    window.display_roster(model)
    window.roster_views["players"].selectRow(0)
    panel = window.player_details
    assert panel.isEnabled()
    assert [panel.tabText(i) for i in range(panel.count())] == [
        "Player",
        "Ratings",
        "Scholarship",
        "Shoes",
        "Jersey",
        "School",
    ]
    assert panel.details.topLevelItem(3).text(1) == "6 ft 0 in"
    assert panel.details.topLevelItem(4).text(1) == "PG"
    texts = [button.text() for button in window.findChildren(QPushButton)]
    assert not any("â" in text for text in texts)
    for removed in (
        "Player properties",
        "Give school independent assets",
        "Give schools five jerseys",
        "Add alternate",
        "Enable alternates",
        "convert to D1",
    ):
        assert not any(removed.lower() in text.lower() for text in texts)
    index = panel.player_index
    panel.status.setCurrentIndex(panel.status.findData(1))
    next(
        b
        for b in panel.findChildren(QPushButton)
        if b.text() == "Apply scholarship status"
    ).click()
    assert model.rows["players"][index]["scholarship_status"] == 1
    assert panel.player_index == index
    props = {
        panel.details.topLevelItem(i).text(0): panel.details.topLevelItem(i).text(1)
        for i in range(panel.details.topLevelItemCount())
    }
    assert props["Away Sock Color"] in ("Black", "White")
    assert props["Left Arm Band"] == "None"
    assert window.roster_views["schools"] is window.roster_views["teams"]


@pytest.mark.gui
def test_duplicate_equipment_captions_do_not_change_selected_code(qtbot, monkeypatch):
    from PySide6.QtWidgets import QInputDialog

    model = roster_fixture()
    model.edit("players", 0, "right_arm_band_code", 11)
    window = Window()
    qtbot.addWidget(window)
    window.display_roster(model)
    window.roster_views["players"].selectRow(0)
    panel = window.player_details
    item = next(
        panel.details.topLevelItem(i)
        for i in range(panel.details.topLevelItemCount())
        if panel.details.topLevelItem(i).text(0) == "Right Arm Band"
    )
    before = bytes(model.data)

    def choose_current(*args, **kwargs):
        labels = args[3]
        assert len(set(labels)) == len(labels)
        return labels[args[4]], True

    monkeypatch.setattr(QInputDialog, "getItem", choose_current)
    panel.edit_item(item, 1)
    assert bytes(model.data) == before
