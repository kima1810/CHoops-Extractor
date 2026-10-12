"""Recover canonical names by CRC32; keep internal-record labels separate."""
import hashlib
import json
import re
from pathlib import Path
from .hash_names import hash_name
from .manifests import OUTPUT,safe_output
from .cache import fingerprint
from ..formats.binary import Binary
from ..formats.standard_iff import StandardIFF

SAFE_NAME=re.compile(r'[A-Za-z0-9_-]+\.(?:iff|cdf|bin)',re.I)


def cache_path(archive):
    key=hashlib.sha256(str(archive.path).encode()).hexdigest()[:16]
    return OUTPUT/'cache'/('identity_'+key+'.json')


def apply(archive,identities):
    for entry in archive.entries:
        item=identities.get(str(entry['hash']),{})
        name=item.get('name')
        if isinstance(name,str) and SAFE_NAME.fullmatch(name) and hash_name(name)==entry['hash']:
            entry['name']=name;entry['name_origin']='CRC32 verified'
        hint=item.get('hint')
        if isinstance(hint,str) and 0<len(hint)<=200 and not any(ord(c)<32 for c in hint):entry['name_hint']=hint


def load_cached(archive):
    path=cache_path(archive)
    if not path.exists():return
    try:
        data=json.loads(path.read_text(encoding='utf8'))
        if data.get('schema')==1 and data.get('fingerprint')==fingerprint(archive):apply(archive,data.get('identities',{}))
    except (ValueError,OSError,TypeError,AttributeError):pass


def recover(archive,candidates=(),job=None):
    entries={e['hash']:e for e in archive.entries};identities={};matches=0;hints=0;ambiguous=set()
    def candidate(name):
        nonlocal matches
        if not isinstance(name,str) or not SAFE_NAME.fullmatch(name):return
        h=hash_name(name)
        if h not in entries or entries[h]['name'] or h in ambiguous:return
        existing=identities.get(str(h),{}).get('name')
        if existing and existing.upper()!=name.upper():
            identities[str(h)].pop('name');ambiguous.add(h);matches-=1;return
        if not existing:identities.setdefault(str(h),{})['name']=name;matches+=1
    for name in candidates:candidate(name.strip())
    unknown=[e for e in archive.entries if not e['name']]
    for i,entry in enumerate(unknown):
        if job:job.check();job.progress(i,len(unknown),'Identifying unnamed archive assets')
        if entry['size']>32*1024*1024:continue
        try:
            data=archive.read(entry)
            if data[:4]==bytes.fromhex('f0985030'):
                b=Binary(data);name=b.utf16(b.relative(36),'be')
                candidate(name);candidate(name[:-4]+'.iff')
                identities.setdefault(str(entry['hash']),{})['hint']='CDF texture/audio bank: '+name[:150]
                hints+=1
            elif data[:4]==bytes.fromhex('ff3bef94'):
                iff=StandardIFF(data)
                records=[r for r in iff.records if r['type']=='SCNE'] or iff.records
                if records:
                    for record in records:candidate(record['name']+'.iff')
                    label=', '.join(dict.fromkeys(r['name'] for r in records))[:145]
                    kind='/'.join(dict.fromkeys(r['type'] for r in records))[:30]
                    identities.setdefault(str(entry['hash']),{})['hint']=kind+': '+label
                    hints+=1
        except (ValueError,UnicodeError):continue
    # Retain earlier recovery information when this pass has fewer candidates.
    for entry in archive.entries:
        if entry.get('name_origin') or entry.get('name_hint'):
            item=identities.setdefault(str(entry['hash']),{})
            if entry.get('name_origin'):item.setdefault('name',entry['name'])
            if entry.get('name_hint'):item.setdefault('hint',entry['name_hint'])
    path=safe_output(cache_path(archive),[archive.path]);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps({'schema':1,'fingerprint':fingerprint(archive),'identities':identities},indent=2),encoding='utf8')
    return dict(identities=identities,matched_names=matches,internal_labels=hints,remaining=len(unknown)-matches)
