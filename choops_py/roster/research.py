"""Read-only structural coverage and contextual palette research."""
import struct
from collections import Counter
from .schema import STRING_FIELDS, REFERENCES, PALETTE_OFFSET, PALETTE_COUNT, PALETTE_HINTS, CONFIRMED_PALETTE_ROLES, CONFIRMED_PALETTE_CAPTIONS, SCHOOL_COLOR_CONTROL_SLOTS, RATING_NAMES, RATING_OFFSET, RATING_COUNT,PLAYER_SCALARS,ROSTER_SLOT_COUNT, CONFERENCE_SCALARS, CONFERENCE_MEMBERS, CONFERENCE_MEMBER_CAPACITY, CONFERENCE_MEMBER_COUNT


def palette_rows(model, team_index):
    team = model.rows['teams'][team_index]
    return [{'slot': i, 'offset': PALETTE_OFFSET+i*4, 'rgba': value,
             'role': PALETTE_HINTS.get(i,'Unassigned palette candidate'),
             'confidence': 'Exact English menu caption and RGBA getter/setter verified' if i in CONFIRMED_PALETTE_CAPTIONS else 'Runtime/material role verified; no Edit Schools caption' if i in CONFIRMED_PALETTE_ROLES else 'RGBA storage verified; role unresolved',
             'school_control': SCHOOL_COLOR_CONTROL_SLOTS.index(i) if i in SCHOOL_COLOR_CONTROL_SLOTS else None}
            for i,value in enumerate(team['palette_colors'])]


