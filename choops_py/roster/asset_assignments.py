"""Copy only roster-backed asset routing/activation, retaining destination data."""
import struct

from .adapters import load_bytes
from .editor_model import EditorModel
from .uniforms import disabled_uniforms, _DISABLED_TAG


def copy_assignments(target, donor, teams):
    if hasattr(target, 'game') or hasattr(donor, 'game'):
        raise ValueError('Asset assignment copying supports College Hoops 2K8 rosters')
    teams = list(teams)
    if not teams or len(teams)!=len(set(teams)):
        raise ValueError('Select destination teams once each')
    if len(target.rows['teams'])!=len(donor.rows['teams']):
        raise ValueError('Roster team counts differ; automatic Team ID matching is unsafe')
    for i in teams:
        if type(i) is not int or not 0<=i<len(target.rows['teams']):
            raise ValueError('Invalid team selection')
        if target.rows['teams'][i]['team_index_check']!=donor.rows['teams'][i]['team_index_check']:
            raise ValueError('Roster Team ID checks differ; assignments were not copied')
    payload=bytes(target.data)
    working=EditorModel(load_bytes(payload))
    rows=[struct.unpack_from('>II',target.data,u['row_offset']) for u in target.rows['uniforms']]
    dormant=disabled_uniforms(payload)
    donor_dormant=disabled_uniforms(bytes(donor.data))
    owner_map={}; changes=[]
    occupied={a>>22&1023 for a,_ in rows+dormant+donor_dormant}
    occupied.update(t['uniform_owner_id'] for m in (target,donor) for t in m.rows['teams'])
    for i in teams:
        src=donor.rows['teams'][i]; dst=target.rows['teams'][i]
        owner=src['uniform_owner_id']
        wanted=[struct.unpack_from('>II',donor.data,u['row_offset']) for u in donor.rows['uniforms'] if u['team_asset_id']==owner]
        saved=[(a,b) for a,b in donor_dormant if a>>22&1023==owner]
        if len({a>>8&7 for a,_ in wanted+saved})!=len(wanted+saved) or any(a>>8&7>4 for a,_ in wanted+saved):
            raise ValueError('Source has ambiguous or unsupported uniform banks')
        if owner not in owner_map:
            existing=[r for r in rows if r[0]>>22&1023==owner]
            existing_saved=[r for r in dormant if r[0]>>22&1023==owner]
            shared=any(t['index'] not in teams and t['uniform_owner_id']==owner for t in target.rows['teams'])
            new_owner=owner
            if shared and (existing!=wanted or existing_saved!=saved):
                new_owner=next((n for n in range(1024) if n not in occupied),None)
                if new_owner is None:raise ValueError('No free uniform owner remains to preserve unselected teams')
                occupied.add(new_owner)
            owner_map[owner]=new_owner
            rows=[r for r in rows if r[0]>>22&1023!=new_owner]
            dormant=[r for r in dormant if r[0]>>22&1023!=new_owner]
            rows.extend(((a&~(1023<<22)) | new_owner<<22,b) for a,b in wanted)
            dormant.extend(((a&~(1023<<22)) | new_owner<<22,b) for a,b in saved)
        offset=working.row_offset('teams',i)
        data=bytearray(payload)
        for field,value in ((0x18c,src['asset_id']),(0x190,owner_map[owner]),(0x194,src['menu_logo_id'])):
            struct.pack_into('>H',data,offset+field,value)
        arena=src.get('arena_index')
        if arena is None:
            struct.pack_into('>i',data,offset+0x44,0)
            working.rows['teams'][i]['arena_index']=None
        else:
            from ..modding.declone import append_independent_arena
            from ..formats.binary import Binary
            count=working.tables['arenas'][1]
            template=dst.get('arena_index') if dst.get('arena_index') is not None else 0
            working.data=bytearray(payload)
            data=append_independent_arena(working,data,i,template,'0')
            anchor=Binary(data).relative(0x24)+count*28
            old=donor.row_offset('arenas',arena)+24
            data[anchor:anchor+28]=donor.data[old:old+28]
            for relative in (0,4,8):
                text=donor.string(old+relative,('asset-copy',arena,relative))
                field=anchor+relative
                if not text:struct.pack_into('>i',data,field,0)
                else:
                    start=len(data);data+=text.encode('utf-16-be')+b'\0\0'
                    struct.pack_into('>i',data,field,start-field+1)
            struct.pack_into('>i',data,anchor+12,offset+0x30-(anchor+12)+1)
            working.tables['arenas']=(Binary(data).relative(0x24)-24,count+1,28)
            working.rows['teams'][i]['arena_index']=count
        payload=bytes(data);working.data=bytearray(payload)
        changes.append(dict(team=i,school=dst.get('school_name',''),source_school=src.get('school_name',''),
                            owner=owner_map[owner],active=[a>>8&7 for a,_ in wanted],inactive=[a>>8&7 for a,_ in saved]))
    if len(rows)>8192 or len(dormant)>8192:
        raise ValueError('Copied uniform table exceeds supported capacity')
    start=(len(payload)+3)&~3
    data=bytearray(payload)+bytearray(start-len(payload))
    data+=b''.join(struct.pack('>II',*r) for r in rows)
    data+=_DISABLED_TAG+struct.pack('>I',len(dormant))+b''.join(struct.pack('>II',*r) for r in dormant)
    struct.pack_into('>Ii',data,0x70,len(rows),start-0x74+1)
    check=EditorModel(load_bytes(bytes(data)))
    if not check.validate()['valid']:raise ValueError('Copied asset assignments failed roster validation')
    return bytes(data),changes


def apply_to_editor(model,payload):
    """One undoable edit; rederive moved table directories on undo/redo too."""
    check=EditorModel(load_bytes(payload))
    if not check.validate()['valid']:raise ValueError('Invalid copied asset assignments')
    model.history.append((bytes(model.data),list(model.edits)))
    model.redo_history=[]
    model.edits.append(dict(table='teams',field='asset_assignments',value='Copied asset routing and activation'))
    model.data=bytearray(payload);model._asset_table_moves=True;model.reload()
