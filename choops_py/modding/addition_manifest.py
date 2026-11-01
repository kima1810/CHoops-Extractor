"""Integrity-checked new archive inputs, separate from existing replacements."""
from pathlib import Path
import json
from ..archive.manifests import digest
from ..archive.importer import asset_name
from ..archive.hash_names import hash_name
from ..core.paths import reject_links


def load(mod, archive):
    root = Path(mod).resolve()
    marker = root / 'additions.json'
    if not marker.exists():
        return {}
    reject_links(root)
    document = json.loads(marker.read_text(encoding='utf8'))
    if document.get('schema') != 1 or not isinstance(document.get('entries'), list) or len(document['entries']) > 16384:
        raise ValueError('Invalid additions manifest')
    occupied = {e['hash'] for e in archive.entries}
    result = {}
    for row in document['entries']:
        name = asset_name(row['archive'])
        if not name.lower().endswith('.iff'):
            raise ValueError('Team additions must be IFF archives')
        identity = hash_name(name)
        if identity in occupied:
            raise ValueError('New asset name/hash already exists: ' + name)
        occupied.add(identity)
        path = (root / row['path']).resolve()
        if not path.is_relative_to(root) or not path.is_file() or path.stat().st_size > 128 * 1024 * 1024:
            raise ValueError('Invalid new asset path: ' + name)
        raw = path.read_bytes()
        if len(raw) != row['size'] or digest(raw) != row['sha256']:
            raise ValueError('New asset changed; select the overrides folder again: ' + name)
        result[name] = raw
    return result
