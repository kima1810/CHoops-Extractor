"""Conservative school membership writes and scoped shoe-brand propagation."""

import struct
from .shoes import FIELDS, STYLE_COUNTS, COLOR_COUNTS
from .schema import ROSTER_SLOT_COUNT
from ..formats.binary import Binary
from ..core.errors import ToolError

TEAM_ROSTER_COUNT = 0x188
TEAM_ROSTER_SLOTS = 0x6C
CAPACITY = ROSTER_SLOT_COUNT


def player_schools(model, index):
    model.row_offset("players", index)
    return [
        row["index"]
        for row in model.rows.get("teams", [])
        if index in row["roster_slots"]
    ]


def checked_members(model, index):
    model.row_offset("teams", index)
    row = model.rows["teams"][index]
    slots = row["roster_slots"]
    count = Binary(model.data).u16(row["row_offset"] + TEAM_ROSTER_COUNT)
    members = [p for p in slots if p is not None]
    if (
        count > CAPACITY
        or count != len(members)
        or slots[:count] != members
        or any(p is not None for p in slots[count:])
    ):
        raise ToolError(
            "school_roster_layout_unsupported",
            "Roster slots/count are inconsistent or not contiguous; no changes made",
        )
    if len(set(members)) != len(members):
        raise ToolError(
            "ambiguous_school_roster", "Duplicate player links are not writable"
        )
    return members


def write_members(model, index, members):
    offset = model.row_offset("teams", index)
    if len(members) > CAPACITY:
        raise ToolError("school_roster_full", "School roster has no free slot")
    if len(set(members)) != len(members):
        raise ToolError(
            "ambiguous_school_roster", "Duplicate player links are unsupported"
        )
    for slot in range(CAPACITY):
        field = offset + TEAM_ROSTER_SLOTS + slot * 4
        delta = (
            model.row_offset("players", members[slot]) + 0x11 - field
            if slot < len(members)
            else 0
        )
        struct.pack_into(">i", model.data, field, delta)
    struct.pack_into(">H", model.data, offset + TEAM_ROSTER_COUNT, len(members))


def transaction(model, record, operation):
    before = bytes(model.data)
    edits = list(model.edits)
    history = list(model.history)
    redo = list(model.redo_history)
    try:
        operation()
        if not model.validate()["valid"]:
            raise ToolError("roster_validation_failed", "Assignment failed validation")
    except Exception:
        model.data = bytearray(before)
        model.edits = edits
        model.history = history
        model.redo_history = redo
        model.reload()
        raise
    model.history = history
    model.redo_history = redo
    model.edits = edits
    if bytes(model.data) != before:
        model.history.append((before, edits))
        model.redo_history = []
        model.edits.append(record)


def move_player(model, player_index, school_index):
    player_index = model.integer(player_index)
    model.row_offset("players", player_index)
    # Unknown/overflow rosters can hide additional owners. Refuse transfers
    # rather than assuming a player is unique or unassigned.
    for school in model.rows.get("teams", []):
        checked_members(model, school["index"])
    schools = player_schools(model, player_index)
    if len(schools) > 1:
        raise ToolError(
            "shared_player_assignment",
            "Player is shared by multiple school rosters; no automatic transfer is safe",
        )
    old = schools[0] if schools else None
    if school_index is not None:
        school_index = model.integer(school_index)
        model.row_offset("teams", school_index)
    if old == school_index:
        return
    groups = {}
    if old is not None:
        groups[old] = checked_members(model, old)
        groups[old].remove(player_index)
    if school_index is not None:
        groups[school_index] = checked_members(model, school_index)
        if len(groups[school_index]) >= CAPACITY:
            raise ToolError("school_roster_full", "Destination school roster is full")
        groups[school_index].append(player_index)

    def apply():
        for index, members in groups.items():
            write_members(model, index, members)
        model.reload()
        if player_schools(model, player_index) != (
            [school_index] if school_index is not None else []
        ):
            raise ToolError(
                "school_assignment_mismatch", "Assignment did not round-trip"
            )

    transaction(
        model,
        dict(
            table="players",
            index=player_index,
            field="school_assignment",
            old=old,
            value=school_index,
        ),
        apply,
    )


def school_shoes(model, index, values):
    model.row_offset("teams", index)
    for school in model.rows.get("teams", []):
        checked_members(model, school["index"])
    members = checked_members(model, index)
    if any(player_schools(model, p) != [index] for p in members):
        raise ToolError(
            "shared_player_shoes",
            "School has shared player records; brand changes cannot be restricted to this school",
        )
    brand = model.integer(values["shoe_brand_code"])
    if brand not in STYLE_COUNTS:
        raise ToolError("invalid_shoe_assignment", "Choose a supported shoe brand")

    def apply():
        model.edit_shoes("teams", index, **values)
        for player in members:
            row = model.rows["players"][player]
            new = {key: row[key] for key in FIELDS["players"]}
            new["shoe_brand_code"] = brand
            new["shoe_style_code"] = (
                new["shoe_style_code"]
                if new["shoe_style_code"] < STYLE_COUNTS[brand]
                else 0
            )
            for key in ("home_shoe_color_code", "away_shoe_color_code"):
                if new[key] >= COLOR_COUNTS[brand]:
                    new[key] = 0
            model.edit_shoes("players", player, **new)

    transaction(
        model,
        dict(table="teams", index=index, field="school_shoe_brand", value=values),
        apply,
    )


def roster_slot(model, school_index, slot, player_index):
    school_index = model.integer(school_index)
    model.row_offset("teams", school_index)
    slot = model.integer(slot)
    if not 0 <= slot < CAPACITY:
        raise ToolError("roster_slot_out_of_range", "Choose slot 1–18")
    members = checked_members(model, school_index)
    if slot > len(members):
        raise ToolError(
            "school_roster_gap",
            "Use the first empty slot; active slots must remain contiguous",
        )
    old = members[slot] if slot < len(members) else None
    if player_index is not None:
        player_index = model.integer(player_index)
        model.row_offset("players", player_index)
    if old == player_index:
        return

    def apply():
        if player_index in members:
            if slot >= len(members):
                raise ToolError(
                    "school_roster_gap", "Choose an active slot to reorder players"
                )
            other = members.index(player_index)
            members[other], members[slot] = members[slot], members[other]
            write_members(model, school_index, members)
        else:
            if old is not None:
                move_player(model, old, None)
            if player_index is not None:
                move_player(model, player_index, school_index)
                current = checked_members(model, school_index)
                current.remove(player_index)
                current.insert(slot, player_index)
                write_members(model, school_index, current)

    transaction(
        model,
        dict(
            table="teams",
            index=school_index,
            field="school_roster_slot",
            slot=slot,
            old=old,
            value=player_index,
        ),
        apply,
    )
