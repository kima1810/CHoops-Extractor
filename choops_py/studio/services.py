"""Application services shared by the native studio and automation."""

from __future__ import annotations

import hashlib
import os
import threading
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..archive.manifests import OUTPUT, safe_name, safe_output
from ..archive.usrdir_reader import Archive
from ..core.reports import save_json


class Cancelled(Exception):
    """A cooperative job cancellation; completed exports remain recorded."""


class JobContext:
    def __init__(self, progress: Callable[[int, int, str], None] | None = None):
        self.cancelled = threading.Event()
        self.progress = progress or (lambda current, total, message: None)

    def check(self):
        if self.cancelled.is_set():
            raise Cancelled("Cancelled by user")


def extract(
    archive: Archive, entries: list[dict], output: Path, job: JobContext | None = None
) -> dict:
    """Stream raw extents with collision preflight and per-entry atomic writes."""
    job = job or JobContext()
    out = safe_output(output, [archive.path])
    # Pair known outer IFF/CDF identities; raw data is retained even if decode fails.
    name_index: dict[str, list[dict]] = {}
    for item in archive.entries:
        if item["name"]:
            name_index.setdefault(item["name"].casefold(), []).append(item)
    selected_ids = {e["index"] for e in entries}
    expanded = list(entries)
    for entry in entries:
        name = entry.get("name")
        if name and Path(name).suffix.lower() in (".iff", ".cdf"):
            partner = str(
                Path(name).with_suffix(
                    ".cdf" if name.lower().endswith(".iff") else ".iff"
                )
            )
            matches = name_index.get(partner.casefold(), [])
            if len(matches) == 1 and matches[0]["index"] not in selected_ids:
                expanded.append(matches[0])
                selected_ids.add(matches[0]["index"])
    entries = expanded
    targets = []
    seen = set()
    for entry in entries:
        name = safe_name(entry["name"] or f"hash_{entry['hash']:08x}.bin")
        key = name.casefold()
        if key in seen or (out / name).exists():
            raise ValueError(f"Duplicate or existing extraction target: {name}")
        seen.add(key)
        targets.append((entry, name))
    if not targets:
        raise ValueError("No assets selected")
    if (out / "extraction_manifest.json").exists():
        raise ValueError("Choose a new extraction destination")
    out.mkdir(parents=True, exist_ok=True)
    total = sum(e["size"] for e, _ in targets)
    done = 0
    rows = []
    status = "complete"
    try:
        for entry, name in targets:
            job.check()
            target = out / name
            temporary = out / (".extract_" + uuid.uuid4().hex)
            h = hashlib.sha256()
            try:
                with temporary.open("xb") as stream:
                    for chunk in archive.chunks(entry):
                        job.check()
                        stream.write(chunk)
                        h.update(chunk)
                        done += len(chunk)
                        job.progress(done, total, name)
                # Exclusive target creation avoids overwriting a concurrent export.
                os.link(temporary, target)
                temporary.unlink()
            finally:
                if temporary.exists():
                    temporary.unlink()
            rows.append({**entry, "output": name, "sha256": h.hexdigest()})
    except Cancelled:
        status = "cancelled"
    except KeyboardInterrupt:
        status = "cancelled"
        raise
    except Exception:
        status = "failed"
        raise
    finally:
        result = {
            "schema": 1,
            "status": status,
            "requested": len(targets),
            "completed": len(rows),
            "bytes_written": sum(row["size"] for row in rows),
            "entries": rows,
        }
        save_json(out / "extraction_manifest.json", result, [archive.path])
    return result


def materialize(archive: Archive, entry: dict, directory: Path | None = None) -> Path:
    """Create a private scratch copy for parsers requiring a filesystem input."""
    directory = directory or OUTPUT / "temp" / ("inspect_" + uuid.uuid4().hex)
    selected = [entry]
    if entry["name"] and entry["name"].lower().endswith(".iff"):
        companion = entry["name"][:-4] + ".cdf"
        selected += [e for e in archive.entries if e["name"] == companion]
    extract(archive, selected, directory)
    name = safe_name(entry["name"] or f"hash_{entry['hash']:08x}.bin")
    return directory / name


