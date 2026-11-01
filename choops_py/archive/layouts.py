"""Detect supported PS3 2K TOC schemas from bounded ranges, never title guesses."""
import struct

CH2K = 'hash-offset-flags-size32'
NBA2K = 'size64-hash-offset'


def decode_toc(raw, alignment, minimum, total):
    if not raw or len(raw) % 16:
        raise ValueError('Truncated 2K archive TOC')
    candidates = []
    for layout in (CH2K, NBA2K):
        rows = []
        for i in range(0, len(raw), 16):
            if layout == CH2K:
                identity, sector, flags, size = struct.unpack_from('>4I', raw, i)
            else:
                size, identity, sector = struct.unpack_from('>QII', raw, i)
                flags = 0
            rows.append(dict(index=i//16, hash=identity, offset=sector*alignment,
                             stored_size=size, size=size, toc_flags=flags))
        ordered = sorted(rows, key=lambda e: e['offset'])
        if len({e['hash'] for e in rows}) != len(rows):
            continue
        valid = True
        for i, entry in enumerate(ordered):
            boundary = ordered[i+1]['offset'] if i+1 < len(rows) else total
            if not minimum <= entry['offset'] < boundary <= total:
                valid = False
                break
            capacity = boundary-entry['offset']
            entry['allocation_size'] = capacity
            if not 0 < entry['stored_size'] <= capacity:
                if layout == NBA2K:
                    valid = False
                    break
                # Retain the established College Hoops extent fallback.
                entry.update(size_derived=True, content_size=None, size=capacity)
            else:
                entry['content_size'] = entry['stored_size']
                entry['size'] = (entry['stored_size'] if layout == NBA2K else
                                 min(capacity, (entry['stored_size']+alignment-1)//alignment*alignment))
        if valid:
            candidates.append((layout, rows))
    if len(candidates) != 1:
        raise ValueError('Unsupported or ambiguous 2K archive TOC; overlaps, duplicates or invalid ranges')
    return candidates[0]


def pack_row(buffer, offset, row, layout):
    """Encode canonical [hash, sector, flags, size] using the source schema."""
    identity, sector, flags, size = row
    if layout == CH2K:
        struct.pack_into('>4I', buffer, offset, identity, sector, flags, size)
    elif layout == NBA2K:
        if flags:
            raise ValueError('The size64 TOC has no flags field')
        struct.pack_into('>QII', buffer, offset, size, identity, sector)
    else:
        raise ValueError('Unsupported 2K TOC writer layout')
