"""Read-only native motion envelope evidence, not a pose decoder or converter."""

import struct

from .binary import Binary

PROFILES = {
    "college-hoops-2k8": dict(
        minimum=64,
        fixups=(0x30, 0x34, 0x38, 0x3C),
        tail=0x40,
        resolved=0x38,
        reference=0x30,
    ),
    "nba-2k11": dict(
        minimum=56,
        fixups=(4, 0x24, 0x28, 0x2C, 0x30, 0x34),
        tail=0x38,
        resolved=0x30,
        reference=0x28,
    ),
}


def relative(header, field):
    value = struct.unpack(">i", header.slice(field, 4))[0]
    if value == 0:
        return None
    target = field + value - 1
    header.slice(target, 1)
    return target


def inspect_envelope(raw, profile):
    """Inspect only confirmed pointer fixups and alias/packed discrimination.

    The native reference resolver uses a different key field in the two games.
    An unresolved reference's key must never be interpreted as a payload pointer.
    Packed transforms, bone identities, timing and contact semantics stay opaque.
    """
    if profile not in PROFILES:
        raise ValueError("Motion envelope profile is not established for this game")
    layout = PROFILES[profile]
    b = Binary(raw)
    b.slice(0, layout["minimum"])
    result = dict(
        profile=profile, bytes=len(raw), pose_decoded=False, import_supported=False
    )
    if b.u32(layout["resolved"]) == 0:
        return {
            **result,
            "kind": "unresolved-reference",
            "source_reference_id": b.u32(layout["reference"]),
        }
    count = b.u32(0x10) & 0x3F
    b.slice(layout["tail"], count * 4)
    fields = (*layout["fixups"], *(layout["tail"] + i * 4 for i in range(count)))
    pointers = {hex(field): relative(b, field) for field in fields}
    result.update(kind="packed", auxiliary_pointer_count=count, pointers=pointers)
    if profile == "nba-2k11":
        # Native fixup 0x15F24 traverses 12-byte entries until INT_MIN, relocating
        # each entry's +8 pointer. This does not establish the event meanings.
        cursor = pointers["0x30"]
        rows = []
        if cursor is not None:
            while True:
                if len(rows) >= 100000:
                    raise ValueError("Motion event list exceeds bounded inspection")
                if b.u32(cursor) == 0x80000000:
                    break
                b.slice(cursor, 12)
                rows.append(
                    dict(
                        offset=cursor,
                        raw_words=[b.u32(cursor), b.u32(cursor + 4)],
                        payload=relative(b, cursor + 8),
                    )
                )
                cursor += 12
        result["event_entries"] = rows
    return result


def inspect_collection(raw, profile):
    """Read observed 0x449E4AC7 entry envelopes; keep contents and meanings opaque."""
    if profile not in ("nba-2k11", "nba-2k14"):
        raise ValueError("Motion collection profile is not established for this game")
    stride, pointer = (20, 8) if profile == "nba-2k11" else (28, 16)
    b = Binary(raw)
    count = b.u32(0)
    if count > 100000:
        raise ValueError("Motion collection count exceeds bounded inspection")
    if not count:
        return dict(profile=profile, entry_count=0, entries=[], import_supported=False)
    start = relative(b, 4)
    if start is None:
        raise ValueError("Motion collection has a null entry table")
    b.slice(start, count * stride)
    rows = []
    for i in range(count):
        at = start + i * stride
        rows.append(
            dict(
                index=i,
                offset=at,
                raw_words=[b.u32(at + j * 4) for j in range(stride // 4)],
                payload=relative(b, at + pointer),
            )
        )
    return dict(
        profile=profile,
        entry_count=count,
        entries=rows,
        entry_stride=stride,
        import_supported=False,
        payloads_decoded=False,
    )


def inspect_links(raw, profile):
    """Index local alias candidates without claiming cross-bank/runtime resolution."""
    from collections import defaultdict

    from .compression import decode
    from .standard_iff import StandardIFF

    if profile not in PROFILES:
        raise ValueError("Motion link profile is not established for this game")
    iff = StandardIFF(raw)
    candidates = defaultdict(list)
    for record in iff.records:
        if record["type_hash"] == 0x60900D71:
            candidates[record["id"]].append(record["index"])
    decoded, rows, edges, errors = {}, [], {}, []
    for record in iff.records:
        if record["type_hash"] != 0x60900D71:
            continue
        spans = list(iff.spans(record))
        if len(spans) != 1:
            errors.append(
                dict(
                    record=record["index"],
                    reason="Motion envelope requires one decoded block",
                )
            )
            continue
        bi, start, end = spans[0]
        block = iff.blocks[bi]
        if block["logical_size"] > 128 * 1024 * 1024:
            raise ValueError("Motion link block exceeds 128 MiB bound")
        if bi not in decoded:
            decoded[bi] = decode(
                iff.raw[block["start"] : block["start"] + block["size"]],
                block["logical_size"],
            )
        try:
            info = inspect_envelope(decoded[bi][start:end], profile)
        except ValueError as error:
            errors.append(dict(record=record["index"], reason=str(error)))
            continue
        row = dict(
            record=record["index"],
            id=record["id"],
            name=record["name"],
            kind=info["kind"],
        )
        if info["kind"] == "unresolved-reference":
            key = info["source_reference_id"]
            local = candidates.get(key, [])
            row.update(
                source_reference_id=key,
                local_candidates=local,
                status="local-candidate"
                if len(local) == 1
                else "ambiguous"
                if local
                else "external-or-missing",
            )
            if len(local) == 1:
                edges[record["index"]] = local[0]
        rows.append(row)
    # Iterative linear graph walk: malicious long alias chains cannot overflow
    # the Python call stack; ambiguous identities never become inferred edges.
    done, cycles = set(), []
    for origin in edges:
        if origin in done:
            continue
        path, positions = [], {}
        at = origin
        while at in edges and at not in done and at not in positions:
            positions[at] = len(path)
            path.append(at)
            at = edges[at]
        if at in positions:
            cycles.append(path[positions[at] :])
        done.update(path)
    return dict(
        profile=profile,
        records=rows,
        envelope_errors=errors,
        local_alias_cycles=cycles,
        mode="read-only",
        pose_decoded=False,
        import_supported=False,
        note=(
            "Local ID matches are candidates. Native bank/variant lookup, "
            "skeletons, events and pose sampling remain required."
        ),
    )
