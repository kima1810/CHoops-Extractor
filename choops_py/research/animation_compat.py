"""Read-only cross-game animation evidence; no animation replacement or porting."""

import argparse
from collections import Counter, defaultdict
from contextlib import ExitStack

from ..archive.build_io import BankReader
from ..archive.manifests import safe_output
from ..archive.usrdir_reader import Archive
from ..core.reports import save_json
from ..formats.binary import Binary
from ..formats.compression import decode
from ..formats.motion_envelope import inspect_collection, inspect_envelope
from ..formats.standard_iff import StandardIFF

TRACK_TYPES = {
    0x60900D71: "SingleMoCap",
    0x7657AB8A: "SKEL",
    0x39F61D57: "motion reference/group family (unresolved)",
    0x449E4AC7: "motion selection collection",
    0x0D53D4B3: "animation graph",
    0x9D34E89E: "unresolved motion.iff record family",
}
MAX_HEADER = 4 * 1024 * 1024
MAX_SAMPLE = 128 * 1024 * 1024


def header_records(raw, entry_size):
    """Validate counts against the actual header, not an arbitrary 10k ceiling."""
    b = Binary(raw)
    size, length, bc, fc = b.u32(4), b.u32(8), b.u32(16), b.u32(24)
    if b.u32(0) != 0xFF3BEF94 or not 32 <= size <= length <= entry_size:
        raise ValueError("Invalid animation inventory IFF boundaries")
    if size != len(raw) or size > MAX_HEADER or bc > (size - 32) // 32:
        raise ValueError("Invalid animation inventory block table")
    table = b.relative(28)
    if table < 32 + bc * 32 or table + fc * 4 > size:
        raise ValueError("Invalid animation inventory record pointer table")
    found = []
    for i in range(fc):
        at = b.relative(table + i * 4)
        if at < table + fc * 4:
            raise ValueError("Animation record overlaps its pointer table")
        b.slice(at, 12)
        blocks = b.u32(at + 8)
        if blocks > bc:
            raise ValueError("Animation record block count exceeds IFF blocks")
        b.slice(at + 12, blocks * 4)
        typ = b.u32(at + 4)
        if typ in TRACK_TYPES:
            found.append(dict(record=i, type_hash=typ, type=TRACK_TYPES[typ]))
    return found


def _profile(archive):
    title = archive.game_info.get("TITLE", "").lower()
    if "college hoops" in title:
        return "college-hoops-2k8"
    if "2k11" in title:
        return "nba-2k11"
    if "2k14" in title:
        return "nba-2k14"
    return None


def inspect(source, job=None):
    archive = Archive(source)
    before = [(archive.path / p["name"]).stat() for p in archive.parts]
    found, skipped, failures = [], [], []
    counts = Counter()
    with ExitStack() as stack:
        reader = BankReader(archive, stack)
        for i, entry in enumerate(sorted(archive.entries, key=lambda e: e["offset"])):
            if job:
                job.check()
                job.progress(
                    i, len(archive.entries), "Inspecting animation record headers"
                )
            prefix = reader.read(entry["offset"], min(32, entry["size"]))
            if prefix[:4] != bytes.fromhex("ff3bef94"):
                continue
            if len(prefix) < 32:
                failures.append(
                    dict(archive_index=entry["index"], reason="Truncated IFF header")
                )
                continue
            size = Binary(prefix).u32(4)
            if size > MAX_HEADER:
                skipped.append(
                    dict(
                        archive_index=entry["index"],
                        reason="IFF header exceeds 4 MiB inspection bound",
                    )
                )
                continue
            try:
                if size < 32 or size > entry["size"]:
                    raise ValueError("Invalid animation inventory header length")
                rows = header_records(reader.read(entry["offset"], size), entry["size"])
            except (ValueError, IndexError) as error:
                failures.append(dict(archive_index=entry["index"], reason=str(error)))
                continue
            for row in rows:
                counts[row["type"]] += 1
                found.append(
                    dict(
                        archive_index=entry["index"],
                        archive=entry["name"] or f"hash_{entry['hash']:08x}",
                        **row,
                    )
                )
    samples = []
    selected = defaultdict(list)
    seen = Counter()
    # Prefer on-court banks and retain bank diversity, rather than five crowd rows.
    ordered = sorted(
        found,
        key=lambda r: (
            not r["archive"].startswith(("nba_animations", "siganims_", "animgraph_")),
            r["archive"],
            r["record"],
        ),
    )
    sampled = set()
    for item in ordered:
        key = (item["archive_index"], item["type"])
        if seen[item["type"]] >= 5 or key in sampled:
            continue
        entry = archive.entries[item["archive_index"]]
        if entry["size"] > MAX_SAMPLE:
            skipped.append(
                dict(
                    archive_index=entry["index"], reason="Sample exceeds 128 MiB bound"
                )
            )
            sampled.add(key)
            continue
        sampled.add(key)
        seen[item["type"]] += 1
        selected[item["archive_index"]].append(item)
    profile = _profile(archive)
    for index, items in selected.items():
        if job:
            job.check()
        iff = StandardIFF(archive.read(archive.entries[index]))
        decoded = {}
        for item in items:
            record = iff.records[item["record"]]
            blocks = []
            for bi, start, end in iff.spans(record):
                if bi not in decoded:
                    block = iff.blocks[bi]
                    if block["logical_size"] > MAX_SAMPLE:
                        raise ValueError(
                            "Animation sample logical block exceeds 128 MiB bound"
                        )
                    decoded[bi] = decode(
                        iff.raw[block["start"] : block["start"] + block["size"]],
                        block["logical_size"],
                    )
                blocks.append(decoded[bi][start:end])
            sample = {
                **item,
                "name": record["name"],
                "decoded_block_sizes": [len(b) for b in blocks],
                "header_prefixes": [b[:32].hex() for b in blocks],
            }
            if len(blocks) == 1:
                try:
                    if item["type_hash"] == 0x60900D71 and profile in (
                        "college-hoops-2k8",
                        "nba-2k11",
                    ):
                        sample["envelope"] = inspect_envelope(blocks[0], profile)
                    if item["type_hash"] == 0x449E4AC7 and profile in (
                        "nba-2k11",
                        "nba-2k14",
                    ):
                        data = inspect_collection(blocks[0], profile)
                        sample["collection"] = {
                            k: v for k, v in data.items() if k != "entries"
                        }
                except ValueError as error:
                    sample["profile_error"] = str(error)
            samples.append(sample)
    after = [(archive.path / p["name"]).stat() for p in archive.parts]
    if any(
        (a.st_size, a.st_mtime_ns, a.st_ino) != (b.st_size, b.st_mtime_ns, b.st_ino)
        for a, b in zip(before, after)
    ):
        raise ValueError("Source changed during animation inspection")
    return dict(
        game=archive.game_info,
        record_counts=dict(counts),
        records=found,
        samples=samples,
        skipped=skipped,
        header_errors=failures,
        source_unchanged=True,
        mode="read-only",
        tracks_decoded=False,
        port_implemented=False,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="+")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    output = safe_output(args.output, args.sources)
    if output.exists():
        raise ValueError("Choose a new animation report path")
    result = dict(
        games=[inspect(s) for s in args.sources],
        direct_swap_certified=False,
        conclusion=(
            "A shared type hash is not a compatibility guarantee. "
            "Native fixup layouts differ; bone mapping, tracks, events, "
            "root motion and selection/blending require conversion. "
            "No animation writer or gameplay port is enabled."
        ),
    )
    save_json(output, result)
    print(output)


if __name__ == "__main__":
    main()
