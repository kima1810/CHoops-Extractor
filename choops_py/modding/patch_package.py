"""Source-bound XOR patch packages; no original or unchanged game bytes."""

from __future__ import annotations

import hashlib
import json
import shutil
import uuid
import zipfile
from pathlib import Path

from ..archive.build_copy import preflight
from ..archive.importer import asset_name, stage
from ..archive.manifests import safe_output
from ..archive.usrdir_reader import Archive
from ..core.reports import save_json

MAX_ENTRY = 128 * 1024 * 1024
MAX_TOTAL = 512 * 1024 * 1024


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def export_patch(source: Path, mod: Path, output: Path) -> dict:
    archive, patches = preflight(source, mod)
    output = safe_output(output, [source, mod])
    if output.exists():
        raise ValueError("Patch output already exists")
    if not patches or sum(len(data) for _, data in patches) > MAX_TOTAL:
        raise ValueError("Empty mod or patch exceeds 512 MiB limit")
    if any(len(data) > MAX_ENTRY for _, data in patches):
        raise ValueError("Patch entry exceeds 128 MiB limit")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(".patch_" + uuid.uuid4().hex)
    entries = []
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as package:
            for i, (entry, edited) in enumerate(patches):
                original = archive.read(entry)
                if len(original) != len(edited):
                    raise ValueError("Only allocation-preserving patches supported")
                delta = bytes(a ^ b for a, b in zip(original, edited))
                name = f"{i:04d}.xor"
                package.writestr(name, delta)
                entries.append(
                    {
                        "index": entry["index"],
                        "hash": entry["hash"],
                        "name": entry["name"],
                        "size": len(original),
                        "source_sha256": sha(original),
                        "result_sha256": sha(edited),
                        "delta": name,
                        "delta_sha256": sha(delta),
                    }
                )
            package.writestr(
                "manifest.json",
                json.dumps(
                    {"schema": 1, "kind": "choops-xor-patch", "entries": entries}
                ),
            )
        # Exclusive publish; no overwrite of a concurrently created destination.
        import os

        os.link(temporary, output)
        return {
            "status": "success",
            "entries": len(entries),
            "bytes": output.stat().st_size,
            "sha256": sha(output.read_bytes()),
        }
    finally:
        if temporary.exists():
            temporary.unlink()


def import_patch(source: Path, package_path: Path, mod: Path) -> dict:
    archive = Archive(source)
    mod = safe_output(mod, [source, package_path])
    if mod.exists():
        raise ValueError("Choose a new mod workspace")
    work = mod.parent / (".patch_import_" + uuid.uuid4().hex)
    input_folder = work / "inputs"
    staged = work / "mod"
    conditions = []
    try:
        with zipfile.ZipFile(package_path) as package:
            infos = package.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)) or "manifest.json" not in names:
                raise ValueError("Duplicate ZIP member or missing manifest")
            if package.getinfo("manifest.json").file_size > 1024 * 1024:
                raise ValueError("Patch manifest exceeds limit")
            manifest = json.loads(package.read("manifest.json"))
            if not isinstance(manifest, dict):
                raise TypeError("Patch manifest must be an object")
            if (
                manifest.get("schema") != 1
                or manifest.get("kind") != "choops-xor-patch"
            ):
                raise ValueError("Unsupported patch schema")
            entries = manifest["entries"]
            if not isinstance(entries, list) or not entries or len(entries) > 10000:
                raise ValueError("Invalid patch entry count")
            expected_names = {"manifest.json"} | {
                f"{i:04d}.xor" for i in range(len(entries))
            }
            if (
                set(names) != expected_names
                or sum(info.file_size for info in infos) > MAX_TOTAL + 1024 * 1024
            ):
                raise ValueError("Unexpected ZIP members or oversized patch")
            ids = set()
            # All source/delta preconditions are checked before staged publication.
            for i, row in enumerate(entries):
                if not isinstance(row, dict):
                    raise TypeError("Patch entry must be an object")
                index = row["index"]
                if (
                    isinstance(index, bool)
                    or not isinstance(index, int)
                    or not 0 <= index < len(archive.entries)
                    or index in ids
                ):
                    raise ValueError("Duplicate or invalid TOC index")
                ids.add(index)
                entry = archive.entries[index]
                if (
                    entry["hash"] != row["hash"]
                    or entry["name"] != row["name"]
                    or entry["size"] != row["size"]
                ):
                    raise ValueError("Patch archive identity/version mismatch")
                if not entry["name"]:
                    raise ValueError("Unresolved archive identity cannot be staged")
                delta_name = f"{i:04d}.xor"
                size = row["size"]
                if (
                    row["delta"] != delta_name
                    or not 0 < size <= MAX_ENTRY
                    or package.getinfo(delta_name).file_size != size
                ):
                    raise ValueError("Patch extent or delta length mismatch")
                original = archive.read(entry)
                if sha(original) != row["source_sha256"]:
                    raise ValueError("Patch original source SHA-256 mismatch")
                delta = package.read(delta_name)
                if sha(delta) != row["delta_sha256"]:
                    raise ValueError("Patch delta SHA-256 mismatch")
                edited = bytes(a ^ b for a, b in zip(original, delta))
                if sha(edited) != row["result_sha256"]:
                    raise ValueError("Patch result SHA-256 mismatch")
                input_folder.mkdir(parents=True, exist_ok=True)
                asset_name(entry["name"])
                replacement = input_folder / entry["name"]
                # Name safety was checked by archive identity resolution and stage.
                if replacement.name != entry["name"]:
                    raise ValueError("Unsafe patch filename")
                replacement.write_bytes(edited)
                stage(staged, replacement, entry["name"])
                conditions.append(
                    {"index": index, "hash": entry["hash"], "sha256": sha(original)}
                )
        save_json(
            staged / "source_preconditions.json", {"schema": 1, "entries": conditions}
        )
        preflight(source, staged)
        mod.parent.mkdir(parents=True, exist_ok=True)
        staged.rename(mod)
        return {"status": "success", "entries": len(conditions), "mod": str(mod)}
    except (zipfile.BadZipFile, KeyError, TypeError) as error:
        raise ValueError(f"Invalid mod patch: {error}") from error
    finally:
        if work.exists():
            shutil.rmtree(work)
