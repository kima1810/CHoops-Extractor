from pathlib import Path
import hashlib
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def validate(base,mod):
    base=Path(base);mod=Path(mod);rows=[]
    for p in base.rglob('*'):
        if p.is_file():
            rel=p.relative_to(base);q=mod/rel
            rows.append(dict(path=str(rel),exists=q.is_file(),same_size=q.is_file() and q.stat().st_size==p.stat().st_size,unchanged=q.is_file() and sha(p)==sha(q)))
    return dict(valid=all(r['exists'] and r['same_size'] for r in rows),scope='file inventory, sizes and hashes; changed bytes are reported, not console certified',files=rows)