def inspect_asset(path: Path) -> dict:
    """Return nested records and texture candidates without guessing writers."""
    from ..formats.cdf_backed_iff import CDFPair
    from ..formats.standard_iff import StandardIFF
    from ..texture_tools.pipeline import Container

    if path.stat().st_size > 128 * 1024 * 1024:
        with path.open("rb") as stream:
            header = stream.read(4096)
        return {
            "path": path,
            "records": [],
            "textures": [],
            "hex": header,
            "warning": "Interactive decode limit is 128 MiB; streamed raw extraction remains available.",
        }
    raw = path.read_bytes()
    records = []
    cdf = path.with_suffix(".cdf")
    if raw[:4] == bytes.fromhex("ff3bef94"):
        records = StandardIFF(raw).records
    elif raw[:4] == bytes.fromhex("f0985030") and cdf.exists():
        records = CDFPair(raw, cdf.read_bytes()).records
    assets = []
    warning = ""
    try:
        container = Container(path, cdf if cdf.exists() else None)
        for asset in container.assets:
            try:
                info = asset.texture.info() if asset.texture else {}
            except ValueError as error:
                info = {"reason": str(error)}
            assets.append(
                {
                    "name": asset.name,
                    "kind": asset.kind,
                    "metadata": info,
                    "warnings": asset.warnings,
                    "editable": asset.texture is not None,
                }
            )
    except ValueError as error:
        warning = str(error)
    return {
        "path": path,
        "records": records,
        "textures": assets,
        "hex": raw[:4096],
        "warning": warning,
    }


def stage_folder(source: Path, folder: Path, mod: Path, job=None) -> dict:
    """Compile recursive records first, then overlay DDS artwork atomically."""
    import shutil
    from ..archive.folder_import import discover,compile_group
    from ..archive.build_copy import preflight
    from ..archive.manifests import write_bytes
    archive=Archive(source);folder=Path(folder);mod=safe_output(mod,[source,folder])
    if mod.exists():raise ValueError('Choose a new mod directory')
    job=job or JobContext();discovery=discover(archive,folder,job)
    work=mod.parent/('.mod_'+uuid.uuid4().hex);rows: list[dict]=[];conditions=[];growth=[];unchanged=0
    details=[];unapplied: list[dict]=[]
    try:
        for i,group in enumerate(discovery['groups']):
            job.check();job.progress(i,len(discovery['groups']),'Compile override '+group['name'])
            original=archive.read(group['entry'])
            try:data,imports=compile_group(archive,group,job)
            except (ValueError,OSError) as error:raise ValueError(group['name']+': '+str(error)) from error
            unapplied.extend(dict(archive=group['name'],**item) for item in imports if item.get('status')=='unmatched')
            if data==original and group['whole'] is None and not group.get('compiled_companion'):unchanged+=1;continue
            target=f'assets/{len(rows):04d}.bin';write_bytes(work/target,data,[source,folder])
            rows.append(dict(archive=group['name'],subfile=None,kind='archive',original_name=group['name'],path=target,sha256=hashlib.sha256(data).hexdigest(),size=len(data)))
            conditions.append(dict(index=group['entry']['index'],hash=group['entry']['hash'],sha256=hashlib.sha256(original).hexdigest()))
            details.append(dict(archive=group['name'],binary_records=len(group['records']),dds_imports=imports))
            if len(data)>len(original):growth.append(dict(archive=group['name'],old_bytes=len(original),new_bytes=len(data)))
            if group.get('compiled_companion'):
                entry,name,payload=group['compiled_companion'];target=f'assets/{len(rows):04d}.bin'
                write_bytes(work/target,payload,[source,folder])
                rows.append(dict(archive=name,subfile=None,kind='archive',original_name=name,path=target,sha256=hashlib.sha256(payload).hexdigest(),size=len(payload)))
                before=archive.read(entry)
                conditions.append(dict(index=entry['index'],hash=entry['hash'],sha256=hashlib.sha256(before).hexdigest()))
                if len(payload)>len(before):growth.append(dict(archive=name,old_bytes=len(before),new_bytes=len(payload)))
        names=[row['archive'].casefold() for row in rows]
        if len(names)!=len(set(names)):raise ValueError('A paired CDF texture import conflicts with a complete CDF replacement')
        if not rows:raise ValueError('All discovered overrides match the selected game; no changes to stage')
        save_json(work/'overrides.json',rows,[source,folder])
        save_json(work/'source_preconditions.json',dict(schema=1,entries=conditions),[source,folder])
        save_json(work/'import_options.json',dict(schema=1,allow_archive_growth=True,dds_priority=True,scne_priority=True),[source,folder])
        report=dict(staged=len(rows),mod=str(mod),detected_formats=discovery['detected_formats'],scanned_files=discovery['scanned_files'],dds_files=discovery['dds_files'],binary_records=discovery['binary_records'],ignored_files=discovery['ignored_files'],shadowed_dds=discovery['shadowed_dds'],resolved_targets=discovery['resolved_targets'],unapplied_overrides=unapplied,unchanged_archives=unchanged,growing_archives=growth,dds_priority=True,scne_priority=True,imports=details)
        save_json(work/'folder_import_report.json',report,[source,folder])
        job.check();job.progress(0,1,'Validating staged overrides')
        _,patches=preflight(source,work,job)
        work.rename(mod)
        return {key:value for key,value in report.items() if key!='imports'}
    except BaseException:
        if work.exists() and work.resolve().is_relative_to(OUTPUT.resolve()):shutil.rmtree(work)
        raise


