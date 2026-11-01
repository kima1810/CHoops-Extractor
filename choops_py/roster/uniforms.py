"""Executable-confirmed uniform banks and append-only roster table growth."""
import struct
from ..formats.binary import Binary
from ..formats.standard_iff import StandardIFF
from ..formats.standard_iff_writer import record_blocks
from ..formats.compression import encode_greedy, MAGIC
from ..core.errors import ToolError

BANKS='haxyz'
JERSEY_SHAPES={0:'u',1:'v',2:'vtri',3:'tri',4:'wishbone'}
VARIANT_NAMES={0:'Home',1:'Away',2:'Alternate 1',3:'Alternate 2',4:'Alternate 3'}

def asset_name(row, selection=False):
    variant=row['variant_code'];asset=row['uniform_asset_id']
    if variant not in range(5) or not 0<=asset<=1023:
        raise ValueError('Unsupported uniform bank or asset selector')
    return ('sel' if selection else '')+'u'+BANKS[variant]+f'{asset:03d}.iff'

def team_uniforms(rows, owner):
    return [row for row in rows if row['team_asset_id']==owner]

def append_uniform(payload, template_index, asset, variant, shape=None):
    """Append a copied table, leaving every original heap/table address intact."""
    b=Binary(payload);count=b.u32(0x70);start=b.relative(0x74)
    if not 0<count<8192 or not 0<=template_index<count:raise ValueError('Invalid uniform template/table')
    table=b.slice(start,count*8)
    word0,word1=struct.unpack_from('>II',table,template_index*8)
    owner=(word0>>22)&1023
    if any((a>>22)&1023==owner and (a>>8)&7==variant for a,_ in disabled_uniforms(payload)):
        raise ValueError('This alternate is disabled; restore it with the availability checkboxes')
    if variant not in (2,3,4) or not 0<=asset<=1023:raise ValueError('New records require a known alternate bank and ten-bit asset ID')
    if any((a>>22)&1023==owner and (a>>8)&7==variant for a,_ in struct.iter_unpack('>II',table)):
        raise ValueError('This team already has that alternate bank')
    if shape is not None:
        if shape not in range(5):raise ValueError('Unknown jersey shape')
        word1=(word1&~(7<<27))|(shape<<27)
    # Unlock ID zero is the executable's unconditional available case.
    word0=(word0&~((1023<<12)|(7<<8)|127))|(asset<<12)|(variant<<8)
    target=(len(payload)+3)&~3
    result=bytearray(payload)+bytearray(target-len(payload))+table+struct.pack('>II',word0,word1)
    struct.pack_into('>I',result,0x70,count+1)
    struct.pack_into('>i',result,0x74,target-0x74+1)
    expected=bytes(payload[:0x70])+bytes(result[0x70:0x78])+bytes(payload[0x78:])
    if bytes(result[:len(payload)])!=expected:raise ValueError('Unexpected modification outside uniform header')
    check=Binary(result);check.slice(check.relative(0x74),(count+1)*8)
    if check.slice(target,count*8)!=table:raise ValueError('Original uniform rows changed')
    return bytes(result)

def encode_roster_iff(original, payload):
    """Grow only a single-record ROST logical block; preserve container metadata."""
    iff=StandardIFF(original)
    if len(iff.blocks)!=1 or len(iff.records)!=1 or iff.records[0]['type']!='ROST' or iff.records[0]['offsets']!=[0]:
        raise ValueError('Roster payload growth requires a single-block, sole-ROST IFF')
    block=iff.blocks[0];stored=original[block['start']:block['start']+block['size']]
    if block['compressed']:
        stored=encode_greedy(stored,payload)
    else:stored=payload
    header=bytearray(original[:iff.header_size])
    prefix=original[iff.header_size:block['start']]
    suffix=original[block['start']+block['size']:iff.file_length]
    new_end=iff.header_size+len(prefix)+len(stored)+len(suffix)
    struct.pack_into('>I',header,8,new_end)
    struct.pack_into('>I',header,32+12,len(payload))
    struct.pack_into('>I',header,32+24,len(stored))
    trailer=original[iff.file_length:]
    if trailer[:4]==bytes.fromhex('aa171516'):
        meaningful=8+Binary(trailer).u32(4,'<')
        if meaningful>len(trailer):raise ValueError('Invalid name trailer')
    elif any(trailer):raise ValueError('Unknown nonzero trailer')
    else:meaningful=0
    if any(trailer[meaningful:]):raise ValueError('Unknown trailer padding')
    result=bytes(header)+prefix+stored+suffix+trailer[:meaningful]
    if len(result)<len(original):result+=b'\0'*(len(original)-len(result))
    parsed=StandardIFF(result)
    if record_blocks(parsed,parsed.records[0])[0][3]!=payload:raise ValueError('Expanded roster IFF failed round-trip')
    return result


