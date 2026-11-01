"""Source-bound CSV changes, atomic rating paste and conservative roster comparison."""

import csv
import io
import json
from collections import defaultdict

from ..archive.manifests import digest
from .schema import EDITABLE, REFERENCES, RATING_COUNT, TENDENCY_NAMES, CSV_GAME_FIELDS

LIST_FIELDS = {"attribute_ratings", "shot_tendencies", "palette_colors"}
CSV_COLUMNS = ("source_sha256", "table", "index", "school", "record", "field", "slot", "original", "value")


def require_college(model):
    if hasattr(model,'game'):
        raise ValueError('NBA bulk CSV/comparison is not established; use the NBA side editor or source-bound roster JSON patches')


def label(row):
    return next((row[k] for k in ("display_name", "school_name", "conference_name", "coach_name", "arena_name") if row.get(k)), f"Record {row['index']}")


def school_labels(model):
    owners = defaultdict(list)
    for school in model.rows.get("teams", []):
        for index in school.get("roster_slots", []):
            if index is not None:
                owners[index].append(school["school_name"])
    return {index: " / ".join(names) for index, names in owners.items()}


def cells(model):
    for table, rows in model.rows.items():
        for row in rows:
            fields=EDITABLE.get(table, ())
            if table=='teams' and 'conference_index' not in fields:fields=(*fields,'conference_index')
            for field in fields:
                if field not in CSV_GAME_FIELDS.get(table, ()) or field not in row or field == "roster_slots":
                    continue
                value = row[field]
                if field in LIST_FIELDS:
                    for slot, item in enumerate(value):
                        yield table, row, field, slot, item
                else:
                    yield table, row, field, None, value


def export_csv(model):
    require_college(model)
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, CSV_COLUMNS)
    writer.writeheader()
    owners = school_labels(model)
    source = digest(model.source.original)
    for table, row, field, slot, value in cells(model):
        encoded = json.dumps(value, ensure_ascii=False)
        writer.writerow(dict(source_sha256=source, table=table, index=row["index"], school=owners.get(row["index"], "") if table == "players" else row.get("school_name", ""), record=label(row), field=field, slot="" if slot is None else slot, original=encoded, value=encoded))
    return output.getvalue()


def csv_changes(model, text):
    require_college(model)
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    if tuple(reader.fieldnames or ()) != CSV_COLUMNS:
        raise ValueError("Use a CSV exported by this roster editor; columns differ")
    changes = []
    seen = set()
    source_hash=digest(model.source.original)
    for line, row in enumerate(reader, 2):
        if row["source_sha256"] != source_hash:
            raise ValueError(f"CSV line {line}: different source roster; use Compare instead")
        table, field = row["table"], row["field"]
        index = int(row["index"])
        slot = int(row["slot"]) if row["slot"] else None
        model.row_offset(table, index)
        key = (table, index, field, slot)
        if key in seen:
            raise ValueError(f"CSV line {line}: duplicate field")
        seen.add(key)
        if (field not in EDITABLE.get(table, ()) and not (table=='teams' and field=='conference_index')) or field == "roster_slots":
            raise ValueError(f"CSV line {line}: unsupported field")
        if field not in CSV_GAME_FIELDS.get(table, ()):
            raise ValueError(f"CSV line {line}: unsupported field")
        original, value = json.loads(row["original"]), json.loads(row["value"])
        current = model.rows[table][index][field]
        if field in LIST_FIELDS:
            if slot is None or not 0 <= slot < len(current):
                raise ValueError(f"CSV line {line}: invalid channel")
            current = current[slot]
        elif slot is not None:
            raise ValueError(f"CSV line {line}: unexpected channel")
        # JSON arrays/objects and booleans must not be coerced into names or IDs.
        expected = str if isinstance(current, str) else int
        allowed = (int, type(None)) if current is None else (expected,)
        if type(value) not in allowed or type(original) not in allowed:
            raise ValueError(f"CSV line {line}: expected a JSON {expected.__name__} value")
        if original == value:
            continue
        if current != original:
            raise ValueError(f"CSV line {line}: field changed since export")
        changes.append(dict(table=table, index=index, field=field, slot=slot, old=current, value=value, record=label(model.rows[table][index])))
    return changes