def decode_texture_preview(source: Path, selector: str):
    from ..texture_tools.pipeline import Container
    cdf = source.with_suffix('.cdf')
    asset = Container(source, cdf if cdf.exists() else None).select(selector)
    return decode_preview_asset(asset)


def decode_preview_asset(asset, max_size=2048):
    import shutil
    from PIL import Image
    from ..texture_tools.external_converters import convert
    info = asset.texture.info()
    work = OUTPUT / 'temp' / ('preview_' + uuid.uuid4().hex)
    work.mkdir(parents=True)
    try:
        dds = work / 'texture.dds'
        gtf = work / 'texture.gtf'
        gtf.write_bytes(asset.texture.gtf())
        convert('gtf2dds', gtf, dds)
        with Image.open(dds) as image:
            image.load()
            image.thumbnail((max_size, max_size))
            image = image.convert('RGBA')
            from ..texture_tools.gtf import remap_preview
            image=remap_preview(image,info['remap'])
            return image.size, image.tobytes()
    finally:
        shutil.rmtree(work)


def inspect_scene_preview(source: Path, record_index: int, include_all=False, job=None):
    from ..texture_tools.pipeline import Container
    from ..formats.standard_iff_writer import record_blocks
    from ..formats.compression import decode
    from ..formats.tool_wrapper import unwrap
    from ..formats.scne import preview_meshes
    job = job or JobContext()
    if source.stat().st_size > 128 * 1024 * 1024:
        raise ValueError('Interactive scene decode limit is 128 MiB')
    cdf = source.with_suffix('.cdf')
    container = Container(source, cdf if cdf.exists() else None)
    records = container.iff.records if container.iff else container.pair.records if container.pair else []
    scene_records = [r for r in records if r['type'] == 'SCNE']
    # Same-name records in cloth packages are alternative rest-pose/LOD
    # sections, not separate arena/floor components to superimpose.
    if len(scene_records)>1 and len({r['name'] for r in scene_records})==1:
        selected_record=next((r for r in scene_records if r['index']==record_index),scene_records[0])
        scenes=[selected_record]
    else:
        scenes=[r for r in scene_records if include_all or r['index']==record_index]
    if not scenes and (container.wrapper_type == 2 or container.kind == "raw-scne"):
        scenes = [{'index': 0, 'name': source.stem}]
    if not scenes:
        raise ValueError('Select a SCNE record in an IFF or open a SCNE wrapper')
    result: dict[str, Any] = {'meshes': [], 'warnings': [], 'textures': [], 'images': {}}
    for rec in scenes:
        job.check()
        if container.iff:
            blocks = [b[3] for b in record_blocks(container.iff, rec)]
        elif container.pair:
            blocks = [decode(container.pair.cdf[rec[k+'_offset']:rec[k+'_offset']+rec[k+'_length']]) for k in ('header','payload')]
        else:
            blocks = [container.raw] if container.kind == "raw-scne" else unwrap(container.raw)[1]
        scene = preview_meshes(blocks)
        if len(blocks) == 1 and scene['meshes']:
            scene['warnings'].append('Static rest-pose preview: runtime skinning, cloth simulation and external material textures are not reproduced')
        assets = [a for a in container.assets if (a.record_index == rec['index'] or container.wrapper_type == 2 or container.kind == 'raw-scne') and a.texture]
        by_index = {a.package_index: a.name for a in assets}
        result['textures'].extend(a.name for a in assets)
        for mesh in scene['meshes']:
            mesh['uniform_surface'] = 'shorts' if 'short' in rec['name'].lower() or 'short' in source.stem.lower() else 'jersey' if 'jersey' in rec['name'].lower() or source.stem.lower().startswith('cloth') else None
            mesh['court_surface'] = rec['name'].lower() == 'floor'
            mesh['name'] = rec['name'] + '/' + mesh['name']
            for batch in mesh['batches']:
                batch['texture'] = by_index.get(batch['texture_index'])
                # This runtime-injected court pass repeats the wood geometry;
                # a neutral diffuse fallback would cover every court decal.
                if mesh['court_surface'] and batch.get('material_hash') == 0xe16ecb73 and batch['texture'] is None:
                    batch['omit_preview'] = True
                    scene['warnings'].append('Court runtime-only material 0xe16ecb73 omitted from color preview')
        result['meshes'].extend(scene['meshes'])
        result['warnings'].extend(scene['warnings'])
    needed = {batch['texture'] for mesh in result['meshes'] for batch in mesh['batches'] if batch['texture']}
    asset_lookup = {a.name:a for a in container.assets if a.texture}
    decoded_bytes = 0
    for i, name in enumerate(sorted(needed)):
        job.check()
        job.progress(i, len(needed), 'Loading material texture ' + name)
        try:
            image = decode_preview_asset(asset_lookup[name], max_size=1024)
            decoded_bytes += len(image[1])
            if decoded_bytes > 128 * 1024 * 1024:
                result['warnings'].append('Scene texture memory limit reached')
                break
            result['images'][name] = image
        except ValueError as error:
            result['warnings'].append(name + ': ' + str(error))
    job.progress(len(needed), len(needed), 'Scene loaded')
    return result


