"""Sequential, bounded verification of copied and relocated split banks."""
from contextlib import ExitStack
from pathlib import Path

CHUNK = 4 * 1024 * 1024


class BankReader:
    def __init__(self, archive, stack):
        self.archive = archive
        self.stack = stack
        self.streams = {}

    def read(self, offset, size):
        result = bytearray()
        base = 0
        for part in self.archive.parts:
            end = base + part['size']
            if base <= offset < end and size:
                name = part['name']
                if name not in self.streams:
                    self.streams[name] = self.stack.enter_context(self.archive.open_part(part) if hasattr(self.archive, 'open_part') else (self.archive.path/name).open('rb'))
                stream = self.streams[name]
                position = offset-base
                if stream.tell() != position:
                    stream.seek(position)
                count = min(size, end-offset)
                data = stream.read(count)
                if len(data) != count:
                    raise ValueError('Short split-bank verification read')
                result.extend(data)
                size -= count
                offset += count
            base = end
        if size:
            raise ValueError('Verification range outside split banks')
        return bytes(result)


def archive_header(archive):
    """Read the pre-body region from logical split-bank coordinates."""
    from ..core.errors import ToolError
    first=min(e['offset'] for e in archive.entries)
    minimum=24+len(archive.parts)*getattr(archive,'descriptor_stride',16)+len(archive.entries)*16
    if first<minimum or first>sum(p['size'] for p in archive.parts):
        raise ToolError('invalid_archive_header_extent',f'First asset starts at {first:,}; metadata needs {minimum:,} bytes. Select a complete matching source JB; overrides cannot repair its TOC.')
    if first>128*1024*1024:
        raise ToolError('archive_header_extent_unconfirmed',f'The pre-body region is {first:,} bytes, above the bounded 128 MiB writer limit. Select the original JB or inspect the source TOC before rebuilding; no overrides were changed.')
    try:
        with ExitStack() as stack:return BankReader(archive,stack).read(0,first)
    except (ValueError,OSError) as error:
        sizes=', '.join(p['name']+': '+str((archive.path/p['name']).stat().st_size if (archive.path/p['name']).is_file() else 'missing') for p in archive.parts)
        raise ToolError('incomplete_archive_header',f'Expected {first:,} header bytes across the source banks ({sizes}). {error}. Restore missing/truncated source banks from the same rip and select the source JB again; do not rename or remove overrides to fix source data.') from error


class BankWriter:
    """Keep destination bank handles open while streaming a relocation."""
    def __init__(self, directory, names, sizes, stack):
        self.directory = Path(directory)
        self.parts = list(zip(names, sizes))
        self.stack = stack
        self.streams = {}

    def write(self, offset, data):
        position = base = 0
        for name, size in self.parts:
            end = base+size
            if base <= offset < end and position < len(data):
                if name not in self.streams:
                    self.streams[name] = self.stack.enter_context((self.directory/name).open('r+b'))
                stream = self.streams[name]
                if stream.tell() != offset-base:
                    stream.seek(offset-base)
                count = min(len(data)-position, end-offset)
                if stream.write(memoryview(data)[position:position+count]) != count:
                    raise ValueError('Short split-bank write')
                position += count
                offset += count
            base = end
        if position != len(data):
            raise ValueError('Incomplete split-bank write')


def verify_body(source, destination, excluded=(), delta=0, job=None):
    """Compare the entire old body, including padding, using each bank handle once.

    Exclusions are source-coordinate (offset, length) pairs for in-place writes.
    Relocated replacements leave their old bytes in place and are NOT excluded.
    New headers and replacement payloads are validated separately by the writer.
    """
    first = min(e['offset'] for e in source.entries)
    end = sum(p['size'] for p in source.parts)
    intervals = []
    for offset, size in sorted(excluded):
        if size < 0 or offset < first or offset+size > end:
            raise ValueError('Invalid preservation exclusion')
        if intervals and offset <= intervals[-1][1]:
            intervals[-1] = (intervals[-1][0], max(intervals[-1][1], offset+size))
        else:
            intervals.append((offset, offset+size))
    spans = []
    cursor = first
    for lo, hi in intervals:
        if cursor < lo:
            spans.append((cursor, lo))
        cursor = hi
    if cursor < end:
        spans.append((cursor, end))
    total = sum(hi-lo for lo, hi in spans)
    done = 0
    with ExitStack() as stack:
        left, right = BankReader(source, stack), BankReader(destination, stack)
        for lo, hi in spans:
            while lo < hi:
                if job:
                    job.check()
                count = min(CHUNK, hi-lo)
                if left.read(lo, count) != right.read(lo+delta, count):
                    raise ValueError('Preserved archive body differs')
                lo += count
                done += count
                if job:
                    job.progress(done, total, 'Verifying preserved archive bytes')
    return done


def verify_files(root, copied, archive, before, job=None):
    """Also verify non-bank files; bank-only checks missed damaged ancillary files."""
    root, copied = Path(root), Path(copied)
    banks = {str((archive.path/p['name']).relative_to(root)) for p in archive.parts}
    for relative, metadata in before.items():
        if relative in banks:
            continue
        target = copied/relative
        if not target.is_file() or target.stat().st_size != metadata['size']:
            raise ValueError('Copied non-bank file missing or resized: '+relative)
        with (root/relative).open('rb') as left, target.open('rb') as right:
            while True:
                if job:
                    job.check()
                data = left.read(CHUNK)
                if data != right.read(CHUNK):
                    raise ValueError('Copied non-bank file differs: '+relative)
                if not data:
                    break
                if job:
                    job.progress(left.tell(), metadata['size'], 'Verifying copied file '+relative)
