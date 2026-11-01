"""Append an independent physical arena while preserving other team links."""
import struct


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
    # Native stadium route (0x580A9C) consumes this numeric halfword, not
    # the arena-code display string. Keep both identities synchronized.
    if not str(new_code).isdecimal() or not 0<=int(new_code)<=65535:
        raise ValueError('Stadium selector must fit an unsigned halfword')
    struct.pack_into('>H',payload,target+count*28+0x12,int(new_code))
    for i in range(count+1):
        old_anchor=physical+(i if i<count else arena_index)*28
        new_anchor=target+i*28
        backlink=old_anchor+0x0c
        delta=struct.unpack_from('>i',model.data,backlink)[0]
        if i==count:
            struct.pack_into('>i',payload,new_anchor+0x0c,model.row_offset('teams',team_index)+0x30-(new_anchor+0x0c)+1)
        elif delta not in (0,-1):
            struct.pack_into('>i',payload,new_anchor+0x0c,backlink+delta-(new_anchor+0x0c))
        for relative in (0,4,8):
            field=old_anchor+relative;delta=struct.unpack_from('>i',model.data,field)[0]
            if delta in (0,-1) and not (i==count and relative==8):continue
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
