"""Read-only catalog of the observed CH2K8 PS3 native popup dispatch table.

This reports executable metadata, not a running game's queue or an editor for
event triggers. Use an already decoded analysis ELF; original EBOOT stays intact.
"""

import hashlib
import struct
from collections import Counter

from ..formats.embedded_motion import NativeELF

POPUP_TABLE = 0x125A37D4
POPUP_COUNT = 83


def _span(elf, address, size, executable=False):
    for segment in elf.segments:
        delta = address - segment["address"]
        if 0 <= delta and delta + size <= segment["file_bytes"]:
            if executable and not segment["flags"] & 1:
                raise ValueError("Popup provider is not in executable memory")
            start = segment["offset"] + delta
            return elf.raw[start:start + size]
    raise ValueError("Popup dependency is outside file-backed native memory")


def _family(kind):
    if kind < 5:
        return "single-line statistics"
    if kind < 37:
        return "statistics and milestone panels"
    if kind < 39:
        return "three-provider panels"
    if kind < 64:
        return "fouls and game events"
    if kind < 77:
        return "injury updates"
    return {
        77: "scoring run", 78: "game point", 79: "clear-ball notice",
        80: "uncleared-ball turnover", 81: "ten-second violation", 82: "foul out",
    }[kind]


def inspect_runtime(raw):
    """Validate all observed rows and every non-null PPC64 function descriptor.

The second table word is queue priority, not line count: admission copies it
to event +0x1C and compares priorities when inserting events. Provider slots
are independent; two priority-2 modes have only one provider.
"""
    elf = NativeELF(raw)
    table = _span(elf, POPUP_TABLE, POPUP_COUNT * 20)
    rows = []
    for kind in range(POPUP_COUNT):
        queue, priority, *descriptors = struct.unpack_from(
            ">5I", table, kind * 20)
        if queue > 3 or priority not in (1, 2) or not descriptors[0]:
            raise ValueError("Not the observed CH2K8 popup dispatch layout")
        providers = []
        for descriptor in descriptors:
            if not descriptor:
                providers.append(None)
                continue
            if descriptor % 4:
                raise ValueError("Unaligned popup function descriptor")
            function, toc = struct.unpack(">2I", _span(elf, descriptor, 8))
            if function % 4 or toc not in (0xA54AC8, 0xA64A94):
                raise ValueError("Unsupported popup function descriptor")
            _span(elf, function, 4, executable=True)
            _span(elf, toc, 4)
            providers.append(dict(descriptor=descriptor, function=function, toc=toc))
        rows.append(dict(type=kind, queue=queue, priority=priority,
                         family=_family(kind), providers=providers))
    return dict(
        schema=1, profile="college-hoops-2k8-ps3-observed",
        mode="read-only", source_sha256=hashlib.sha256(raw).hexdigest(),
        table_address=POPUP_TABLE, row_bytes=20, rows=rows,
        queue_counts=dict(Counter(row["queue"] for row in rows)),
        unique_providers=len({
            p["function"] for row in rows for p in row["providers"] if p
        }),
        runtime_state_observed=False, patch_supported=False,
        notes=[
            "Static dispatch entries do not prove every event is triggered in a mode.",
            "Priority is independent of the number of non-null providers.",
            "Timing, queue advancement and native text tags must remain intact.",
            "Other executable revisions and NBA profiles are not established.",
        ],
    )
