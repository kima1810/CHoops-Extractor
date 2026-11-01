"""Topology-preserving experimental College Hoops garment editing.

Only the observed embedded float-position cloth layout is writable. OBJ is an
edit cage: faces, UVs, ordering and seam positions must survive the DCC roundtrip.
Observed SPU distance constraints are adapted; runtime fit still needs testing.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import struct
from pathlib import Path

from ..archive.manifests import safe_output
from ..core.errors import ToolError
from ..formats.binary import Binary
from ..formats.scne import preview_meshes
from ..formats.standard_iff import StandardIFF
from ..formats.standard_iff_writer import record_blocks, replace_records

SCHEMA = "choops-uniform-mesh-1"
WARNING = (
    "Experimental garment edit with adapted stretch/bend distances. Runtime "
    "body collision is unchanged; packed normal/tangent attributes are "
    "preserved. Animation, fit and lighting need manual game testing."
)
GARMENT = re.compile(
    r"(?:jersey_(?:u|v|vtri|tri|wishbone)_(?:thin|reg|fat)|shorts(?:thin|reg|fat))\Z"
)
CONTAINER = re.compile(
    r"cloth_(?:shorts|(?:u|v|vtri|tri|wishbone)(?:_(?:thin|reg|fat))?)\.iff\Z"
)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _layout(raw):
    """Require one authored mesh, three exact observed streams and strip draws."""
    h = Binary(raw)
    h.slice(0, 0x54)
    if h.u32(0x44) != 1 or h.u32(0x3C) != 1:
        raise ValueError("Uniform requires exactly one mesh and one instance")
    p = h.relative(0x48)
    h.slice(p, 176)
    if h.u32(p + 0x84) != 1 or h.u32(p + 0xA4) != 0x10:
        raise ValueError("Unsupported uniform stream/index layout")
    d = h.relative(p + 0x88)
    n = h.u32(d + 16)
    if not 3 <= n <= 10000 or h.u32(d + 20) != 3:
        raise ValueError("Unsupported uniform vertex dimensions")
    streams = []
    for i, stride in enumerate((4, 24, 4)):
        e = d + 28 + i * 16
        if h.u32(e + 4) != stride or h.u32(e + 8) != n * stride:
            raise ValueError("Unsupported uniform vertex stride")
        start = h.relative(e + 12)
        h.slice(start, n * stride)
        streams.append((start, n * stride))
    declaration = h.relative(p + 0x9C)
    codes = [h.slice(declaration + i * 64 + 8, 8).hex() for i in range(h.u32(p + 0x94))]
    if codes != [
        "2000010002030000",
        "200c010006010f00",
        "2010010006010200",
        "2014010006010e00",
        "2000000001020800",
        "2000020202010a00",
    ]:
        raise ValueError("Unsupported uniform vertex declarations")
    if any(a < d + 76 and d < a + size for a, size in streams):
        raise ValueError("Uniform vertex stream overlaps metadata")
    for i, (a, size) in enumerate(streams):
        if any(a < b + length and b < a + size for b, length in streams[i + 1 :]):
            raise ValueError("Aliased uniform vertex streams")
    positions = [
        struct.unpack_from(">3f", raw, streams[1][0] + i * 24) for i in range(n)
    ]
    uvs = [
        tuple(x / 32767 for x in struct.unpack_from(">2h", raw, streams[0][0] + i * 4))
        for i in range(n)
    ]
    if not all(math.isfinite(x) and abs(x) < 1000 for v in positions for x in v):
        raise ValueError("Invalid garment position")
    ni = h.u32(p + 0xA8)
    if ni > 100000:
        raise ValueError("Excessive garment indices")
    indices = struct.unpack(">" + str(ni) + "H", h.slice(h.relative(p + 0xAC), ni * 2))
    runs, draw = h.u32(p + 0x7C), h.relative(p + 0x80)
    if runs != 1 or h.u32(draw) != 6:
        raise ValueError("Unsupported garment draw topology")
    first, count = h.u32(draw + 4), h.u32(draw + 8)
    if first + count > ni:
        raise ValueError("Garment draw exceeds indices")
    faces, strip = [], []
    for index in indices[first : first + count]:
        if index == 65535:
            strip = []
            continue
        if index >= n:
            raise ValueError("Garment index outside vertex stream")
        strip.append(index)
        if len(strip) >= 3:
            a, b, c = strip[-3:]
            if len(strip) % 2 == 0:
                a, b = b, a
            if len({a, b, c}) == 3:
                faces.append((a, b, c))
    if not faces:
        raise ValueError("Empty garment")
    scene = preview_meshes([raw])
    if scene["warnings"] or len(scene["meshes"]) != 1:
        raise ValueError("Uniform fails supported scene preview")
    return {
        "positions": positions,
        "uvs": uvs,
        "faces": faces,
        "position_start": streams[1][0],
    }


def _cloth(raw, positions):
    """Identify native 16-byte rest particles by bounded pointers and exact XYZ.

    Do not search arbitrary bytes for floats. The first two same-sized particle
    buffers are zero-initialized workspace, not a second authored rest mesh.
    """
    h = Binary(raw)
    size = h.u16(0)
    start, end = h.u32(0xC0), h.u32(0xC8)
    if not size or size % 16 or end - start != size or start < 0xF0:
        raise ValueError("Unsupported cloth rest particle table")
    h.slice(start, size)
    particles = [struct.unpack_from(">4f", raw, p) for p in range(start, end, 16)]
    if not all(math.isfinite(x) and abs(x) < 1000 for v in particles for x in v[:3]):
        raise ValueError("Invalid cloth rest position")
    if not all(v[3] == 1 for v in particles):
        raise ValueError("Unsupported cloth rest particle attributes")
    lookup = {}
    for i, v in enumerate(particles):
        lookup.setdefault(struct.pack(">3f", *v[:3]), []).append(i)
    mapping = []
    for v in positions:
        matches = lookup.get(struct.pack(">3f", *v), [])
        if len(matches) != 1:
            raise ValueError(
                "Visible vertex has missing or ambiguous cloth rest particle"
            )
        mapping.append(matches[0])
    return start, mapping


def _pairs(iff):
    pairs = []
    seen = set()
    for r in iff.records:
        if r["type"] != "SCNE":
            continue
        if not GARMENT.fullmatch(r["name"]):
            raise ValueError("Not a supported College Hoops garment record")
        if r["name"] in seen:
            raise ValueError("Ambiguous garment scene names")
        seen.add(r["name"])
        matches = [
            c for c in iff.records if c["type"] == "Clth" and c["name"] == r["name"]
        ]
        if len(matches) != 1:
            raise ValueError("Missing or ambiguous matching cloth record")
        sb, cb = record_blocks(iff, r), record_blocks(iff, matches[0])
        if len(sb) != 1 or len(cb) != 1:
            raise ValueError("Only embedded garment records are writable")
        layout = _layout(sb[0][3])
        start, mapping = _cloth(cb[0][3], layout["positions"])
        pairs.append((r, matches[0], sb[0][3], cb[0][3], layout, start, mapping))
    if not pairs:
        raise ValueError("No supported garment records")
    return pairs


def write_obj(path, positions, uvs, faces):
    lines = [
        "# CHoops edit cage. Keep vertex order, UVs and triangles. Units unchanged.",
        "# Preserve vertex order; export without triangulating or modifiers.",
    ]
    lines += ["v " + " ".join(format(x, ".9g") for x in v) for v in positions]
    lines += ["vt " + " ".join(format(x, ".12g") for x in v) for v in uvs]
    lines += ["f " + " ".join(f"{i + 1}/{i + 1}" for i in face) for face in faces]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf8")


def read_obj(path, layout):
    """Validate topology/UV identity; OBJ normals do not replace native attributes."""
    path = Path(path)
    if path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError("OBJ exceeds garment size limit")
    positions, uvs, faces = [], [], []
    for line in path.read_text(encoding="utf8").splitlines():
        words = line.split("#", 1)[0].split()
        if not words:
            continue
        kind, values = words[0], words[1:]
        if kind == "v" and len(values) == 3:
            positions.append(tuple(float(x) for x in values))
        elif kind == "vt" and len(values) == 2:
            uvs.append(tuple(float(x) for x in values))
        elif kind == "f" and len(values) == 3:
            face = []
            for item in values:
                ids = item.split("/")
                if len(ids) < 2 or not ids[0] or not ids[1]:
                    raise ValueError("OBJ requires original vertex/UV identities")
                v, uv = int(ids[0]) - 1, int(ids[1]) - 1
                if not 0 <= v < len(layout["positions"]) or not 0 <= uv < len(uvs):
                    raise ValueError("OBJ index outside original mesh")
                if any(abs(a - b) > 1e-7 for a, b in zip(uvs[uv], layout["uvs"][v])):
                    raise ValueError("OBJ changed UVs or reordered vertices")
                face.append(v)
            faces.append(tuple(face))
        elif kind in ("o", "g", "s", "usemtl", "mtllib", "vn"):
            continue
        else:
            raise ValueError("Unsupported OBJ statement: " + kind)
    if faces != layout["faces"] or len(positions) != len(layout["positions"]):
        raise ValueError("OBJ must preserve ordered triangles and vertex count")
    if not all(math.isfinite(x) and abs(x) < 1000 for v in positions + uvs for x in v):
        raise ValueError("OBJ contains invalid coordinates")
    if any(math.dist(a, b) > 20 for a, b in zip(positions, layout["positions"])):
        raise ValueError("Garment displacement exceeds conservative 20-unit limit")

    def normal(points, face):
        a, b, c = [points[i] for i in face]
        u, v = [b[i] - a[i] for i in range(3)], [c[i] - a[i] for i in range(3)]
        return (
            u[1] * v[2] - u[2] * v[1],
            u[2] * v[0] - u[0] * v[2],
            u[0] * v[1] - u[1] * v[0],
        )

    for face in faces:
        old, new = normal(layout["positions"], face), normal(positions, face)
        old_length, new_length = math.hypot(*old), math.hypot(*new)
        if old_length > 1e-8 and (
            new_length < 0.01 * old_length or sum(a * b for a, b in zip(old, new)) <= 0
        ):
            raise ValueError("OBJ collapsed or inverted a garment triangle")
    # Export rounding must not turn an unchanged model into a binary edit.
    return [
        a if max(abs(x - y) for x, y in zip(a, b)) < 1e-6 else b
        for a, b in zip(layout["positions"], positions)
    ]


def export_iff(source, output):
    source = Path(source)
    out = safe_output(output, [source])
    if out.exists() and any(out.iterdir()):
        raise ValueError("Choose an empty model export directory")
    iff = StandardIFF(source.read_bytes())
    pairs = _pairs(iff)
    out.mkdir(parents=True, exist_ok=True)
    models = []
    for r, c, sb, cb, layout, start, mapping in pairs:
        name = r["name"] + ".obj"
        write_obj(out / name, layout["positions"], layout["uvs"], layout["faces"])
        models.append(
            {
                "obj": name,
                "record": r["index"],
                "name": r["name"],
                "vertices": len(mapping),
                "triangles": len(layout["faces"]),
            }
        )
    manifest = {
        "schema": SCHEMA,
        "source_sha256": digest(iff.raw),
        "source_name": source.name,
        "models": models,
        "warning": WARNING,
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf8"
    )
    return manifest


def import_iff(source, edited, output):
    source, edited = Path(source), Path(edited)
    target = safe_output(output, [source, edited])
    if target.exists():
        raise ValueError(
            "Choose a new output IFF; source and existing files stay intact"
        )
    iff = StandardIFF(source.read_bytes())
    manifest = json.loads((edited / "manifest.json").read_text(encoding="utf8"))
    if manifest.get("schema") != SCHEMA or manifest.get("source_sha256") != digest(
        iff.raw
    ):
        raise ValueError("Model manifest does not match the original IFF")
    pairs = _pairs(iff)
    expected = [
        {
            "obj": r["name"] + ".obj",
            "record": r["index"],
            "name": r["name"],
            "vertices": len(mapping),
            "triangles": len(layout["faces"]),
        }
        for r, c, sb, cb, layout, start, mapping in pairs
    ]
    if manifest.get("models") != expected:
        raise ValueError("Model manifest identities/counts changed")
    changes, changed_vertices, changed_constraints = {}, 0, 0
    for r, c, sb, cb, layout, start, mapping in pairs:
        obj = edited / (r["name"] + ".obj")
        if obj.is_symlink():
            raise ValueError("Linked model input is not supported")
        positions = read_obj(obj, layout)
        new_s, new_c = bytearray(sb), bytearray(cb)
        particles = {}
        for i, (old, new, particle) in enumerate(
            zip(layout["positions"], positions, mapping)
        ):
            packed = struct.pack(">3f", *new)
            if particle in particles and particles[particle] != packed:
                raise ValueError(
                    "OBJ split a sewn cloth particle; move seam duplicates together"
                )
            particles[particle] = packed
            if new != old:
                struct.pack_into(">3f", new_s, layout["position_start"] + i * 24, *new)
                new_c[start + particle * 16 : start + particle * 16 + 12] = packed
                changed_vertices += 1
        from .cloth_constraints import retarget_distances

        new_c, adapted = retarget_distances(cb, bytes(new_c))
        changed_constraints += adapted
        # Validate structural layout and exact SCNE/Clth agreement after edits.
        check = _layout(bytes(new_s))
        _cloth(bytes(new_c), check["positions"])
        changes[r["index"]] = [bytes(new_s)]
        changes[c["index"]] = [bytes(new_c)]
    try:
        result = replace_records(iff, changes)
    except ToolError as error:
        if error.code != "archive_extent_capacity_exceeded":
            raise
        from ..formats.standard_iff_writer import replace_records_expanding

        result = replace_records_expanding(iff, changes)
    checked = StandardIFF(result)
    if [r["offsets"] for r in checked.records] != [r["offsets"] for r in iff.records]:
        raise ValueError("Uniform edit unexpectedly relocated logical records")
    for old in iff.records:
        wanted = changes.get(old["index"], [b[3] for b in record_blocks(iff, old)])
        if [
            b[3] for b in record_blocks(checked, checked.records[old["index"]])
        ] != wanted:
            raise ValueError("Untouched record preservation failed")
    from ..formats.compression import decode

    for before, after in zip(iff.blocks, checked.blocks):
        old = decode(
            iff.raw[before["start"] : before["start"] + before["size"]],
            before["logical_size"],
        )
        actual = decode(
            result[after["start"] : after["start"] + after["size"]],
            after["logical_size"],
        )
        expected = bytearray(old)
        for index, parts in changes.items():
            for (block, start, end, data), replacement in zip(
                record_blocks(iff, iff.records[index]), parts
            ):
                if block == before["index"]:
                    expected[start:end] = replacement
        if actual != expected:
            raise ValueError("Unreferenced logical bytes changed during uniform edit")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as stream:
        stream.write(result)
    return {
        "models": len(pairs),
        "changed_vertices": changed_vertices,
        "changed_constraints": changed_constraints,
        "warning": WARNING,
    }


def modern_positions(positions, shorts=False):
    """Shorts hem +20% of length; jersey torso circumference minus up to 7%.

    Keep the shorts waist/hips and jersey collar/armhole region fixed. Transform
    every coincident seam vertex identically. Do not change body/build routing.
    """
    low, high = min(v[1] for v in positions), max(v[1] for v in positions)
    span = high - low
    if span <= 0:
        raise ValueError("Degenerate garment height")

    def smooth(t):
        t = max(0.0, min(1.0, t))
        return t * t * (3 - 2 * t)

    result = []
    for x, y, z in positions:
        t = (y - low) / span
        if shorts:
            y += span * 0.20 * (1 - smooth(t / 0.65))
        else:
            amount = 0.07 * smooth(t / 0.15) * (1 - smooth((t - 0.50) / 0.22))
            x, z = x * (1 - amount), z * (1 - amount)
        result.append((x, y, z))
    return result


def import_folder(edited, output, job=None):
    """Reimport an exported collection into a new standalone overrides folder."""
    edited = Path(edited)
    out = safe_output(output, [edited])
    if out.exists() and any(out.iterdir()):
        raise ValueError("Choose an empty output folder")
    sources = sorted((edited / "originals").glob("*.iff"))
    if not sources or any(not CONTAINER.fullmatch(p.name) for p in sources):
        raise ValueError(
            "Choose an exported uniform collection with original cloth IFFs"
        )
    from ..core.paths import reject_links

    reject_links(edited)
    rows = []
    for i, source in enumerate(sources):
        if job:
            job.check()
            job.progress(i, len(sources), source.name)
        report = import_iff(source, edited / "models" / source.stem, out / source.name)
        rows.append({"archive": source.name, **report})
    result = {"schema": SCHEMA, "archives": rows, "warning": WARNING}
    out.mkdir(parents=True, exist_ok=True)
    (out / "uniform-import.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf8"
    )
    return result


def export_archive(archive, output, modern=False, job=None):
    """Export every supplied existing garment container; never create a JB."""
    out = safe_output(output, [archive.path])
    if out.exists() and any(out.iterdir()):
        raise ValueError("Choose an empty uniform output directory")
    entries = [e for e in archive.entries if CONTAINER.fullmatch(e.get("name") or "")]
    if not entries:
        raise ValueError("No named College Hoops cloth containers in this source")
    names = [e["name"].casefold() for e in entries]
    if len(set(names)) != len(names):
        raise ValueError("Ambiguous cloth container names")
    # Validate the complete set before writing any files.
    inputs = [(e, archive.read(e)) for e in entries]
    for e, raw in inputs:
        _pairs(StandardIFF(raw))
    rows = []
    for index, (entry, raw) in enumerate(inputs):
        if job:
            job.check()
            job.progress(index, len(inputs), entry["name"])
        name = entry["name"]
        source = out / "originals" / name
        source.parent.mkdir(parents=True, exist_ok=True)
        with source.open("xb") as stream:
            stream.write(raw)
        folder = out / "models" / name.removesuffix(".iff")
        manifest = export_iff(source, folder)
        if modern:
            export_iff(source, out / "original-models" / name.removesuffix(".iff"))
            for r, c, sb, cb, layout, start, mapping in _pairs(StandardIFF(raw)):
                positions = modern_positions(
                    layout["positions"], r["name"].startswith("shorts")
                )
                write_obj(
                    folder / (r["name"] + ".obj"),
                    positions,
                    layout["uvs"],
                    layout["faces"],
                )
            report = import_iff(source, folder, out / "overrides" / name)
        else:
            report = {"models": len(manifest["models"]), "changed_vertices": 0}
        rows.append({"archive": name, **report})
    result = {
        "schema": SCHEMA,
        "preset": "modern-fit-2" if modern else None,
        "archives": rows,
        "warning": WARNING,
    }
    (out / "uniforms.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf8"
    )
    (out / "README.md").write_text(
        "# Editable College Hoops uniforms\n\n"
        "originals/: immutable source IFF copies used for reimport identity checks.\n"
        "models/: editable OBJ cages and per-container manifests.\n"
        "original-models/: untouched OBJ cages (modern-fit exports only).\n"
        "overrides/: edited complete IFF replacements (modern-fit exports only).\n\n"
        "Modern fit: shorts hem raised by 20% of original mesh height; waist and\n"
        "upper hips fixed. Jersey torso circumference reduced by up to 7%;\n"
        "collar/upper armholes and bottom attachment row fixed. All existing\n"
        "necklines/builds are included; these shared meshes affect every team.\n\n"
        "In Blender, keep vertex order on OBJ import/export, preserve coordinates\n"
        "(Y is up in these files), and apply no topology-changing modifiers.\n"
        "Keep all seam duplicates together; do not weld, delete, subdivide,\n"
        "retriangulate, reorder triangles or alter UVs. Export selected garment\n"
        "alone back to its original OBJ path. Import validates the original IFF\n"
        "hash, UV identity, topology, seams, finite coordinates and triangle flips.\n"
        "It writes positions in SCNE/Clth and adapts native stretch/bend lengths\n"
        "while preserving their authored slack/prestrain ratios.\n\n"
        "Reimport through Models / Courts > Uniform meshes > Reimport edited\n"
        "uniform models, choosing this collection root; or use:\n\n"
        "    python -m choops_py.cli import-uniform-models "
        "COLLECTION output/edited-uniforms\n\n"
        "To test the ready models, select ONLY overrides/ as an overrides folder\n"
        "in Explorer. Do not select the collection root: it contains originals.\n"
        "Do not combine these complete IFFs with another cloth geometry mod.\n\n"
        + WARNING
        + "\n\n"
        "This is a rest-pose experiment, not a certified animation/cloth port.\n"
        "No EBOOT, source JB, uniform artwork or roster is modified.\n",
        encoding="utf8",
    )
    if job:
        job.progress(len(inputs), len(inputs), "Uniform meshes exported")
    return result
