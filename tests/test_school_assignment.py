import struct
import pytest
from support import roster_fixture
from choops_py.roster.editor_model import EditorModel
from choops_py.roster.adapters import load_bytes
from choops_py.roster.membership import write_members, player_schools
from choops_py.core.errors import ToolError


def model_fixture():
    old = roster_fixture()
    tables = dict(old.tables)
    tables["players"] = (0x40, 3, 308)
    model = EditorModel(load_bytes(bytes(old.data)), tables)
    write_members(model, 0, [0, 1])
    write_members(model, 1, [2])
    model.reload()
    return model


def test_transfer_row_zero_updates_both_counts_and_preserves_players():
    model = model_fixture()
    before = bytes(model.data)
    players = before[0x40 : 0x40 + 3 * 308]
    model.move_player_to_school(0, 1)
    assert player_schools(model, 0) == [1]
    assert model.rows["teams"][0]["roster_slots"][:2] == [1, None]
    assert model.rows["teams"][1]["roster_slots"][:2] == [2, 0]
    assert bytes(model.data)[0x40 : 0x40 + 3 * 308] == players
    assert len(model.history) == 1
    reopened = EditorModel(load_bytes(bytes(model.data)), model.tables)
    assert player_schools(reopened, 0) == [1]
    model.undo()
    assert bytes(model.data) == before
    model.redo()
    assert player_schools(model, 0) == [1]


def test_inactive_row_zero_link_is_empty_but_active_one_is_real():
    model = model_fixture()
    offset = model.row_offset("teams", 1)
    field = offset + 0x6C + 4
    struct.pack_into(
        ">i", model.data, field, model.row_offset("players", 0) + 17 - field
    )
    model.reload()
    assert model.rows["teams"][1]["roster_slots"][1] is None
    struct.pack_into(">H", model.data, offset + 0x188, 2)
    model.reload()
    assert model.rows["teams"][1]["roster_slots"][1] == 0


def test_inconsistent_or_shared_links_refuse_without_mutation():
    model = model_fixture()
    write_members(model, 1, [0, 2])
    model.reload()
    before = bytes(model.data)
    with pytest.raises(ToolError, match="shared"):
        model.move_player_to_school(0, None)
    assert bytes(model.data) == before
    model = model_fixture()
    struct.pack_into(">H", model.data, model.row_offset("teams", 1) + 0x188, 19)
    model.reload()
    before = bytes(model.data)
    with pytest.raises(ToolError):
        model.move_player_to_school(0, 1)
    assert bytes(model.data) == before


def test_roster_slot_swap_and_removal_keep_dense_membership():
    model = model_fixture()
    before = bytes(model.data)
    model.edit_school_roster_slot(0, 0, 1)
    assert model.rows["teams"][0]["roster_slots"][:2] == [1, 0]
    model.undo()
    assert bytes(model.data) == before
    model.edit_school_roster_slot(0, 0, None)
    assert model.rows["teams"][0]["roster_slots"][0] == 1
    assert player_schools(model, 0) == []


def test_school_brand_propagates_only_to_its_roster_in_one_undo():
    model = model_fixture()
    model.edit_shoes("players", 0, 1, 2, 15, 14)
    model.edit_shoes("players", 1, 1, 1, 3, 4)
    model.edit_shoes("players", 2, 1, 2, 5, 6)
    before = bytes(model.data)
    other = dict(model.rows["players"][2])
    history = len(model.history)
    model.edit_school_shoes(
        0,
        shoe_brand_code=0,
        shoe_style_code=0,
        home_shoe_color_code=0,
        away_shoe_color_code=1,
    )
    assert [model.rows["players"][i]["shoe_brand_code"] for i in (0, 1)] == [0, 0]
    assert model.rows["players"][0]["shoe_style_code"] == 0
    assert model.rows["players"][0]["home_shoe_color_code"] == 0
    assert model.rows["players"][2] == other
    assert len(model.history) == history + 1
    model.undo()
    assert bytes(model.data) == before


def test_shared_roster_brand_propagation_is_blocked_atomically():
    model = model_fixture()
    write_members(model, 1, [0, 2])
    model.reload()
    before = bytes(model.data)
    with pytest.raises(ToolError):
        model.edit_school_shoes(
            0,
            shoe_brand_code=1,
            shoe_style_code=0,
            home_shoe_color_code=0,
            away_shoe_color_code=1,
        )
    assert bytes(model.data) == before


def test_eighteen_member_brand_scope_and_full_destination_guard():
    model = EditorModel(
        load_bytes(bytes(0x4000)),
        {"players": (0x100, 20, 308), "teams": (0x2000, 2, 704)},
    )
    write_members(model, 0, list(range(18)))
    write_members(model, 1, [18])
    model.reload()
    before = bytes(model.data)
    with pytest.raises(ToolError, match="full"):
        model.move_player_to_school(18, 0)
    assert bytes(model.data) == before
    model.edit_school_shoes(
        0,
        shoe_brand_code=3,
        shoe_style_code=0,
        home_shoe_color_code=0,
        away_shoe_color_code=1,
    )
    assert all(model.rows["players"][i]["shoe_brand_code"] == 3 for i in range(18))
    assert (
        model.rows["players"][18]["shoe_brand_code"] == 0
        and model.rows["players"][19]["shoe_brand_code"] == 0
    )
    assert len(model.history) == 1
    model.undo()
    assert bytes(model.data) == before
