"""Explicit independent school assets in a new JB copy; no classification changes."""
import struct
from ..archive.usrdir_reader import Archive
from ..archive.hash_names import hash_name
from ..archive.add_assets import build
from ..roster.editor_model import EditorModel
from ..roster.adapters import load_bytes
from ..roster.uniforms import asset_name,append_uniform_records,encode_roster_iff
from ..formats.cdf_backed_iff_writer import clone_texture_record


def prepare(source,team_index,new_id,roster_payload=None):
    if not isinstance(new_id,int) or not 0<=new_id<=1023:raise ValueError('Choose a ten-bit independent asset ID')
    archive=Archive(source);entries={e['hash']:e for e in archive.entries}
    def read(name):
        entry=entries.get(hash_name(name))
        if entry is None:raise ValueError('Required source asset missing: '+name)
        return archive.read(entry)
    original=read('roster_english.iff')
    model=EditorModel(load_bytes(original if roster_payload is None else roster_payload))
    if not 0<=team_index<len(model.rows['teams']):raise ValueError('Select an existing school')
    team=model.rows['teams'][team_index]
    if any(new_id in (t['asset_id'],t['uniform_owner_id'],t['menu_logo_id']) for t in model.rows['teams']):
        raise ValueError('Independent ID is already referenced by a team')
    if any(r['team_asset_id']==new_id for r in model.rows['uniforms']):raise ValueError('Uniform owner ID is already in use')
    owned=[r for r in model.rows['uniforms'] if r['team_asset_id']==team['uniform_owner_id']]
    if not {0,1}.issubset({r['variant_code'] for r in owned}):raise ValueError('School requires verified home and away uniforms')
    additions={};specs=[]
    def clone(old,new):
        if hash_name(new) in entries or new in additions:raise ValueError('Independent asset filename already exists: '+new)
        additions[new]=read(old)
    arena_index=team.get('arena_index')
    if arena_index is None:raise ValueError('School has no verified arena reference')
    arena=model.rows['arenas'][arena_index]
    clone('s'+arena['arena_code']+'.iff',f's{new_id:03d}.iff')
    night='s'+arena['arena_code']+'n.iff'
    if hash_name(night) in entries:clone(night,f's{new_id:03d}n.iff')
    for row in owned:
        target={**row,'uniform_asset_id':new_id}
        for selection in (False,True):clone(asset_name(row,selection),asset_name(target,selection))
        specs.append((row['index'],new_id,row['variant_code'],new_id))
    logo_iff,logo_cdf=clone_texture_record(read('teamselectlogo.iff'),read('teamselectlogo.cdf'),
                                        f"logo{team['menu_logo_id']:03d}",f'logo{new_id:03d}')
    payload=bytearray(append_uniform_records(bytes(model.data),specs))
    payload=append_independent_arena(model,payload,team_index,arena_index,str(new_id))
    offset=model.row_offset('teams',team_index)
    for relative in (0x18c,0x190,0x194):struct.pack_into('>H',payload,offset+relative,new_id)
    roster=encode_roster_iff(original,bytes(payload));check=EditorModel(load_bytes(roster))
    updated=check.rows['teams'][team_index]
    if not check.validate()['valid'] or updated['team_type_code']!=team['team_type_code'] or updated.get('conference_index')!=team.get('conference_index'):
        raise ValueError('Independent asset preparation changed school classification or membership')
    replacements={'roster_english.iff':roster,'teamselectlogo.iff':logo_iff,'teamselectlogo.cdf':logo_cdf}
    return additions,replacements


def declone(source,team_index,new_id,output,job=None,roster_payload=None):
    additions,replacements=prepare(source,team_index,new_id,roster_payload)
    return build(source,additions,output,replacements,job)


def append_independent_arena(model,payload,team_index,arena_index,new_code):
    """Copy physical arena rows and rebase their three string references."""
    start,count,stride=model.tables['arenas']
    if stride!=28 or count>=8192:raise ValueError('Unsupported arena table')
    from ..formats.binary import Binary
    old=Binary(model.data);physical=start+24;body=old.slice(physical,count*28)
    # New legacy start is 24 bytes before the physical name-pointer anchor.
    target=(len(payload)+27)&~3
    payload+=b'\0'*(target-len(payload))
    payload+=body+body[arena_index*28:(arena_index+1)*28]
    for i in range(count+1):
        old_anchor=physical+(i if i<count else arena_index)*28
        new_anchor=target+i*28
        for relative in (0,4,8):
            field=old_anchor+relative;delta=struct.unpack_from('>i',model.data,field)[0]
            if delta in (0,-1):continue
            old_string=field+delta;new_field=new_anchor+relative
            if i<count:
                struct.pack_into('>i',payload,new_field,old_string-new_field)
            else:
                text=new_code if relative==8 else model.string(field,('arenas',arena_index,'copy'))
                string_start=len(payload)+1
                payload+=b'\0'+text.encode('utf-16-le')+b'\0\0'
                struct.pack_into('>i',payload,new_field,string_start-new_field)
    struct.pack_into('>I',payload,0x20,count+1)
    struct.pack_into('>i',payload,0x24,target+1-0x24)
    for team in model.rows['teams']:
        original=team.get('arena_index')
        if original is None:continue
        index=count if team['index']==team_index else original
        field=model.row_offset('teams',team['index'])+0x44
        struct.pack_into('>i',payload,field,target+index*28+1-field)
    return payload
