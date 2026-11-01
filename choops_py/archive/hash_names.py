import json,zlib
from pathlib import Path
from functools import lru_cache
def hash_name(name): return zlib.crc32(name.upper().encode('ascii')) & 0xffffffff

def replacement_hash(name):
    """Resolve a canonical filename or the Python ripper's explicit hash label."""
    import re
    match=re.fullmatch(r'hash_([0-9a-f]{8})\.(?:iff|bin|cdf)',name,re.IGNORECASE)
    return int(match[1],16) if match else hash_name(name)
def namespace():
    banks='roster english french german italian spanish japanese motion music frontend frontend_sync global gamedata gamedataextra loading legalpage loc fonts online playercreate playeditor teamselectlogo arenapics overlaycache jukebox roster_english streetdata studio studio_preview studio_pontiac dornas crowd sfx_inside facegen ababall basket chantcreate chantcreate_drums chantcreate_sounds gameintro gameintro_cameras gameintro_drums gameintro_playerspeech halftimeadjustments legacy powerbar reelmanual weeklyshow tutorial drilldata shrine shrine_trophies statefarm kellogg gumbel Director'.split()
    for name in banks:
        for ext in ('.iff','.cdf','.bin'): yield name+ext
    for prefix in ('f','ua','uh','ux','uy','uz','selua','seluh','selux','seluy','seluz','s','m','p','coach','h'):
        for i in range(10000 if prefix=='h' else 1024 if prefix=='s' or prefix.startswith(('u','selu')) else 1000):
            for ext in ('.iff','.cdf','.bin'):yield f"{prefix}{i:0{4 if prefix=='h' else 3}d}{ext}"
    for i in range(10000):
        yield f'png{i:04d}.iff'
    for i in range(1000):yield f'logo{i:03d}.iff'
    for i in range(10000):yield f'logo{i:04d}.iff'
    for name in ('players.bin','teams.bin'):yield name
    for i in range(1024):yield f's{i:03d}n.iff'
    for shape in ('u','v','vtri','tri','wishbone'):
        for build in ('thin','reg','fat'):yield f'cloth_{shape}_{build}.iff'
    for i in range(2):yield f'shoe_{i}.iff'
    for base,styles,colors in ((100,3,16),(200,1,16),(300,1,16),(500,4,2)):
        for style in range(styles):
            for color in range(colors):yield f'shoe_{base+style}_{color:02d}.iff'

@lru_cache
def lookup():
    result={hash_name(n):n for n in namespace()}
    result.update({int(k):v for k,v in json.loads(Path(__file__).with_name('names.json').read_text()).items()})
    result.update({int(k):v for k,v in json.loads(Path(__file__).with_name('verified_names.json').read_text(encoding='utf8')).items()})
    return result
def resolve(value):
    try:h=int(value,0)
    except ValueError:h=hash_name(value)
    return dict(hash=h,name=lookup().get(h),hex=f'0x{h:08x}')
