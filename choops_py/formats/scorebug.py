"""Read-only scorebug, sixth-man scene and authored text-anchor inventory."""
import argparse
import json
import re

from ..archive.usrdir_reader import Archive
from .binary import Binary
from .package import textures
from .standard_iff import StandardIFF
from .standard_iff_writer import record_blocks
from .txtr import TXTR

ARCHIVES=('gamedata.iff','gamedataextra.iff')


def inspect_iff(raw):
    iff=StandardIFF(raw);result=[]
    for rec in iff.records:
        if not re.search('scorebug|shotclock|^6th_',rec['name'],re.I):continue
        row={key:rec[key] for key in ('index','name','type')}
        blocks=[p[3] for p in record_blocks(iff,rec)]
        row['block_lengths']=list(map(len,blocks))
        if rec['type']=='SCNE':
            b=Binary(blocks[0]);count=b.u32(0x44)
            if count>4096:raise ValueError('Scorebug model count exceeds scene limit')
            table=b.relative(0x48) if count else 0;b.slice(table,count*0xb0)
            row['parts']=[b.utf16(b.relative(table+i*0xb0),'be') for i in range(count)]
            text_count=b.u32(0x4c)
            if text_count>4096:raise ValueError('Scorebug text count exceeds scene limit')
            text_table=b.relative(0x50) if text_count else 0
            b.slice(text_table,text_count*144)
            import struct
            row['text_anchors']=[]
            for i in range(text_count):
                at=text_table+i*144
                row['text_anchors'].append(dict(name=b.utf16(b.relative(at+64),'be'),
                    position=list(struct.unpack_from('>3f',blocks[0],at+48)),
                    matrix_copies_match=blocks[0][at+48:at+60]==blocks[0][at+96:at+108]))
            row['textures']=[dict(index=t.index,**TXTR([t.header,t.payload]).info()) for t in textures(blocks)]
        elif rec['type']=='TXTR':row['texture']=TXTR(blocks).info()
        result.append(row)
    return result


def discover(archive):
    result={}
    for name in ARCHIVES:
        matches=[e for e in archive.entries if e['name']==name]
        if len(matches)!=1:raise ValueError('Missing or ambiguous scorebug archive: '+name)
        result[name]=inspect_iff(archive.read(matches[0]))
    return dict(schema=1,archives=result,source_unchanged=True,runtime_bindings_verified=False,
                next_steps=['Authored geometry/text edits are experimental; confirm runtime animation and event behavior separately.',
                            'Keep PS3/Xenon variants distinct; record names alone do not establish active routing.'])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('jb_folder')
    args=parser.parse_args();print(json.dumps(discover(Archive(args.jb_folder)),indent=2))


if __name__=='__main__':main()
