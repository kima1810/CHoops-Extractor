"""Read-only structural coverage and contextual palette research."""
import struct
from collections import Counter
from .schema import STRING_FIELDS, REFERENCES, PALETTE_OFFSET, PALETTE_COUNT, PALETTE_HINTS, CONFIRMED_PALETTE_ROLES, CONFIRMED_PALETTE_CAPTIONS, SCHOOL_COLOR_CONTROL_SLOTS, RATING_NAMES, RATING_OFFSET, RATING_COUNT


def palette_rows(model, team_index):
    team = model.rows['teams'][team_index]
    return [{'slot': i, 'offset': PALETTE_OFFSET+i*4, 'rgba': value,
             'role': PALETTE_HINTS.get(i,'Unassigned palette candidate'),
             'confidence': 'Exact English menu caption and RGBA getter/setter verified' if i in CONFIRMED_PALETTE_CAPTIONS else 'Runtime/material role verified; no Edit Schools caption' if i in CONFIRMED_PALETTE_ROLES else 'RGBA storage verified; role unresolved',
             'school_control': SCHOOL_COLOR_CONTROL_SLOTS.index(i) if i in SCHOOL_COLOR_CONTROL_SLOTS else None}
            for i,value in enumerate(team['palette_colors'])]


def analyze(model):
    data = bytes(model.data)
    header = []
    for field in range(8, 0xb0, 8):
        count = struct.unpack_from('>I',data,field)[0]
        delta = struct.unpack_from('>i',data,field+4)[0]
        target = field+4+delta
        header.append({'field':field,'count':count,'relative_anchor':target,
                       'in_bounds':0<=target<len(data), 'meaning':'unassigned header table anchor'})
    tables = {}
    for name,(start,count,stride) in model.tables.items():
        known = {}
        def mark(offset,length,label):
            for i in range(offset,offset+length):known[i]=label
        for field,offset in STRING_FIELDS.get(name,{}).items():mark(offset,4,field+' relative UTF-16LE pointer')
        if name=='players':
            mark(0x18,2,'Player identifier');mark(0x1b,1,'Jersey number; adjacent flags preserved')
            mark(0x3a,1,'Height inches');mark(0x3b,1,'Position code')
            for i,attribute_name in enumerate(RATING_NAMES):mark(RATING_OFFSET+i*2,2,attribute_name+' rating, u16 scaled by 100')
            mark(0x78,4,'Close / mid / 3PT / drive tendencies')
            mark(0x7f,1,'Potential');mark(0x80,1,'Confidence')
        if name=='teams':
            for field,(offset,_,_) in REFERENCES.items():mark(offset,4,field)
            mark(0x6c,64,'Sixteen player references')
            mark(0x18c,2,'Asset family ID');mark(0x18e,2,'Identity/check index')
            mark(0x190,2,'Asset ID repeat');mark(0x192,2,'Mascot asset candidate')
            mark(0x194,2,'Asset ID repeat')
            mark(PALETTE_OFFSET,PALETTE_COUNT*4,'RGBA team palette; 22 menu captions verified')
        active = [r['index'] for r in model.rows[name] if r.get('display_name') or r.get('school_name') or r.get('arena_name') or r.get('coach_name')]
        sample = active or list(range(count))
        fields=[]
        for offset in range(stride):
            values=Counter(data[start+i*stride+offset] for i in sample)
            fields.append({'offset':offset,'meaning':known.get(offset,'Unknown byte; read-only'),
                'min':min(values,default=0),'max':max(values,default=0),'distinct':len(values),
                'common':values.most_common(4),
                'rating_candidate':name=='players' and offset not in known and len(values)>10 and max(values,default=0)<=100})
        tables[name]={'start':start,'count':count,'stride':stride,'end':start+count*stride,
                      'classified_bytes_per_row':len(known),'unknown_bytes_per_row':stride-len(known),
                      'fields':fields}
    overlaps=[]
    for a,ta in tables.items():
        for b,tb in tables.items():
            if a<b and ta['start']<tb['end'] and tb['start']<ta['end']:
                overlaps.append({'tables':[a,b],'bytes':min(ta['end'],tb['end'])-max(ta['start'],tb['start']),
                                 'status':'legacy table-boundary ambiguity; unknown fields remain read-only'})
    intervals=sorted((t['start'],t['end']) for t in tables.values())
    unassigned=[];cursor=0
    for start,end in intervals:
        if start>cursor:unassigned.append({'start':cursor,'end':start})
        cursor=max(cursor,end)
    if cursor<len(data):unassigned.append({'start':cursor,'end':len(data)})
    return {'schema':1,'complete_semantic_reverse_engineering':False,'header_anchors':header,
            'tables':tables,'table_boundary_ambiguities':overlaps,'unassigned_regions':unassigned,
            'team_palette_count':PALETTE_COUNT,
            'findings':['Team asset ID links roster rows to sXXX / uniform / logo families.',
                        'Palette stores RGBA bytes; 22 exact Edit Schools captions are corroborated by localized callback bindings.',
                        'All 30 rating names and their numeric encoding are corroborated by localized executable UI bindings; remaining semantics are still incomplete.']}
