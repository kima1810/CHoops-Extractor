"""Read-only CH recruit-pool and separately supplied interest-node audits.

Unknown fields remain opaque. These readers never allocate a recruit, mutate a
roster, convert a player, or infer an enclosing Legacy interest-pool save offset.
"""

from collections import Counter
from hashlib import sha256
from struct import unpack_from

from ..roster.schema import detect_tables
from .transfer_portal import native_preference_profile

MAX_INPUT = 64 * 1024 * 1024
RECRUIT_STRIDE = 0xD8
MAX_RECRUITS = 16384  # Reader bound, not a native growth limit.
INTEREST_CAPACITY = 16000
INTEREST_STRIDE = 8
CLASS_LABELS = ("HS FR", "HS SO", "HS JR", "HS SR", "JC FR", "JC SO")


def inspect_recruit_pool(payload: bytes) -> dict:
    """Inspect a decoded roster payload, retaining unknowns as source hashes.

    Header +0x48 is allocated record count, not active/available recruit count.
    An all-zero record is reported as blank, never certified safe for insertion.
    """
    if (
        not isinstance(payload, (bytes, bytearray))
        or not 0xB0 <= len(payload) <= MAX_INPUT
    ):
        raise ValueError("recruit inspection requires a bounded decoded CH roster")
    tables = detect_tables(payload)
    count, delta = unpack_from(">Ii", payload, 0x48)
    if not 1 <= count <= MAX_RECRUITS:
        raise ValueError("unsupported recruit directory count")
    if delta == 0:
        raise ValueError("null recruit directory pointer")
    start = 0x4C + delta - 1
    end = start + count * RECRUIT_STRIDE
    if start < 0xB0 or start % 4 or end > len(payload):
        raise ValueError("recruit pool is misaligned or outside the roster")
    for name, (other, size, stride) in tables.items():
        if start < other + size * stride and other < end:
            raise ValueError(f"recruit pool overlaps {name}")
    # Also protect starts of directory tables whose strides remain unknown.
    for at in range(0, 0xB0, 8):
        if at == 0x48:
            continue
        other_count, relative = unpack_from(">Ii", payload, at)
        target = at + 4 + relative - 1
        if other_count and relative and start <= target < end:
            raise ValueError("recruit pool contains another directory target")
    records = []
    classes: Counter[str] = Counter()
    blanks = 0
    for index in range(count):
        at = start + index * RECRUIT_STRIDE
        raw = payload[at : at + RECRUIT_STRIDE]
        if not any(raw):
            blanks += 1
            continue
        word40, word44 = unpack_from(">II", raw, 0x40)
        class_code = (word40 >> 21) & 15
        profile = (word40 >> 7) & 127
        head = unpack_from(">H", raw, 0x4A)[0]
        label = CLASS_LABELS[class_code] if class_code < len(CLASS_LABELS) else None
        issues = []
        if label is None:
            issues.append("unestablished_class_code")
        preferences = None
        if profile < 96:
            preferences = native_preference_profile(profile)
        else:
            issues.append("uninitialized_preference_profile")
        if head != 0xFFFF and head >= INTEREST_CAPACITY:
            issues.append("unsupported_interest_head")
        classes[label or f"unknown_{class_code}"] += 1
        records.append(
            {
                "slot": index,
                "offset": at,
                "record_sha256": sha256(raw).hexdigest(),
                "flags_2d": raw[0x2D],
                "recruiting_filter_bit_2": bool(raw[0x2D] & 4),
                "committed_bit": bool(word40 >> 31),
                "class_code": class_code,
                "class_label": label,
                "preference_index": profile,
                "preferences": preferences,
                "location_id": (word44 >> 3) & 1023,
                "interest_head": head,
                "issues": issues,
            }
        )
    return {
        "schema": 1,
        "source_sha256": sha256(payload).hexdigest(),
        "pool_start": start,
        "pool_bytes": end - start,
        "record_stride": RECRUIT_STRIDE,
        "allocated_slots": count,
        "blank_records": blanks,
        "nonzero_records": len(records),
        "class_counts_nonzero": dict(classes),
        "school_count": tables["teams"][1],
        "records": records,
        "blank_slots_certified_reusable": False,
        "native_pool_insertion_installed": False,
        "gameplay_ready": False,
    }


