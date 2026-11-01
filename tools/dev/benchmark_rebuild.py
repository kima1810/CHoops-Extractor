"""Measure rebuild preservation I/O using synthetic banks only; never a game JB."""

import argparse
import random
import shutil
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

from choops_py.archive.add_assets import checksum
from choops_py.archive.build_io import verify_body
from choops_py.archive.usrdir_reader import Archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--entries', type=int, default=8192)
    args = parser.parse_args()
    if not 1 <= args.entries <= 65536:
        parser.error('entries must be between 1 and 65536')
    with tempfile.TemporaryDirectory(prefix='choops-synthetic-io-') as folder:
        root = Path(folder)
        left, right = root/'source', root/'copy'
        left.mkdir()
        entries = [dict(offset=2048+i*4096, size=4096) for i in range(args.entries)]
        random.Random(27).shuffle(entries)
        with (left/'0A').open('wb') as stream:
            stream.write(b'\0'*2048)
            for i in range(args.entries):
                stream.write(i.to_bytes(4, 'big')*1024)
        shutil.copytree(left, right)
        parts = [dict(name='0A', size=(left/'0A').stat().st_size)]
        source = SimpleNamespace(path=left, entries=entries, parts=parts)
        target = SimpleNamespace(path=right, entries=entries, parts=parts)
        started = time.perf_counter()
        for entry in entries:
            left_hash = checksum(Archive.chunks(source, entry))
            assert left_hash == checksum(Archive.chunks(target, entry))
        old = time.perf_counter()-started
        started = time.perf_counter()
        verified = verify_body(source, target)
        new = time.perf_counter()-started
        print(f'Synthetic bytes verified: {verified:,}; entries: {args.entries:,}')
        print(f'Previous per-entry checks: {old:.4f}s; sequential checks: {new:.4f}s')
        print(f'Verification speedup: {old/new:.2f}x; '
              f'bank opens: {2*args.entries:,} -> 2')
        print('This measures verification only, not whole-build time. '
              'No game data used.')


if __name__ == '__main__':
    main()
