"""Evidence-based archive categories and roster references, without invented names."""
import re
from collections import defaultdict
from .hash_names import hash_name
from ..roster.uniforms import asset_name, VARIANT_NAMES, JERSEY_SHAPES


def category(entry):
    if entry['hash']==4175903001:return 'Shoes'
    name=(entry.get('name') or '').lower()
    hint=(entry.get('name_hint') or '').lower()
    if re.match(r'shoe_',name):return 'Shoes'
    if re.match(r'(?:sel)?u[haxyz]\d+',name):return 'Uniforms'
    if name.startswith('cloth'):return 'Cloth geometry'
    if re.fullmatch(r'[sf]\d+n?\.(iff|cdf|bin)',name):return 'Stadiums'
    if 'logo' in name or 'logo' in hint:return 'Logos'
    if name.startswith(('p','h')) and re.fullmatch(r'(?:png|p|h)\d+\.(iff|cdf|bin)',name):return 'Players'
    if any(word in name for word in ('music','jukebox','chant','sfx')):return 'Audio'
    if any(word in name for word in ('frontend','teamselect','loading','legalpage')):return 'Menus'
    if 'roster' in name:return 'Rosters'
    if name in ('crowd.iff', 'gumbel.iff', 'kellogg.iff', 'gameintro_cameras.iff', 'playercreate.iff'):
        return 'Animation banks'
    if ('singlemocap' in hint or name=='motion.iff' or
        name.startswith(('animgraph_','animations_','siganims_','nba_animations','online_teamup_animations','endorsementanims'))):return 'Animation banks'
    return 'Other / unresolved'


def catalog(entries,model=None):
    references=defaultdict(set)
    if model and hasattr(model,'game'):
        for player in model.rows['players']:
            references[hash_name(f"png{player['face_id']:04d}.iff")].add(player['display_name']+' — face artwork')
        for arena in model.rows['arenas']:
            for role in ('stadium_asset','floor_asset','dorna_asset','led_asset'):
                if arena.get(role):references[hash_name(arena[role]+'.iff')].add(arena['arena_name']+' — '+role.replace('_',' '))
        for team in model.rows['teams']:
            if team.get('menu_logo'):
                owner=team['city']+' '+team['team_name']
                references[hash_name(team['menu_logo']+'.iff')].add(owner+' — menu logo')
                references[hash_name('teamselectlogo.iff')].add(owner+' — '+team['menu_logo'])
    if model and not hasattr(model,'game'):
        for school in model.rows.get('teams',[]):
            name=school['school_name']
            arena_index=school.get('arena_index')
            arenas=model.rows.get('arenas',[])
            if isinstance(arena_index,int) and 0<=arena_index<len(arenas):
                code=arenas[arena_index].get('arena_code')
                if code and str(code).isdigit():
                    for file in (f's{code}.iff',f's{code}n.iff'):
                        references[hash_name(file)].add(name+' — stadium')
            for role in ('home_shoe_texture','away_shoe_texture'):
                if school.get(role):references[hash_name(school[role])].add(name+' — '+role.replace('_',' '))
            if school.get('menu_logo_id') is not None:
                references[hash_name('teamselectlogo.iff')].add(name+f" — menu logo ID {school['menu_logo_id']} (bank)")
            for uniform in model.rows.get('uniforms',[]):
                if uniform['team_asset_id']!=school['uniform_owner_id']:continue
                try:
                    variant = VARIANT_NAMES.get(uniform['variant_code'], 'Uniform')
                    references[hash_name(asset_name(uniform))].add(name+' — '+variant+' uniform')
                    references[hash_name(asset_name(uniform, selection=True))].add(name+' — '+variant+' uniform selection menu')
                    shape=JERSEY_SHAPES.get(uniform.get('jersey_shape_code'))
                    if shape:
                        for build in ('','_thin','_reg','_fat'):
                            references[hash_name(f'cloth_{shape}{build}.iff')].add(name+' — '+variant+' jersey geometry')
                    references[hash_name('cloth_shorts.iff')].add(name+' — shared shorts geometry')
                except ValueError:continue
        schools_by_player=defaultdict(set)
        for school in model.rows.get('teams', []):
            for player_index in school.get('roster_slots', []):
                if type(player_index) is int:schools_by_player[player_index].add(school['school_name'])
        for player in model.rows.get('players', []):
            owner=player.get('display_name') or 'Player #'+str(player.get('index', '?'))
            schools=schools_by_player.get(player.get('index'), set())
            if schools:owner+=' ('+', '.join(sorted(schools))+')'
            for role in ('home_shoe_texture', 'away_shoe_texture'):
                if player.get(role):references[hash_name(player[role])].add(owner+' — '+role.replace('_',' '))
        from ..roster.conference_assets import logo_record
        for conference in model.rows.get('conferences', []):
            if 0 <= conference['index'] < 39:
                name=conference.get('conference_name') or 'Conference #'+str(conference['index'])
                references[hash_name('teamselectlogo.iff')].add(name+' — '+logo_record(conference['index'])+' conference menu logo (bank)')
        # The paired CDF contains payload for the same confirmed IFF ownership.
        for entry in entries:
            name=entry.get('name') or ''
            if name.lower().endswith('.cdf'):
                references[entry['hash']].update(references[hash_name(name[:-4]+'.iff')])
    rows=[]
    for entry in entries:
        row=dict(entry,category=category(entry),references='; '.join(sorted(references[entry['hash']])))
        if entry['hash']==4175903001 and not row.get('name') and not row.get('name_hint'):row['name_hint']='SCNE shoe mesh: hi_shoe1 (verified internal record)'
        rows.append(row)
    return rows


def record_references(archive_name, records, model):
    """Confirmed school menu logo IDs resolve to exact logoNNN bank records."""
    owners=defaultdict(set)
    archive_name=archive_name or ''
    if model and hasattr(model,'game') and archive_name.lower()=='teamselectlogo.iff':
        for team in model.rows['teams']:
            if team.get('menu_logo'):owners[team['menu_logo']].add(team['city']+' '+team['team_name'])
    if model and not hasattr(model,'game') and archive_name.lower()=='teamselectlogo.iff':
        for school in model.rows.get('teams',[]):
            if school.get('menu_logo_id') is not None:
                owners[f"logo{school['menu_logo_id']:03d}"].add(school['school_name'])
        from ..roster.conference_assets import logo_record
        for conference in model.rows.get('conferences', []):
            if 0 <= conference['index'] < 39:
                owners[logo_record(conference['index'])].add(conference['conference_name'] or f"Conference #{conference['index']}")
    bank_references=''
    if model and archive_name and archive_name.lower()!='teamselectlogo.iff':
        bank_references=catalog([dict(name=archive_name,hash=hash_name(archive_name))],model)[0]['references']
    return [{**record,'references':'; '.join(sorted(owners[record.get('name','')])) or bank_references} for record in records]
