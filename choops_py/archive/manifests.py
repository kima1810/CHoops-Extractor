from pathlib import Path
import json, hashlib, sys
def resolved_path(path):
    """Treat Win32 extended drive/UNC spellings as the same resolved location."""
    value = str(Path(path).resolve())
    if value.startswith('\\\\?\\UNC\\'):
        value = '\\\\' + value[8:]
    elif value.startswith('\\\\?\\') and len(value) > 6 and value[5:7] == ':\\':
        value = value[4:]
    return Path(value)

ROOT=resolved_path(sys.executable).parent if getattr(sys,'frozen',False) else resolved_path(__file__).parents[2]
def output_root():
    """Keep a frozen Mac app's writable data outside its signed bundle."""
    if getattr(sys, 'frozen', False) and sys.platform == 'darwin':
        return Path.home()/'Library'/'Application Support'/'CHoops Studio'/'output'
    return ROOT/'output'

OUTPUT=output_root()
def source_root(path):
    p=resolved_path(path)
    for candidate in [p,*p.parents]:
        if (candidate/"PS3_GAME").is_dir(): return candidate
    return p if p.is_dir() else p.parent
def safe_output(path, sources=()):
    p=resolved_path(path)
    if not p.is_relative_to(resolved_path(OUTPUT)): raise ValueError("All outputs must be under project output/")
    for s in sources:
        source=resolved_path(s)
        protected=source_root(s)
        if source.is_file() and protected==source.parent:
            if p==source: raise ValueError("Output would overwrite input")
        elif p.is_relative_to(protected): raise ValueError("Output is inside input/source folder")
    return p

def build_destination(path, sources=()):
    """User-chosen JB destination, including other drives; never a source tree."""
    raw=Path(path).absolute()
    for parent in (raw,*raw.parents):
        if parent.is_symlink() or (hasattr(parent,'is_junction') and parent.is_junction()):
            raise ValueError('Build destination must not traverse links or junctions')
    p=resolved_path(raw)
    if p==Path(p.anchor) or p==resolved_path(ROOT) or resolved_path(ROOT).is_relative_to(p):
        raise ValueError('Choose a separate named build folder')
    for value in sources:
        source=resolved_path(source_root(value))
        if p.is_relative_to(source) or source.is_relative_to(p):
            raise ValueError('Build destination overlaps an input/source folder')
    return p
def write_bytes(path,data,sources=()):
    p=safe_output(path,sources)
    if p.exists(): raise ValueError(f"Output exists: {p}")
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f: f.write(data)
    return p
def report(path,data,sources=()): return write_bytes(path,(json.dumps(data,indent=2)+"\n").encode(),sources)
def digest(data): return hashlib.sha256(data).hexdigest()
def safe_name(name):
    import re
    return re.sub(r'[^A-Za-z0-9_.-]', '_',str(name)).strip('.') or 'unnamed'