def inspect_interest_graph(
    nodes: bytes,
    heads: dict[int, int],
    *,
    school_count: int,
    free_head: int | None = None,
) -> dict:
    """Audit a separately identified native 16000-node block.

    +0 signed school ID, +2 signed next, +4 signed score, +6/+7 raw bytes.
    No enclosing save offset is inferred. Unowned nodes are not called leaks.
    """
    if (
        not isinstance(nodes, (bytes, bytearray))
        or len(nodes) != INTEREST_CAPACITY * INTEREST_STRIDE
    ):
        raise ValueError("interest block must contain exactly 16000 eight-byte nodes")
    if type(school_count) is not int or not 1 <= school_count <= 8192:
        raise ValueError("invalid school count")
    if not isinstance(heads, dict) or len(heads) > MAX_RECRUITS:
        raise ValueError("heads must be a bounded slot-to-head mapping")

    def index_or_end(value: int) -> int | None:
        if type(value) is not int:
            raise ValueError("node index must be an integer")
        if value in (-1, 0xFFFF):
            return None
        if not 0 <= value < INTEREST_CAPACITY:
            raise ValueError("unsupported interest index or terminator")
        return value

    owners: dict[int, str] = {}
    chains = []
    free_nodes = 0
    for slot in heads:
        if type(slot) is not int or not 0 <= slot < MAX_RECRUITS:
            raise ValueError("invalid recruit slot identity")
    entries = [(f"recruit_{slot}", heads[slot], False) for slot in sorted(heads)]
    if free_head is not None:
        entries.append(("free", free_head, True))
    for owner, head, is_free in entries:
        index = index_or_end(head)
        schools = set()
        chain = []
        previous_score = None
        sorted_scores = True
        while index is not None:
            if index in owners:
                raise ValueError(f"interest node cycle or shared ownership at {index}")
            owners[index] = owner
            school, next_index, score, byte6, byte7 = unpack_from(
                ">hhhBB", nodes, index * INTEREST_STRIDE
            )
            if is_free:
                if school != 0x7FFF:
                    raise ValueError("free list contains a live school node")
                free_nodes += 1
            else:
                if not 0 <= school < school_count:
                    raise ValueError("live interest node school is out of range")
                if school in schools:
                    raise ValueError("duplicate school in recruit interest list")
                schools.add(school)
                if previous_score is not None and score > previous_score:
                    sorted_scores = False
                previous_score = score
                chain.append(
                    {
                        "index": index,
                        "school_index": school,
                        "score": score,
                        "byte_6": byte6,
                        "byte_7": byte7,
                    }
                )
            index = index_or_end(next_index)
        if not is_free:
            chains.append(
                {
                    "owner": owner,
                    "nodes": chain,
                    "descending_score_order": sorted_scores,
                }
            )
    return {
        "schema": 1,
        "node_capacity": INTEREST_CAPACITY,
        "source_sha256": sha256(nodes).hexdigest(),
        "live_nodes": len(owners) - free_nodes,
        "free_nodes_traced": free_nodes,
        "free_head_supplied": free_head is not None,
        "unowned_nodes": INTEREST_CAPACITY - len(owners),
        "chains": chains,
        "native_pool_insertion_installed": False,
        "enclosing_save_offset_established": False,
        "gameplay_ready": False,
    }


RECRUITING_STATE_SIZE = 0x415A4
AGGREGATE_RECRUITING_OFFSET = 0x11418


def inspect_recruiting_section(section: bytes, roster: bytes) -> dict:
    """Inspect an explicitly identified native recruiting component.

    The offset is relative to 0x595D64's aggregate, not a certified USERDATA offset.
    Secondary-node ownership and every queue-field meaning remain unresolved.
    """
    if (
        not isinstance(section, (bytes, bytearray))
        or len(section) != RECRUITING_STATE_SIZE
    ):
        raise ValueError("recruiting section must be exactly 0x415A4 bytes")
    pool = inspect_recruit_pool(roster)
    interest_free, secondary_free = unpack_from(">ii", section)
    queue_counts = unpack_from(">4I", section, 8)
    other_counters = unpack_from(">4I", section, 0x18)
    if any(count > 128 for count in queue_counts):
        raise ValueError("recruiting queue count exceeds its 128-record block")
    if (
        secondary_free not in (-1, 0xFFFF)
        and not 0 <= secondary_free < INTEREST_CAPACITY
    ):
        raise ValueError("unsupported secondary free-list head")
    # Native ownership auditor 0x5CA108 traverses only flags &4 recruit records.
    heads = {
        row["slot"]: row["interest_head"]
        for row in pool["records"]
        if row["recruiting_filter_bit_2"]
    }
    graph = inspect_interest_graph(
        section[0x28:0x1F428],
        heads,
        school_count=pool["school_count"],
        free_head=interest_free,
    )
    secondary_nonnull = 0
    secondary_outside = 0
    for at in range(0x1F428, 0x3E828, 8):
        pointer = unpack_from(">I", section, at)[0]
        if pointer:
            secondary_nonnull += 1
            if pointer >= len(roster):
                secondary_outside += 1
    queues = []
    for block, count in enumerate(queue_counts):
        base = 0x3E828 + block * 0xA00
        for index in range(count):
            at = base + index * 20
            pointers = unpack_from(">3I", section, at + 4)
            queues.append(
                {
                    "block": block,
                    "index": index,
                    "record_sha256": sha256(section[at : at + 20]).hexdigest(),
                    "roster_relative_words": pointers,
                    "references_within_roster": all(
                        pointer < len(roster) for pointer in pointers
                    ),
                    "referent_types_established": False,
                }
            )
    return {
        "schema": 1,
        "source_sha256": sha256(section).hexdigest(),
        "bytes": RECRUITING_STATE_SIZE,
        "native_aggregate_relative_offset": AGGREGATE_RECRUITING_OFFSET,
        "userdata_offset_established": False,
        "interest_graph": graph,
        "secondary_free_head": secondary_free,
        "secondary_nonnull_references": secondary_nonnull,
        "secondary_references_outside_roster": secondary_outside,
        "secondary_node_ownership_validated": False,
        "queue_counts": queue_counts,
        "other_counters_raw": other_counters,
        "queues": queues,
        "tail_word_raw": unpack_from(">I", section, 0x41028)[0],
        "tail_bytes_sha256": sha256(section[0x4102C:]).hexdigest(),
        "full_native_state_semantics_established": False,
        "native_pool_insertion_installed": False,
        "gameplay_ready": False,
    }