def analyze(model):
    if hasattr(model,'game'):raise ValueError('This byte audit describes College Hoops only; see NBA_ROSTERS_AND_2K14.md for NBA schemas')
    data = bytes(model.data)
    header = []
    for field in range(8, 0xb0, 8):
        count = struct.unpack_from('>I',data,field)[0]
        delta = struct.unpack_from('>i',data,field+4)[0]
        target = field+4+delta-1
        from .schema import HEADER_TABLES
        binding=next((name for name,spec in HEADER_TABLES.items() if spec[0]==field),None)
        header.append({'field':field,'count':count,'relative_anchor':target,
                       'in_bounds':0<=target<len(data), 'meaning':binding+' table anchor' if binding else 'unassigned header table anchor'})
    tables = {}
    for name,(start,count,stride) in model.tables.items():
        from .schema import HEADER_TABLES
        origin=HEADER_TABLES.get(name,(0,1))[1]-1
        known = {}; masks = {};crossings=[];logical_masks={}
        def mark(offset,length,label):
            if offset+length>stride:crossings.append(dict(offset=offset,length=length,meaning=label))
            for i in range(offset,min(offset+length,stride)):
                known[i]=label;masks[i]=255
            for i in range(max(offset,origin),min(offset+length,origin+stride)):logical_masks[i]=255
        def packed(offset,size,shift,bits,label):
            if offset+size>stride:crossings.append(dict(offset=offset,length=size,meaning=label))
            for bit in range(shift,shift+bits):
                i=offset+size-1-bit//8
                if origin<=i<origin+stride:logical_masks[i]=logical_masks.get(i,0)|(1<<(bit%8))
                if 0<=i<stride:
                    masks[i]=masks.get(i,0)|(1<<(bit%8))
                    previous=known.get(i,'')
                    if label not in previous:known[i]=(previous+'; ' if previous else '')+label
        for field,offset in STRING_FIELDS.get(name,{}).items():mark(offset,4,field+' relative UTF-16BE pointer (displacement includes +1)')
        if name=='players':
            for field,(offset,size,shift,bits,_,_) in PLAYER_SCALARS.items():packed(offset,size,shift,bits,f'{field}: bits {shift}..{shift+bits-1}')
            from .shoes import FIELDS
            for field,(offset,shift,bits) in FIELDS['players'].items():packed(offset,4,shift,bits,field)
            mark(0x18,2,'Player identifier');mark(0x1b,1,'Jersey number; adjacent flags preserved')
            mark(0x3a,1,'Height inches');mark(0x3b,1,'Position code')
            for i,attribute_name in enumerate(RATING_NAMES):mark(RATING_OFFSET+i*2,2,attribute_name+' rating, u16 scaled by 100')
            mark(0x78,4,'Close / mid / 3PT / drive tendencies')
            mark(0x7f,1,'Potential');mark(0x80,1,'Confidence')
        if name=='teams':
            for field,(offset,_,_) in REFERENCES.items():mark(offset,4,field)
            mark(0x6c,ROSTER_SLOT_COUNT*4,'Eighteen player references');mark(0x188,2,'Active roster count')
            mark(0x18c,2,'Asset family ID');mark(0x18e,2,'Identity/check index')
            mark(0x190,2,'Asset ID repeat');mark(0x192,2,'Mascot asset candidate')
            mark(0x194,2,'Asset ID repeat')
            mark(PALETTE_OFFSET,PALETTE_COUNT*4,'RGBA team palette; 22 menu captions verified')
            from .shoes import FIELDS
            from .schema import TEAM_TYPE_OFFSET
            for field,(offset,shift,bits) in FIELDS['teams'].items():packed(offset,4,shift,bits,field)
            packed(TEAM_TYPE_OFFSET,4,15,3,'Team type')
        if name=='conferences':
            for field,(offset,size) in CONFERENCE_SCALARS.items():
                mark(offset,size,'Conference tournament index (legacy presentation_id)' if field=='presentation_id' else field)
            mark(CONFERENCE_MEMBERS,CONFERENCE_MEMBER_CAPACITY*4,'Reciprocal school reference array')
            mark(CONFERENCE_MEMBER_COUNT,2,'School member count')
        if name=='uniforms':
            for offset,shift,bits,label in ((0,22,10,'Uniform owner ID'),(0,12,10,'Uniform asset ID'),
                    (0,8,3,'Home/away/alternate bank'),(0,0,7,'Unlock ID'),(4,27,3,'Jersey shape')):
                packed(offset,4,shift,bits,label)
        if name=='arenas':
            mark(0x24,4,'Relative team-name-anchor reference; runtime ownership role unresolved')
            mark(0x2a,2,'Native numeric stadium asset selector (physical arena +0x12)')
            packed(0x30,2,0,2,'Native stadium resource mode (physical arena +0x18)')
        active = [r['index'] for r in model.rows[name] if r.get('display_name') or r.get('school_name') or r.get('arena_name') or r.get('coach_name')]
        sample = active or list(range(count))
        fields=[]
        for offset in range(stride):
            values=Counter(data[start+i*stride+offset] for i in sample)
            fields.append({'offset':offset,'meaning':known.get(offset,'Unknown byte; read-only'),
                'known_bit_mask':masks.get(offset,0),
                'unresolved_bit_mask':255^masks.get(offset,0),
                'min':min(values,default=0),'max':max(values,default=0),'distinct':len(values),
                'common':values.most_common(4),
                'rating_candidate':name=='players' and offset not in known and len(values)>10 and max(values,default=0)<=100})
        tables[name]={'start':start,'count':count,'stride':stride,'end':start+count*stride,
                      'classified_bytes_per_row':sum(mask==255 for mask in masks.values()),
                      'partially_classified_bytes_per_row':sum(mask!=255 for mask in masks.values()),
                      'unknown_bytes_per_row':stride-sum(mask==255 for mask in masks.values()),
                      'classified_bits_per_row':sum(mask.bit_count() for mask in masks.values()),
                      'fields_crossing_declared_stride':crossings,
                      'unresolved_ranges':unresolved_ranges([255^masks.get(i,0) for i in range(stride)]),
                      'logical_record_window':dict(raw_origin_offset=origin,start=start+origin,end=start+origin+count*stride,
                          classified_bits_per_row=sum(value.bit_count() for value in logical_masks.values()),
                          unresolved_ranges=unresolved_ranges([255^logical_masks.get(i,0) for i in range(origin,origin+stride)])),
                      'fields':fields}
    overlaps=[]
    for a,ta in tables.items():
        for b,tb in tables.items():
            if a<b and ta['start']<tb['end'] and tb['start']<ta['end']:
                overlaps.append({'tables':[a,b],'bytes':min(ta['end'],tb['end'])-max(ta['start'],tb['start']),
                                 'status':'biased editor windows overlap; compare logical_record_window before inferring table overlap'})
    intervals=sorted((t['start'],t['end']) for t in tables.values())
    unassigned=[];cursor=0
    for start,end in intervals:
        if start>cursor:unassigned.append({'start':cursor,'end':start})
        cursor=max(cursor,end)
    if cursor<len(data):unassigned.append({'start':cursor,'end':len(data)})
    logical_overlaps=[]
    for a,ta in tables.items():
        for b,tb in tables.items():
            left,right=ta['logical_record_window'],tb['logical_record_window']
            if a<b and left['start']<right['end'] and right['start']<left['end']:
                logical_overlaps.append(dict(tables=[a,b],bytes=min(left['end'],right['end'])-max(left['start'],right['start'])))
    logical_unassigned=[];cursor=0
    for start,end in sorted((t['logical_record_window']['start'],t['logical_record_window']['end']) for t in tables.values()):
        if start>cursor:logical_unassigned.append(dict(start=cursor,end=start))
        cursor=max(cursor,end)
    if cursor<len(data):logical_unassigned.append(dict(start=cursor,end=len(data)))
    return {'schema':1,'complete_semantic_reverse_engineering':False,'header_anchors':header,
            'arena_team_reference_audit':arena_team_references(model),
            'tables':tables,'table_boundary_ambiguities':overlaps,'logical_table_overlaps':logical_overlaps,
            'unassigned_regions':unassigned,'logical_unassigned_regions':logical_unassigned,
            'team_palette_count':PALETTE_COUNT,
            'findings':['Team asset ID links roster rows to sXXX / uniform / logo families.',
                        'Palette stores RGBA bytes; 22 exact Edit Schools captions are corroborated by localized callback bindings.',
                        'All 30 rating names and their numeric encoding are corroborated by localized executable UI bindings; remaining semantics are still incomplete.']}