def inspect_uniform_preview(source, job=None):
    """Render authored uniform RGB artwork; normal/number atlases stay separate."""
    from ..texture_tools.pipeline import Container
    source = Path(source)
    if source.stat().st_size > 128*1024*1024:
        raise ValueError('Interactive uniform decode limit is 128 MiB')
    cdf=source.with_suffix('.cdf')
    container=Container(source,cdf if cdf.exists() else None)
    images={}
    for role,names in (('jersey',('unifregion','unif')),('shorts',('shortregion','short'))):
        for record_name in names:
            candidates=[a for a in container.assets if a.name==record_name and a.texture]
            if len(candidates)>1:raise ValueError('Uniform artwork identity is ambiguous: '+record_name)
            if candidates:
                if job:job.check()
                size,raw=decode_preview_asset(candidates[0],max_size=1024)
                # Uniform artwork alpha also carries material information. A
                # cloth rest-pose preview uses opaque RGB, not cutout holes.
                rgba=bytearray(raw);rgba[3::4]=b'\xff'*(len(rgba)//4)
                images[role]=(size,bytes(rgba))
                break
    if not images:raise ValueError('Uniform has no supported jersey or shorts artwork')
    return images


def inspect_shoe_preview(archive,texture_entry,job=None):
    """Preview the standalone shoe mesh with named upper/sole artwork."""
    import re
    from ..formats.standard_iff import StandardIFF
    from ..texture_tools.pipeline import Container
    job=job or JobContext()
    # This hash identifies the stock standalone hi_shoe1 container. Verify its
    # contents on each source; modded JB archives retain their original hashes.
    candidates=sorted(archive.entries,key=lambda e:e['hash']!=4175903001)
    chosen=None
    for entry in candidates:
        if entry['hash']!=4175903001 and entry.get('name') and not re.search('shoe',entry['name'],re.I):continue
        if entry['size']>2*1024*1024:continue
        job.check()
        try:
            raw=archive.read(entry)
            if raw[:4]!=bytes.fromhex('ff3bef94'):continue
            iff=StandardIFF(raw)
            record=next((r for r in iff.records if r['type']=='SCNE' and re.fullmatch(r'(?:hi_|lo_)?shoe\d*',r['name'],re.I)),None)
            if record:chosen=(entry,record['index']);break
        except ValueError:continue
    if chosen is None:raise ValueError('No standalone shoe SCNE mesh found in this JB folder')
    source=materialize(archive,chosen[0])
    result=inspect_scene_preview(source,chosen[1],False,job)
    if not result['meshes']:raise ValueError('Shoe SCNE contains no supported geometry')
    texture_path=materialize(archive,texture_entry)
    container=Container(texture_path)
    images={}
    for role in ('shoe_upper','shoe_sole'):
        assets=[a for a in container.assets if a.texture and a.name==role]
        if len(assets)!=1:raise ValueError('Shoe artwork requires one named '+role+' texture')
        job.check();size,raw=decode_preview_asset(assets[0],max_size=1024)
        # Shoe alpha carries material data, rather than preview transparency.
        opaque=bytearray(raw);opaque[3::4]=b'\xff'*(len(raw)//4)
        images[role]=(size,bytes(opaque))
    upper={'fastener_mat','midsole_mat','toe_mat','heel_mat','logo_mat','hitop_mat','upper_mat'}
    for mesh in result['meshes']:
        mesh['uniform_surface']=None
        for batch in mesh['batches']:
            material=batch.get('material_name')
            if material=='sole_mat':batch['texture']='shoe_sole'
            elif material in upper:batch['texture']='shoe_upper'
            else:result['warnings'].append('Unmapped shoe material: '+str(material))
    result['images'].update(images);result['textures']=list(images)
    result['warnings'].append('Standalone shoe rest pose; texture family does not change the authored shoe silhouette')
    return source,result