def apply_changes(model, changes):
    require_college(model)
    """Validate the entire selection, rollback on failure, and retain replayable edits."""
    before, history, redo, edits = bytes(model.data), list(model.history), list(model.redo_history), list(model.edits)
    from .shoes import FIELDS
    shoes=defaultdict(dict);deferred=[]
    try:
        for change in changes:
            current=model.rows[change['table']][change['index']][change['field']]
            if change['slot'] is not None:current=current[change['slot']]
            if current!=change['old']:raise ValueError('Selected change is stale; compare/export again')
        model._batch_writes=True
        for change in changes:
            table, index, field, slot = (change[k] for k in ("table", "index", "field", "slot"))
            current = model.rows[table][index][field]
            if slot is not None:
                current = current[slot]
            if current != change["old"]:
                raise ValueError("Selected change is stale; compare/export again")
            if field in FIELDS.get(table,{}):
                shoes[table,index][field]=change['value']
            elif field == "conference_index":
                deferred.append(change)
            else:
                model.edit(table, index, field, change["value"], slot)
        model._batch_writes=False
        model.reload()
        for (table,index),updates in shoes.items():
            values={field:model.rows[table][index][field] for field in FIELDS[table]};values.update(updates)
            if table=='teams':model.edit_school_shoes(index,**values)
            else:model.edit_shoes(table,index,**values)
        for change in deferred:model.move_team_to_conference(change['index'],change['value'])
        if not model.validate()["valid"]:
            raise ValueError("Imported edits fail roster validation")
        for change in changes:
            value=model.rows[change['table']][change['index']][change['field']]
            if change['slot'] is not None:value=value[change['slot']]
            if value!=change['value']:raise ValueError('Selected changes conflict with a coupled roster field; no changes imported')
    except Exception:
        model._batch_writes=False
        model.data = bytearray(before)
        model.history, model.redo_history, model.edits = history, redo, edits
        model.reload()
        raise
    model.history = history + ([(before, edits)] if bytes(model.data) != before else [])
    model.redo_history = [] if bytes(model.data) != before else redo
    return len(changes)


def rating_document(row):
    return json.dumps({"schema": "choops-ratings-1", "ratings": row["attribute_ratings"], "tendencies": row["shot_tendencies"]})


def paste_ratings(model, indices, text):
    require_college(model)
    document = json.loads(text)
    ratings, tendencies = document["ratings"], document["tendencies"]
    if document.get("schema") != "choops-ratings-1" or len(ratings) != RATING_COUNT or len(tendencies) != len(TENDENCY_NAMES):
        raise ValueError("Copy ratings from this editor first")
    for values, low in ((ratings, 35), (tendencies, 0)):
        if any(type(v) is not int or not low <= v <= 99 for v in values):
            raise ValueError("Invalid rating values")
    changes = []
    for index in sorted(set(indices)):
        model.row_offset("players", index)
        for field, values in (("attribute_ratings", ratings), ("shot_tendencies", tendencies)):
            for slot, value in enumerate(values):
                old = model.rows["players"][index][field][slot]
                if old != value:
                    changes.append(dict(table="players", index=index, field=field, slot=slot, old=old, value=value))
    return apply_changes(model, changes)


def identities(model, table, *, player_ids=True):
    result = defaultdict(list)
    owners = school_labels(model)
    ids=[row.get('player_id') for row in model.rows.get('players',[])]
    stable_ids=player_ids and bool(ids) and None not in ids and len(set(ids))==len(ids)
    for row in model.rows.get(table, []):
        if table == "players":
            # Name and school are required; changed names and transfers are ambiguous.
            key = (owners.get(row["index"], "").casefold(),row['player_id']) if stable_ids else (owners.get(row["index"], "").casefold(), row["first_name"].casefold(), row["last_name"].casefold())
        elif table == "uniforms":
            key = (row["team_asset_id"], row["variant_code"])
        else:
            key = next((str(row[k]).casefold() for k in ('school_name','conference_name','coach_name','arena_name') if row.get(k)),None)
        result[key].append(row["index"])
    return result


def compare(model, other):
    require_college(model);require_college(other)
    changes, unmatched = [], []
    owners=school_labels(model)
    maps = {}
    def unique_player_ids(roster):
        ids=[r.get('player_id') for r in roster.rows.get('players',[])]
        return bool(ids) and None not in ids and len(set(ids))==len(ids)
    player_ids=unique_player_ids(model) and unique_player_ids(other)
    for table in model.rows:
        left, right = identities(model, table,player_ids=player_ids), identities(other, table,player_ids=player_ids)
        maps[table] = {indices[0]: right[key][0] for key, indices in left.items() if key is not None and len(indices) == 1 and len(right.get(key, [])) == 1}
        unmatched.extend(f"{table}: {label(model.rows[table][i])} (missing or ambiguous match)" for indices in left.values() for i in indices if i not in maps[table])
    for table, row, field, slot, old in cells(model):
        peer_index = maps[table].get(row["index"])
        if peer_index is None:
            continue
        value = other.rows[table][peer_index][field]
        if slot is not None:
            value = value[slot]
        target = REFERENCES[field][1] if field in REFERENCES else 'conferences' if table=='teams' and field=='conference_index' else None
        if target is not None and value is not None:
            inverse = {v: k for k, v in maps.get(target, {}).items()}
            if value not in inverse:
                unmatched.append(f"{table}: {label(row)} / {field} (unmatched reference)")
                continue
            value = inverse[value]
        if old != value:
            changes.append(dict(table=table, index=row["index"], field=field, slot=slot, old=old, value=value, record=label(row), school=owners.get(row["index"], "") if table == "players" else row.get("school_name", "")))
    return {"changes": changes, "unmatched": unmatched}
