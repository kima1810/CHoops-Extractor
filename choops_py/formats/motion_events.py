"""Bounded motion-event bridge; semantic mappings must be supplied explicitly.

This translates an event table, never a playable motion bank. Native marker IDs
are game-specific. No speculative cross-game mapping is installed here.
"""

from __future__ import annotations

import math
import struct

from .binary import Binary
from .embedded_motion import NativeELF

SENTINEL = -0x80000000
MAX_EVENTS = 100000
MAX_INPUT = 256 * 1024 * 1024
PROFILES = {"college-hoops-2k8": 8, "nba-2k11": 12}

# Only individually traced reads, not inferred complete payload layouts. The
# roles describe native operations, not unproven basketball/contact labels.
PAYLOAD_READS = {
    90: ((0, "I", "actor-category-comparison", "0x47F4FC"),),
    92: (
        (0, "i", "nonzero-dispatch-index", "0x4D1B9C"),
        (4, "f", "clamped-random-threshold", "0x4D1B9C"),
    ),
    93: ((0, "i", "nonzero-dispatch-table-index", "0x43903C"),),
    94: (
        (0, "i", "dispatch-table-index-0xA1E25C", "0x38603C"),
        (4, "i", "identity-table-index-0xA1E200", "0x38603C"),
    ),
    173: (
        (0, "i", "selection-table-index-0xA1E11C", "0x3839B8"),
        (12, "f", "event-time-window-extension", "0x3839B8"),
    ),
    178: ((0, "i", "dispatch-cases-59-60-61", "0x655604"),),
    186: ((0, "i", "selection-value-addend", "0x42EBD8"),),
}


def inspect_payload_consumers(raw, identity, address, *, native=False):
    """Inspect traced payload reads without treating them as portable semantics.

    Gaps, remaining size, other consumers and target enum correspondence stay
    unresolved. This does not make opaque payloads eligible for conversion.
    """
    if len(raw) > MAX_INPUT or type(address) is not int or address < 0 or address % 4:
        raise ValueError("Payload input/address exceeds bounds or alignment")
    reader = NativeELF(raw).read if native else Binary(raw).slice
    fields = []
    for offset, kind, role, consumer in PAYLOAD_READS.get(identity, ()):
        data = reader(address + offset, 4)
        value = struct.unpack(">" + kind, data)[0]
        fields.append(
            dict(
                offset=offset,
                type=kind,
                raw_bits=int.from_bytes(data, "big"),
                value=value if kind != "f" or math.isfinite(value) else None,
                role=role,
                consumer=consumer,
            )
        )
    return dict(
        fields=fields,
        complete_payload=False,
        portable_semantics=False,
        gameplay_ready=False,
    )


def mirrored_marker_contract():
    """The native mirror-swapped pair plus invariant third marker, not all IDs.

    NBA11 0x3806D4 and CH 0x231BB0 exchange the pair under the same mirror flag.
    NBA11's additional marker 24 is deliberately excluded. Anatomical or ball
    contact names are not inferred from this selector alone.
    """
    return dict(
        schema=1,
        rules=[
            dict(
                source_id=source,
                target_id=target,
                payload_word=None,
                evidence="Native mirrored selector NBA11 0x3806D4 / CH 0x231BB0",
            )
            for source, target in ((21, 20), (22, 21), (23, 22))
        ],
    )


def curve_timing_contract():
    """Verified selector and trajectory-cache timing roles, not all events.

    Native CH 0x3073B4 / NBA11 0x46DE20 fill the same four timing fields
    and pass them to equivalent curve normalizers CH 0x2CBEC / NBA11 0x141CC.
    NBA11 46 maps to CH 40 here: a blanket minus-one rule is incorrect.
    """
    result = mirrored_marker_contract()
    result["rules"].extend(
        dict(
            source_id=source,
            target_id=target,
            payload_word=None,
            evidence="Native trajectory cache CH 0x3073B4 / NBA11 0x46DE20; equivalent five-float curve normalizers",
        )
        for source, target in ((20, 19), (37, 36), (46, 40), (38, 37))
    )
    return result


def inspect_events(raw, profile, start=0, *, native=False):
    """Read relative IFF-block offsets or absolute decoded-ELF addresses.

    Only NBA11 event 90 exposes a rule-selecting payload word here. Additional
    individually traced reads have separate opt-in inspection; their complete
    payload schemas and cross-game enum correspondence remain unresolved.
    The sentinel occupies at least four bytes, not a complete event row.
    """
    if profile not in PROFILES:
        raise ValueError("Motion event profile is not established")
    if len(raw) > MAX_INPUT or type(start) is not int or start < 0 or start % 4:
        raise ValueError("Motion event input/address exceeds bounds or alignment")
    b = Binary(raw)
    elf = NativeELF(raw) if native else None

    def read(address, size):
        return elf.read(address, size) if elf else b.slice(address, size)

    cursor, rows = start, []
    while True:
        identity = struct.unpack(">i", read(cursor, 4))[0]
        if identity == SENTINEL:
            break
        if len(rows) >= MAX_EVENTS:
            raise ValueError("Motion event list exceeds bounded inspection")
        data = read(cursor, PROFILES[profile])
        time_bits = struct.unpack_from(">I", data, 4)[0]
        time = struct.unpack_from(">f", data, 4)[0]
        if not math.isfinite(time):
            raise ValueError("Motion event time must be finite")
        payload = None
        payload_word = None
        if profile == "nba-2k11":
            value = struct.unpack_from(">I", data, 8)[0]
            if value:
                delta = value if value < 0x80000000 else value - 0x100000000
                payload = value if native else cursor + 8 + delta - 1
                if payload % 4:
                    raise ValueError("Motion event payload is not word aligned")
                read(payload, 1)  # Validate even an opaque pointer's target.
                if identity == 90:
                    payload_word = struct.unpack(">I", read(payload, 4))[0]
            elif identity == 90:
                raise ValueError("NBA11 event 90 requires its native payload")
        rows.append(
            dict(
                offset=cursor,
                id=identity,
                time=time,
                time_bits=time_bits,
                payload=payload,
                payload_word=payload_word,
            )
        )
        cursor += PROFILES[profile]
    return dict(
        profile=profile,
        mode="read-only",
        native_addresses=native,
        start=start,
        sentinel=cursor,
        entries=rows,
        entry_stride=PROFILES[profile],
        time_ordered=all(a["time"] <= b["time"] for a, b in zip(rows, rows[1:])),
        opaque_payloads=sum(
            r["payload"] is not None and r["payload_word"] is None for r in rows
        ),
        gameplay_ready=False,
        complete_motion=False,
    )


