"""Read-only NBA 2K9 PS3 inventory and exact stored-asset extraction.

No GUI/game mode, cache identity registration, archive writer or conversion is
enabled. NBA 2K9 TOC rows are size64/hash32/sector32, unlike College Hoops.
"""
import argparse
import hashlib
import json
import shutil
import uuid
from collections import Counter
from contextlib import ExitStack
from pathlib import Path

from ..archive.build_io import BankReader
from ..archive.hash_names import hash_name
from ..archive.manifests import safe_output
from ..archive.usrdir_reader import Archive


class NBA2K9Archive(Archive):
    """Restrict the shared automatic reader to the researched size64 schema."""
    def __init__(self, source):
        super().__init__(source)
        from ..archive.layouts import NBA2K
        if self.toc_layout != NBA2K:
            raise ValueError('This research command expects the NBA 2K9 size64 TOC')
        for entry in self.entries:
            entry['name_status']='hash_dictionary_candidate' if entry['name'] else 'unresolved'

    def select(self, selector):
        if selector.startswith('index:'):
            index = int(selector[6:])
            matches = [e for e in self.entries if e['index'] == index]
        else:
            identity = int(selector[5:], 0) if selector.startswith('hash:') else hash_name(selector)
            matches = [e for e in self.entries if e['hash'] == identity]
        if len(matches) != 1:
            raise ValueError('No unique NBA 2K9 asset: '+selector)
        return matches[0]


def resource_kind(prefix):
    if prefix[:4] == bytes.fromhex('ff3bef94'):
        return 'standard_iff'
    if prefix[:4] == bytes.fromhex('f0985030'):
        return 'cdf_metadata'
    if prefix[:5] == bytes.fromhex('010e4837c3'):
        return 'flagged_h7a_resource'
    if prefix[:4] == bytes.fromhex('0e4837c3'):
        return 'h7a_prefixed_resource'
    return 'other_resource'


def snapshot(archive):
    result = {}
    for part in archive.parts:
        info = (archive.path/part['name']).stat()
        result[part['name']] = (info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_ino)
    return result


def extract(source, output, selectors=(), all_iff=False):
    """Inventory all signatures; export only requested stored payloads unchanged."""
    archive = NBA2K9Archive(source)
    before = snapshot(archive)
    output = safe_output(output, [archive.path])
    if output.exists():
        raise ValueError('Choose a new NBA 2K9 research output folder')
    output.parent.mkdir(parents=True, exist_ok=True)
    pending = output.parent/('.nba2k9_extract_'+uuid.uuid4().hex)
    pending.mkdir()
    try:
        counts = Counter()
        with ExitStack() as stack:
            reader = BankReader(archive, stack)
            for entry in sorted(archive.entries, key=lambda e: e['offset']):
                prefix = reader.read(entry['offset'], min(32, entry['size']))
                entry['kind'] = resource_kind(prefix)
                counts[entry['kind']] += 1
        selected = {e['index']: e for e in (archive.select(s) for s in selectors)}
        if all_iff:
            selected.update({e['index']: e for e in archive.entries
                             if e['kind'] in ('standard_iff', 'cdf_metadata')})
        # A CDF metadata file is not self-contained: include its linked payload.
        from ..formats.binary import Binary
        confirmed_names = {}
        for entry in list(selected.values()):
            if entry['kind'] == 'cdf_metadata':
                raw = archive.read(entry)
                b = Binary(raw)
                companion = b.utf16(b.relative(36), 'be')
                if Path(companion).name != companion or any(c in companion for c in '/\\:'):
                    raise ValueError('Unsafe CDF companion name')
                partner = archive.select(companion)
                selected[partner['index']] = partner
                confirmed_names[partner['index']] = companion
                owner_name = str(Path(companion).with_suffix('.iff'))
                if hash_name(owner_name) == entry['hash']:
                    confirmed_names[entry['index']] = owner_name
        exported = []
        for entry in sorted(selected.values(), key=lambda e: e['index']):
            # Known hash candidates are labels, not newly verified name mappings.
            suffix = '.iff' if entry['kind'] in ('standard_iff', 'cdf_metadata') else '.bin'
            name = confirmed_names.get(entry['index']) or entry['name'] or f"hash_{entry['hash']:08x}{suffix}"
            if Path(name).name != name or any(c in name for c in '/\\:'):
                raise ValueError('Unsafe candidate filename')
            checksum = hashlib.sha256()
            with (pending/name).open('xb') as stream:
                for chunk in archive.chunks(entry):
                    stream.write(chunk)
                    checksum.update(chunk)
            # Re-read written bytes independently; never certify just a write hash.
            with (pending/name).open('rb') as stream:
                actual = hashlib.file_digest(stream, 'sha256').hexdigest()
            if actual != checksum.hexdigest():
                raise ValueError('Extracted asset checksum mismatch')
            exported.append(dict(index=entry['index'], hash=entry['hash'], file=name,
                                 bytes=entry['size'], sha256=actual, kind=entry['kind']))
        if snapshot(archive) != before:
            raise ValueError('NBA 2K9 source changed during extraction')
        report = dict(schema=1, game='NBA 2K9 PS3 research', bank_count=len(archive.parts),
                      alignment=archive.alignment, entry_count=len(archive.entries),
                      candidate_names=sum(e['name'] is not None for e in archive.entries),
                      kinds=dict(counts), entries=archive.entries, extracted=exported,
                      source_inventory_unchanged=True, this_command_read_only=True, shared_builder_layout=archive.toc_layout)
        (pending/'inventory.json').write_text(json.dumps(report, indent=2), encoding='utf8')
        pending.rename(output)
        return report
    except BaseException:
        shutil.rmtree(pending)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('output')
    parser.add_argument('--extract', nargs='+', default=[], metavar='NAME_OR_HASH')
    parser.add_argument('--all-iff', action='store_true', help='Extract every direct IFF and linked CDF (large)')
    args = parser.parse_args()
    report = extract(args.source, args.output, args.extract, args.all_iff)
    print(json.dumps({key: value for key, value in report.items() if key != 'entries'}, indent=2))


if __name__ == '__main__':
    main()
