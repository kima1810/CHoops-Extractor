import hashlib,json
from .usrdir_reader import Archive,usrdir
from .manifests import OUTPUT,report,safe_output
def cache_path(path):return OUTPUT/'cache'/(hashlib.sha256(str(usrdir(path)).encode()).hexdigest()[:16]+'.json')
def fingerprint(a):return [{'name':p['name'],'size':p['size'],'mtime_ns':(a.path/p['name']).stat().st_mtime_ns} for p in a.parts]
def build(path):
    a=Archive(path);p=safe_output(cache_path(path),[a.path])
    if p.exists():p.unlink()
    report(p,dict(schema=3,source=str(a.path),fingerprint=fingerprint(a),entries=a.entries),[a.path]);return p
def info(path):
    a=Archive(path);p=safe_output(cache_path(path),[a.path])
    if not p.exists():raise ValueError("Cache missing; run build-cache")
    data=json.loads(p.read_text())
    if data.get('schema')!=3:raise ValueError('Outdated archive cache; run build-cache')
    if data['fingerprint']!=fingerprint(a):raise ValueError("Stale cache")
    return data
