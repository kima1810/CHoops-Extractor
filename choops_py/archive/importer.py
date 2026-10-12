"""One hashed staging manifest for whole archives, subfiles and edited DDS."""
from pathlib import Path
import json
from ..archive.manifests import safe_output,write_bytes,digest
from ..core.reports import save_json
from ..core.errors import ToolError
from ..formats.standard_iff import StandardIFF
from ..texture_tools.dds import inspect as inspect_dds

def asset_name(name):
    if not name or Path(name).name!=name or '/' in name or '\\' in name or ':' in name or name in ('.','..'):
        raise ToolError('unsafe_archive_name','Archive identity must be a plain filename')
    return name

def listing(mod):
    p=Path(mod)/'overrides.json'
    data=json.loads(p.read_text(encoding='utf-8')) if p.exists() else []
    if not isinstance(data,list):raise ToolError('invalid_mod_manifest','Expected a list of overrides')
    return data

def stage(mod,file,iff,sub=None):
    mod=safe_output(mod,[file]);name=asset_name(iff);source=Path(file);data=source.read_bytes();rows=listing(mod)
    if any(r['archive'].lower()==name.lower() and r['subfile']==sub for r in rows):raise ToolError('duplicate_override','Remove the existing staging entry before importing this target again')
    kind='dds' if source.suffix.lower()=='.dds' else 'subfile' if sub is not None else 'archive'
    if kind=='dds':
        if not sub:raise ToolError('texture_selector_required','DDS staging requires --sub texture name or SCNE/texture_N')
        inspect_dds(data)
    elif kind=='archive' and source.suffix.lower()=='.iff' and data[:4]==bytes.fromhex('ff3bef94'):StandardIFF(data)
    target=f'assets/{len(rows):04d}.bin';write_bytes(mod/target,data,[file]);row={'archive':name,'subfile':sub,'kind':kind,'original_name':source.name,'path':target,'sha256':digest(data),'size':len(data)}
    rows.append(row);save_json(mod/'overrides.json',rows,[file]);return row

def validate(mod):
    mod=Path(mod).resolve();rows=listing(mod);targets=set()
    for row in rows:
        asset_name(row['archive']);key=(row['archive'].lower(),row['subfile'])
        if key in targets:raise ToolError('duplicate_override',str(key))
        targets.add(key);path=(mod/row['path']).resolve()
        if not path.is_relative_to(mod) or path.is_symlink():raise ToolError('unsafe_mod_path','Staged file escapes mod folder')
        data=path.read_bytes()
        if digest(data)!=row['sha256'] or len(data)!=row['size']:raise ToolError('staged_asset_changed','Reimport changed assets so their fingerprints are reviewed')
        if row.get('kind')=='dds':inspect_dds(data)
        elif row['subfile'] is None and row['archive'].lower().endswith('.iff'):
            if data[:4]==bytes.fromhex('ff3bef94'):StandardIFF(data)
            elif data[:4]!=bytes.fromhex('f0985030'):raise ToolError('invalid_iff_override','Unrecognized PS3 IFF magic')
    return rows
