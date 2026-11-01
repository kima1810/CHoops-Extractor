"""Read-only College Hoops face routing inventory; never edits roster or assets."""
import argparse
import json
import re
from collections import Counter

from ..archive.hash_names import hash_name
from ..archive.usrdir_reader import Archive
from ..formats.binary import Binary
from ..formats.cdf_backed_iff import CDFPair
from ..formats.compression import decode
from ..formats.standard_iff import StandardIFF
from ..formats.standard_iff_writer import record_blocks
from ..formats.txtr import TXTR
from ..roster.adapters import load_bytes
from ..roster.editor_model import EditorModel

LIKENESSES = {
    1: 'Mike Conley', 2: 'Glen Davis', 3: 'Greg Oden', 4: 'J.J. Redick',
    5: 'Al Thornton', 6: 'Alando Tucker', 7: 'Julian Wright',
}
# Raw editor rows begin 16 bytes before the engine's logical player anchor.
FACE_SLOT_OFFSET = 0x9c
CUSTOM_MORPH_OFFSET = 0x98
GENERATION_SEED_OFFSET = 0x1c
MORPH_RANGES = ((0xb6, 50), (0xe8, 30), (0x106, 50))


def player_faces(model, include_players=False):
    if hasattr(model, 'game'):
        raise ValueError('Face routing offsets describe College Hoops, not NBA rosters')
    start, count, stride = model.tables['players']
    if stride != 308:
        raise ValueError('Unsupported College Hoops player stride')
    b = Binary(model.data)
    slots = Counter()
    custom = 0
    nonzero_morphs = [0, 0, 0]
    players = []
    for index in range(count):
        offset = start + index*stride
        slot = b.u32(offset+FACE_SLOT_OFFSET) & 15
        flag = bool(b.u32(offset+CUSTOM_MORPH_OFFSET) & 1)
        slots[slot] += 1
        custom += flag
        for group, (relative, length) in enumerate(MORPH_RANGES):
            # Last range crosses the biased editor window, but remains inside
            # the engine's logical row. Do not truncate it at the legacy stride.
            nonzero_morphs[group] += any(b.slice(offset+relative, length))
        if include_players:
            row = model.rows['players'][index]
            players.append(dict(index=index, name=row['display_name'],
                dedicated_face_slot=slot, original_likeness=LIKENESSES.get(slot),
                slot_established=slot in (0, *LIKENESSES),
                custom_morph_flag=flag,
                generation_seed=b.u32(offset+GENERATION_SEED_OFFSET)))
    result = dict(player_count=count, dedicated_slot_counts=dict(sorted(slots.items())),
        custom_morph_flag_count=custom, nonzero_morph_row_counts=nonzero_morphs,
        writable=False)
    if include_players:
        result['players'] = players
    return result


def inventory(archive, include_players=False):
    by_hash = {e['hash']: e for e in archive.entries}
    result = dict(mode='read-only', banks={}, unresolved=[],
        png_named_entry_count=sum(bool(re.fullmatch(r'png\d+\.iff', e['name'] or ''))
                                  for e in archive.entries))
    for bank in ('pcaatface', 'pcfacenormal', 'pcfacehair'):
        iff_entry = by_hash.get(hash_name(bank+'.iff'))
        cdf_entry = by_hash.get(hash_name(bank+'.cdf'))
        if iff_entry is None or cdf_entry is None:
            result['unresolved'].append(bank+': paired IFF/CDF missing')
            continue
        pair = CDFPair(archive.read(iff_entry), archive.read(cdf_entry))
        records = []
        for rec in pair.records:
            item = dict(name=rec['name'], type=rec['type'])
            if rec['type'] == 'TXTR':
                blocks = [decode(pair.cdf[rec[p+'_offset']:rec[p+'_offset']+rec[p+'_length']])
                          for p in ('header', 'payload')]
                item['texture'] = TXTR(blocks).info()
            records.append(item)
        result['banks'][bank+'.iff'] = records
    for bank, wanted in (('global.iff', {'facegen_head', 'facegen_bench_head'}),
                         ('facegen.iff', {'mean_head'})):
        entry = by_hash.get(hash_name(bank))
        if entry is None:
            result['unresolved'].append(bank+': missing')
            continue
        iff = StandardIFF(archive.read(entry))
        records = []
        for rec in iff.records:
            if rec['name'] not in wanted and rec['type'] != 'FRFG':
                continue
            blocks = [p[3] for p in record_blocks(iff, rec)]
            item = dict(name=rec['name'], type=rec['type'], block_sizes=list(map(len, blocks)))
            if rec['type'] == 'SCNE':
                header = Binary(blocks[0])
                item.update(texture_slots=header.u32(0x20), mesh_parts=header.u32(0x44))
            records.append(item)
        result['banks'][bank] = records
    roster = by_hash.get(hash_name('roster_english.iff'))
    if roster is not None:
        result['roster'] = player_faces(EditorModel(load_bytes(archive.read(roster))), include_players)
    else:
        result['unresolved'].append('roster_english.iff: missing')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', help='Original College Hoops PS3 JB/USRDIR')
    parser.add_argument('--players', action='store_true', help='Include source player names and selectors')
    args = parser.parse_args()
    print(json.dumps(inventory(Archive(args.source), args.players), indent=2))


if __name__ == '__main__':
    main()
