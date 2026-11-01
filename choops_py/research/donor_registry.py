"""Observed NBA11 signature collection registration and typed dependency index.

Native 0x6599D0 filters category at entry +4 and registers the payload through
0x65840C. 0x659730 looks entries up by +0. The reference resolver 0x656B70
distinguishes SingleMoCap/group IDs using each 12-byte reference's +4 word.
Unknown payload tails/group internals remain read-only.
"""

from collections import Counter, defaultdict

from ..formats.binary import Binary
from ..formats.motion_envelope import inspect_collection
from ..formats.standard_iff import StandardIFF
from ..formats.standard_iff_writer import record_blocks

COLLECTION = 0x449E4AC7
MOTION = 0x60900D71
GROUP = 0x39F61D57
MAX_BANK_BYTES = 128 * 1024 * 1024


def reference_selection(kind):
    """Describe verified 0x656AEC selection without dereferencing runtime memory."""
    if kind == 0:
        return dict(mode="direct", group_member=None, runtime_offset=None)
    if 1 <= kind <= 4:
        return dict(
            mode="group-member",
            group_member=kind - 1,
            runtime_offset=(kind - 1) * 16 + 12,
        )
    if kind == 5:
        return dict(mode="disabled", group_member=None, runtime_offset=None)
    # Other native branches fall through, but their serialized meaning is not
    # established. Do not silently interpret malformed data as a direct motion.
    return dict(mode="unestablished", group_member=None, runtime_offset=None)


def inspect_entries(raw, profile="nba-2k11"):
    if profile != "nba-2k11":
        raise ValueError("Donor registration semantics are established only for NBA11")
    if len(raw) > MAX_BANK_BYTES:
        raise ValueError("Signature collection exceeds bounded inspection")
    report = inspect_collection(raw, profile)
    b = Binary(raw)
    rows = report["entries"]
    table_end = max((r["offset"] + 20 for r in rows), default=8)
    targets = sorted({r["payload"] for r in rows if r["payload"] is not None})
    ends = dict(zip(targets, targets[1:] + [len(raw)]))
    result = []
    for row in rows:
        key, category, _, ordinal, flag = row["raw_words"]
        if not 0 <= category <= 30:
            raise ValueError(
                "Signature category is outside the observed 31-category manager"
            )
        count = 8 if category == 0 else 1 if 2 <= category <= 10 else 2
        start = row["payload"]
        if (
            start is None
            or start % 4
            or start < table_end
            or start + count * 12 > ends[start]
        ):
            raise ValueError(
                "Signature references overlap or exceed their payload extent"
            )
        refs = []
        for index in range(count):
            at = start + index * 12
            identity, kind, cache = (b.u32(at + delta) for delta in (0, 4, 8))
            if cache:
                raise ValueError(
                    "Serialized signature contains a nonzero native cache pointer"
                )
            refs.append(
                dict(
                    slot=index,
                    resource_id=identity,
                    raw_kind=kind,
                    resource_type_hash=GROUP if kind else MOTION,
                    empty=identity == 0,
                    selection=reference_selection(kind),
                )
            )
        result.append(
            dict(
                index=row["index"],
                raw_lookup_key=key,
                localization_key=key | 1,
                category=category,
                ordinal_word=ordinal,
                raw_flag_0x10=flag,
                references=refs,
                unparsed_tail_bytes=ends[start] - start - count * 12,
                payload_semantics_complete=False,
            )
        )
    return result


def inspect_banks(banks, profile="nba-2k11"):
    """Index related banks together; ambiguity never chooses a load-order winner."""
    if profile != "nba-2k11" or not 1 <= len(banks) <= 32:
        raise ValueError("Choose 1..32 NBA11 signature banks")
    if sum(len(raw) for _, raw in banks) > MAX_BANK_BYTES:
        raise ValueError("Combined signature banks exceed 128 MiB")
    index = defaultdict(list)
    collections = []
    for bank_index, (name, raw) in enumerate(banks):
        iff = StandardIFF(raw)
        if any(b["logical_size"] > MAX_BANK_BYTES for b in iff.blocks):
            raise ValueError("Signature bank block exceeds bounded inspection")
        for record in iff.records:
            if record["type_hash"] in (MOTION, GROUP):
                index[record["type_hash"], record["id"]].append(
                    dict(bank=bank_index, record=record["index"])
                )
            if record["type_hash"] == COLLECTION:
                if len(list(iff.spans(record))) != 1:
                    raise ValueError("Observed signature collection requires one block")
                blocks = record_blocks(iff, record)
                if len(blocks) != 1:
                    raise ValueError("Observed signature collection requires one block")
                collections.append(
                    (
                        bank_index,
                        record["index"],
                        inspect_entries(blocks[0][3], profile),
                    )
                )
    if not collections:
        raise ValueError("No observed signature collections in the supplied banks")
    rows = []
    counts = Counter()
    categories = defaultdict(list)
    for bank, record, entries in collections:
        for row in entries:
            item = dict(bank=bank, collection_record=record, **row)
            for ref in item["references"]:
                matches = (
                    index.get((ref["resource_type_hash"], ref["resource_id"]), [])
                    if not ref["empty"]
                    else []
                )
                ref["candidates"] = matches
                ref["status"] = (
                    "empty"
                    if ref["empty"]
                    else "resolved-identity"
                    if len(matches) == 1
                    else "external-or-missing"
                    if not matches
                    else "ambiguous"
                )
                counts[ref["status"]] += 1
            rows.append(item)
            categories[item["category"]].append(item["ordinal_word"])
    return dict(
        profile=profile,
        mode="read-only",
        banks=[name for name, _ in banks],
        entries=rows,
        entry_count=len(rows),
        reference_counts=dict(counts),
        categories=[
            dict(
                category=category,
                count=len(ordinals),
                unique_ordinals=len(set(ordinals)),
                contiguous_from_zero=min(ordinals) == 0
                and max(ordinals) == len(set(ordinals)) - 1,
            )
            for category, ordinals in sorted(categories.items())
        ],
        runtime_registration_installed=False,
        target_slot_mapping_established=False,
        group_payloads_translated=False,
        gameplay_ready=False,
    )