def inspect_auxiliary_pairs(raw, start, *, native=False):
    """NBA11 +0x34 membership table, confirmed by native 0x1A880.

    Count followed by eight-byte rows; native comparison uses each first word.
    No pointer fixups establish the second word's meaning, so it stays raw.
    """
    if len(raw) > MAX_INPUT or type(start) is not int or start < 0 or start % 4:
        raise ValueError("Auxiliary table input/address exceeds bounds or alignment")
    b = Binary(raw)
    elf = NativeELF(raw) if native else None
    read = elf.read if elf else b.slice
    count = struct.unpack(">i", read(start, 4))[0]
    if not 0 <= count <= MAX_EVENTS:
        raise ValueError("Auxiliary pair count exceeds inspection bounds")
    data = read(start + 4, count * 8)
    return dict(
        count=count,
        entries=[dict(key=a, raw_value=b) for a, b in struct.iter_unpack(">II", data)],
        gameplay_ready=False,
        semantics_established=False,
    )


def transcode_events(report, contract):
    """Pack CH event rows using a reviewed, explicit per-ID/payload contract.

    Unknown IDs, opaque payloads and ambiguous mappings block the whole output.
    Times, order, duplicate markers and float bit patterns survive unchanged.
    Event 90 may select a rule by its consumed payload word; all other payload
    schemas remain blocked. A contract is a research assertion, not validation
    of gameplay semantics. Its evidence strings are retained in the report.
    """
    if report.get("profile") != "nba-2k11":
        raise ValueError("Event bridge requires an inspected NBA 2K11 event table")
    if not isinstance(contract, dict) or contract.get("schema") != 1:
        raise ValueError("Event mapping contract requires schema 1")
    rules = contract.get("rules")
    if not isinstance(rules, list) or len(rules) > MAX_EVENTS:
        raise ValueError("Event mapping contract requires bounded rules")
    mapping = {}
    for rule in rules:
        if not isinstance(rule, dict):
            raise ValueError("Invalid event mapping rule")
        source, target = rule.get("source_id"), rule.get("target_id")
        word, evidence = rule.get("payload_word"), rule.get("evidence")
        if any(
            type(v) is not int or not 0 <= v <= 0x7FFFFFFF for v in (source, target)
        ):
            raise ValueError("Event mapping IDs must be nonnegative signed integers")
        if word is not None and (
            source != 90 or type(word) is not int or not 0 <= word <= 0xFFFFFFFF
        ):
            raise ValueError("Only event 90 supports an explicit payload-word rule")
        if (
            not isinstance(evidence, str)
            or not evidence.strip()
            or len(evidence) > 2048
        ):
            raise ValueError("Each event mapping rule requires bounded evidence text")
        key = (source, word)
        if key in mapping:
            raise ValueError("Duplicate or ambiguous event mapping rule")
        mapping[key] = (target, evidence)
    output, applied = bytearray(), []
    rows = report["entries"]
    if len(rows) > MAX_EVENTS:
        raise ValueError("Motion event list exceeds bounded conversion")
    for row in rows:
        if row["payload"] is not None and (
            row["id"] != 90 or row["payload_word"] is None
        ):
            raise ValueError(
                f"Opaque payload for event {row['id']}; conversion blocked"
            )
        word = row["payload_word"] if row["payload"] is not None else None
        key = (row["id"], word)
        if key not in mapping:
            raise ValueError(
                f"No explicit mapping for event {row['id']} payload {word}"
            )
        target, evidence = mapping[key]
        output += struct.pack(">iI", target, row["time_bits"])
        applied.append(
            dict(
                source_id=row["id"],
                payload_word=word,
                target_id=target,
                evidence=evidence,
            )
        )
    output += struct.pack(">i", SENTINEL)
    check = inspect_events(output, "college-hoops-2k8")
    if [(r["id"], r["time_bits"]) for r in check["entries"]] != [
        (a["target_id"], r["time_bits"]) for a, r in zip(applied, rows)
    ]:
        raise ValueError("Converted event table failed preservation check")
    return bytes(output), dict(
        scope="event-table-only",
        events=len(rows),
        rules_applied=applied,
        semantic_mapping="caller-supplied-research-contract",
        target_profile="college-hoops-2k8",
        gameplay_ready=False,
        complete_motion=False,
        time_bits_preserved=True,
    )