def append_uniform_records(payload, specifications):
    """Append many records with a single copied table, without heap relocation."""
    b=Binary(payload);count=b.u32(0x70);start=b.relative(0x74)
    table=b.slice(start,count*8)
    existing={(a>>22&1023,a>>8&7) for a,_ in list(struct.iter_unpack('>II',table))+disabled_uniforms(payload)}
    extra=[]
    for spec in specifications:
        template,asset,variant=spec[:3];owner_override=spec[3] if len(spec)>3 else None
        if not 0<=template<count or not 0<=asset<=1023 or variant not in range(5):raise ValueError('Invalid uniform specification')
        a,c=struct.unpack_from('>II',table,template*8)
        owner=a>>22&1023 if owner_override is None else owner_override
        if not 0<=owner<=1023 or (owner,variant) in existing:raise ValueError('Duplicate/invalid team uniform bank')
        existing.add((owner,variant))
        a=(a&~((1023<<22)|(1023<<12)|(7<<8)|127))|(owner<<22)|(asset<<12)|(variant<<8)
        extra.append(struct.pack('>II',a,c))
    if count+len(extra)>8192:raise ValueError('Uniform table exceeds supported limit')
    target=(len(payload)+3)&~3
    result=bytearray(payload)+bytearray(target-len(payload))+table+b''.join(extra)
    struct.pack_into('>I',result,0x70,count+len(extra));struct.pack_into('>i',result,0x74,target-0x74+1)
    return bytes(result)


_DISABLED_TAG = b'CHoopsDisabledUniformsV1\0'

def disabled_uniforms(payload):
    """Editor recovery records are outside the game-counted uniform table."""
    position=payload.rfind(_DISABLED_TAG)
    if position<0:return []
    start=position+len(_DISABLED_TAG)
    if start+4>len(payload):raise ValueError('Truncated disabled uniform metadata')
    count=Binary(payload).u32(start)
    if count>8192 or start+4+count*8>len(payload):raise ValueError('Invalid disabled uniform metadata')
    return list(struct.iter_unpack('>II',payload[start+4:start+4+count*8]))

def set_alternate_enabled(payload, owner, variant, enabled):
    if variant not in (2,3,4) or not 0<=owner<=1023:raise ValueError('Invalid alternate selector')
    if len(payload)>60*1024*1024:raise ValueError('Roster expansion exceeds the supported size')
    b=Binary(payload);count=b.u32(0x70);start=b.relative(0x74)
    active=list(struct.iter_unpack('>II',b.slice(start,count*8)))
    dormant=disabled_uniforms(payload)
    matches=lambda row: (row[0]>>22)&1023==owner and (row[0]>>8)&7==variant
    source=dormant if enabled else active;target=active if enabled else dormant
    found=[row for row in source if matches(row)]
    if not found:
        if any(matches(row) for row in target):return payload
        raise ValueError('No linked alternate exists. Add its assets to a JB copy first.')
    if len(found)!=1 or any(matches(row) for row in target):raise ValueError('Ambiguous alternate links')
    source.remove(found[0]);target.append(found[0])
    # Keep each owner in bank order: the executable selects by list ordinal.
    if enabled:
        restored=active.pop()
        candidates=[i for i,row in enumerate(active) if (row[0]>>22)&1023==owner]
        position=next((i for i in candidates if (active[i][0]>>8)&7>variant),candidates[-1]+1 if candidates else len(active))
        active.insert(position,restored)
    offset=(len(payload)+3)&~3
    result=bytearray(payload)+bytearray(offset-len(payload))
    result+=b''.join(struct.pack('>II',*row) for row in active)
    result+=_DISABLED_TAG+struct.pack('>I',len(dormant))
    result+=b''.join(struct.pack('>II',*row) for row in dormant)
    struct.pack_into('>I',result,0x70,len(active))
    struct.pack_into('>i',result,0x74,offset-0x74+1)
    return bytes(result)