def arena_team_references(model):
    """Validate a structural backlink without guessing ownership/edit semantics."""
    if 'arenas' not in model.tables or 'teams' not in model.tables:return []
    data=bytes(model.data);start,count,stride=model.tables['teams'];result=[]
    for row in model.rows['arenas']:
        field=row['row_offset']+0x24
        if field+4>len(data):
            result.append(dict(index=row['index'],status='out_of_bounds'));continue
        value=struct.unpack_from('>i',data,field)[0]
        if value in (0,-1):
            result.append(dict(index=row['index'],status='null'));continue
        target=field+value-1;relative=target-start-0x30
        valid=relative%stride==0 and 0<=relative//stride<count
        team_index=relative//stride if valid else None
        result.append(dict(index=row['index'],field_offset=field,target=target,
                           team_index=team_index,status='resolved' if valid else 'unresolved',
                           reciprocal=bool(valid and model.rows['teams'][team_index].get('arena_index')==row['index'])))
    return result


def unresolved_ranges(masks):
    """Half-open byte runs sharing the same unknown-bit mask, including partials."""
    result=[]
    for offset,mask in enumerate(masks):
        if not mask:continue
        if result and result[-1]['end']==offset and result[-1]['unresolved_bit_mask']==mask:
            result[-1]['end']=offset+1
        else:result.append(dict(start=offset,end=offset+1,unresolved_bit_mask=mask))
    return result


def main():
    import argparse
    import json
    from .editor_model import EditorModel
    parser=argparse.ArgumentParser(description='Read-only roster bit-coverage audit; unknown bytes are not editable.')
    parser.add_argument('roster')
    parser.add_argument('--full',action='store_true',help='Include every row-byte observation')
    args=parser.parse_args();report=analyze(EditorModel.open(args.roster))
    if not args.full:
        for table in report['tables'].values():table.pop('fields')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
