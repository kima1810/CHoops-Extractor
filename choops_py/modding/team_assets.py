"""Roster-linked team asset plans. Originals are read-only; output is explicit."""
from collections import Counter, defaultdict
from pathlib import Path
import json
import struct
import uuid

from ..archive.hash_names import hash_name
from ..archive.manifests import safe_output, digest
from ..core.paths import reject_links
from ..roster.adapters import load_bytes
from ..roster.editor_model import EditorModel
from ..roster.uniforms import BANKS, asset_name, encode_roster_iff, disabled_uniforms, _DISABLED_TAG

KINDS = ('stadium', 'h', 'a', 'x', 'y', 'z', 'menu_logo')


def require_college(archive):
    base = getattr(archive, 'base', archive)
    title = getattr(base, 'game_info', {}).get('TITLE', '')
    if base.read_only or (title and 'college hoops 2k8' not in title.casefold()):
        raise ValueError('Team asset expansion requires a writable College Hoops 2K8 JB')


def read_named(archive, name):
    matches = [e for e in archive.entries if e['hash'] == hash_name(name)]
    if len(matches) != 1:
        raise ValueError('Required unique source asset missing: ' + name)
    return archive.read(matches[0])


def roster_model(archive):
    require_college(archive)
    original = read_named(archive, 'roster_english.iff')
    return original, EditorModel(load_bytes(original))


def arena_selector(model, team):
    index = team.get('arena_index')
    if index is None:
        return None, None
    physical = model.row_offset('arenas', index) + 24
    # Native 0x580A3C reads the physical record's +0x12 selector and +0x18 mode.
    return struct.unpack_from('>H', model.data, physical + 0x12)[0], struct.unpack_from('>H', model.data, physical + 0x18)[0] & 3


def inventory(archive, model, *, inspect_logos=True):
    """One row per team; active means linked, not necessarily profile-unlocked."""
    require_college(archive)
    hashes = {e['hash'] for e in archive.entries}
    owners = Counter(t['uniform_owner_id'] for t in model.rows['teams'])
    arenas = Counter(t.get('arena_index') for t in model.rows['teams'])
    menu = Counter(t['menu_logo_id'] for t in model.rows['teams'])
    dormant = disabled_uniforms(bytes(model.data))
    logos = None
    if inspect_logos and hash_name('teamselectlogo.iff') in hashes and hash_name('teamselectlogo.cdf') in hashes:
        from ..formats.cdf_backed_iff import CDFPair
        logos = {r['name'] for r in CDFPair(read_named(archive, 'teamselectlogo.iff'), read_named(archive, 'teamselectlogo.cdf')).records}
    # Sharing follows the actual asset route, even when roster owner/arena rows
    # differ (for example a classic team pointing at a modern team's stadium).
    routes, users = {}, defaultdict(list)
    for team in model.rows['teams']:
        keys = {'menu_logo': ('menu_logo', team['menu_logo_id'])}
        selector, _ = arena_selector(model, team)
        if selector is not None:
            keys['stadium'] = ('stadium', selector)
        owned = [u for u in model.rows['uniforms'] if u['team_asset_id'] == team['uniform_owner_id']]
        for variant, bank in enumerate(BANKS):
            matches = [u for u in owned if u['variant_code'] == variant]
            if len(matches) == 1:
                keys[bank] = ('uniform', asset_name(matches[0], False))
        routes[team['index']] = keys
        for key in keys.values():
            users[key].append(team)
    result = []
    for team in model.rows['teams']:
        selector, mode = arena_selector(model, team)
        filename = f's{selector:03d}.iff' if selector is not None else ''
        banks = {}
        present = []
        owned = [u for u in model.rows['uniforms'] if u['team_asset_id'] == team['uniform_owner_id']]
        for variant, bank in enumerate(BANKS):
            matches = [u for u in owned if u['variant_code'] == variant]
            if not matches:
                disabled = any(a >> 22 & 1023 == team['uniform_owner_id'] and a >> 8 & 7 == variant for a, _ in dormant)
                banks[bank] = 'Inactive (saved)' if disabled else 'Inactive'
            elif len(matches) != 1:
                banks[bank] = 'Ambiguous'
            else:
                uniform = matches[0]
                names = [asset_name(uniform, selection) for selection in (False, True)]
                missing = [n for n in names if hash_name(n) not in hashes]
                if not missing:
                    present.append(bank)
                state = 'Missing: ' + ', '.join(missing) if missing else 'Active'
                if uniform['unlock_id']:
                    state += f"; unlock {uniform['unlock_id']}"
                banks[bank] = f"{names[0]} / {names[1]} — {state}"
        label = f"logo{team['menu_logo_id']:03d}"
        if filename and hash_name(filename) in hashes:
            present.append('stadium')
        if logos is not None and label in logos:
            present.append('menu_logo')
        result.append(dict(index=team['index'], school=team.get('school_name') or f"Team {team['index']}",
                           present_assets=present,
                           shared_assets={kind: [f"{other.get('school_name') or 'Team'} [Team {other['index']}]"
                                                for other in users[key] if other['index'] != team['index']]
                                          for kind, key in routes[team['index']].items()},
                           asset_id=team['asset_id'], owner_id=team['uniform_owner_id'], menu_id=team['menu_logo_id'],
                           stadium=(filename + (' — Present' if hash_name(filename) in hashes else ' — Missing')) if filename else 'Unassigned',
                           stadium_mode=mode, menu_logo=label + (' — Present' if logos is not None and label in logos else ' — Missing' if logos is not None else ' — Not inspected'),
                           shared=f"Uniforms {owners[team['uniform_owner_id']]} / arena {arenas[team.get('arena_index')]} / logo {menu[team['menu_logo_id']]}", **banks))
    return result


def available_ids(archive, model):
    """Reserve every existing team/arena/uniform/dormant identity and filename."""
    used = {t[k] for t in model.rows['teams'] for k in ('asset_id', 'uniform_owner_id', 'menu_logo_id')}
    used.update(u[k] for u in model.rows['uniforms'] for k in ('team_asset_id', 'uniform_asset_id'))
    used.update(a >> 22 & 1023 for a, _ in disabled_uniforms(bytes(model.data)))
    used.update(a >> 12 & 1023 for a, _ in disabled_uniforms(bytes(model.data)))
    used.update(arena_selector(model, t)[0] for t in model.rows['teams'])
    hashes = {e['hash'] for e in archive.entries}
    return [i for i in range(1024) if i not in used and all(hash_name(n) not in hashes for n in
            [f's{i:03d}.iff', f's{i:03d}n.iff', *(f'{prefix}u{b}{i:03d}.iff' for prefix in ('', 'sel') for b in BANKS)])]


def prepare(archive, requests, *, roster_payload=None, job=None):
    """Clone checked categories for selected teams, with independent uniform owners.

    requests: [{'team': index, 'id': unused_id, 'assets': ['stadium','h',...]}].
    All linked banks survive owner separation; unchecked art retains its old ID.
    Missing checked banks copy Home artwork, never imply new artwork.
    """
    original, model = roster_model(archive)
    if roster_payload is not None:
        model = EditorModel(load_bytes(bytes(roster_payload)))
    if not requests:
        raise ValueError('Select at least one team and asset category')
    free = set(available_ids(archive, model))
    additions, replacements, changes = {}, {}, []
    logo_templates = dict(getattr(archive, 'logo_templates', {}))
    fallbacks = list(getattr(archive, 'alternate_fallbacks', []))
    cache = {}
    def cached_read(name):
        if name not in cache:
            cache[name] = read_named(archive, name)
        return cache[name]
    payload = bytes(model.data)
    seen = set()
    hashes = {e['hash'] for e in archive.entries}
    source_dormant = disabled_uniforms(payload)
    dormant = list(source_dormant)
    all_rows = [struct.unpack_from('>II', model.data, u['row_offset']) for u in model.rows['uniforms']]
    uniforms_changed = False
    requested_ids = {r['id'] for r in requests}
    for step, request in enumerate(requests):
        if job:
            job.check(); job.progress(step, len(requests), 'Preparing independent team assets')
        index, new_id = request['team'], request['id']
        kinds = set(request['assets'])
        if type(index) is not int or not 0 <= index < len(model.rows['teams']) or index in seen:
            raise ValueError('Choose each existing team once')
        team = model.rows['teams'][index]
        reuse_owner = new_id == team['uniform_owner_id'] and kinds.issubset(set(BANKS)) and sum(t['uniform_owner_id'] == new_id for t in model.rows['teams']) == 1
        if type(new_id) is not int or (new_id not in free and not reuse_owner):
            raise ValueError('Choose an unused asset ID from 0–1023')
        if not kinds or not kinds.issubset(KINDS):
            raise ValueError('Choose supported asset categories')
        seen.add(index); free.discard(new_id)
        offset = model.row_offset('teams', index)
        def clone(old, new):
            if new in additions:
                raise ValueError('Duplicate planned asset: ' + new)
            if new == old:
                return
            if hash_name(new) in hashes:
                raise ValueError('Target asset already exists: ' + new)
            additions[new] = cached_read(old)
        if 'stadium' in kinds:
            selector, mode = arena_selector(model, team)
            if selector is None or mode not in (0, 1):
                raise ValueError('Stadium requires a normal arena route (mode 0 or 1)')
            clone(f's{selector:03d}.iff', f's{new_id:03d}.iff')
            if hash_name(f's{selector:03d}n.iff') in hashes:
                clone(f's{selector:03d}n.iff', f's{new_id:03d}n.iff')
            from .declone import append_independent_arena
            payload = bytes(append_independent_arena(model, bytearray(payload), index, team['arena_index'], str(new_id)))
            # Update only arena routing state; one full reparse validates the final
            # batch. Rebuilding thousands of player dictionaries per team is wasteful.
            from ..formats.binary import Binary
            count = model.tables['arenas'][1]
            model.tables['arenas'] = (Binary(payload).relative(0x24)-24, count+1, 28)
            model.rows['teams'][index]['arena_index'] = count
            model.data = bytearray(payload)
        selected = {BANKS.index(k) for k in kinds if k in BANKS}
        if selected:
            fallback_asset_id = None
            old_owner = team['uniform_owner_id']
            owned = [u for u in model.rows['uniforms'] if u['team_asset_id'] == old_owner]
            if len({u['variant_code'] for u in owned}) != len(owned) or any(u['variant_code'] > 4 for u in owned):
                raise ValueError('Ambiguous or unsupported uniform banks for selected team')
            source = {u['variant_code']: struct.unpack_from('>II', model.data, u['row_offset']) for u in owned}
            for a, b in source_dormant:
                if a >> 22 & 1023 == old_owner:
                    variant = a >> 8 & 7
                    if variant in source or variant > 4:
                        raise ValueError('Ambiguous dormant uniform bank')
                    source[variant] = (a, b)
            if not {0, 1}.issubset({u['variant_code'] for u in owned}):
                raise ValueError('Team must have active home and away templates')
            active = {u['variant_code'] for u in owned} | selected
            # Native list ordinals must not skip a preceding bank.
            active.update(range(max(active) + 1))
            rows = []
            saved = []
            for variant in sorted(set(source) | active):
                word0, word1 = source.get(variant, source[0])
                old = {'variant_code': word0 >> 8 & 7, 'uniform_asset_id': word0 >> 12 & 1023}
                if variant in active and (variant in selected or variant not in {u['variant_code'] for u in owned}):
                    target = {'variant_code': variant, 'uniform_asset_id': new_id}
                    if reuse_owner and any(hash_name(asset_name(target, selection)) in hashes and asset_name(target, selection)!=asset_name(old, selection) for selection in (False,True)):
                        # A filename at the owner's ID can belong to another team's
                        # artwork. Give this owner's new bank a separate free selector.
                        if fallback_asset_id is None:
                            fallback_asset_id=next((i for i in sorted(free) if i not in requested_ids),None)
                            if fallback_asset_id is None:raise ValueError('No free artwork selector remains for this alternate')
                            free.remove(fallback_asset_id)
                        target['uniform_asset_id']=fallback_asset_id
                    for selection in (False, True):
                        old_name, new_name = asset_name(old, selection), asset_name(target, selection)
                        clone(old_name, new_name)
                        if variant >= 2 and variant not in source:
                            fallbacks.append(dict(archive=new_name, home=old_name, sha256=digest(additions[new_name]),
                                                  message=f"{new_name}: alternate missing in overrides; cloned Home slot {old_name}"))
                    word0 = (word0 & ~(1023 << 12)) | target['uniform_asset_id'] << 12
                    if old != target:word0 &= ~127
                word0 = (word0 & ~(1023 << 22 | 7 << 8)) | new_id << 22 | variant << 8
                (rows if variant in active else saved).append((word0, word1))
            # Keep old rows for other teams sharing the owner. Build the counted
            # table once after all requests, keeping each owner in native bank order.
            if reuse_owner:
                all_rows = [(a, b) for a, b in all_rows if a >> 22 & 1023 != old_owner]
                dormant = [(a, b) for a, b in dormant if a >> 22 & 1023 != old_owner]
            all_rows.extend(rows); dormant.extend(saved); uniforms_changed = True
            if len(all_rows) > 8192:
                raise ValueError('Uniform table exceeds supported capacity')
            data = bytearray(payload)
            struct.pack_into('>H', data, offset + 0x190, new_id)
            payload = bytes(data)
        if 'menu_logo' in kinds:
            from ..formats.cdf_backed_iff_writer import clone_texture_record
            old_iff = replacements.get('teamselectlogo.iff') or read_named(archive, 'teamselectlogo.iff')
            old_cdf = replacements.get('teamselectlogo.cdf') or read_named(archive, 'teamselectlogo.cdf')
            new_iff, new_cdf = clone_texture_record(old_iff, old_cdf, f"logo{team['menu_logo_id']:03d}", f'logo{new_id:03d}')
            donor = f"logo{team['menu_logo_id']:03d}"
            logo_templates[f'logo{new_id:03d}'] = logo_templates.get(donor, donor)
            replacements.update({'teamselectlogo.iff': new_iff, 'teamselectlogo.cdf': new_cdf})
            data = bytearray(payload); struct.pack_into('>H', data, offset + 0x194, new_id)
            payload = bytes(data)
        # General asset identity is used by other consumers: leave it unchanged.
        changes.append(dict(team=index, school=team.get('school_name', ''), id=new_id, assets=sorted(kinds)))
    if uniforms_changed:
        start = (len(payload) + 3) & ~3
        data = bytearray(payload) + bytearray(start - len(payload))
        data += b''.join(struct.pack('>II', *r) for r in all_rows)
        data += _DISABLED_TAG + struct.pack('>I', len(dormant))
        data += b''.join(struct.pack('>II', *r) for r in dormant)
        struct.pack_into('>Ii', data, 0x70, len(all_rows), start - 0x74 + 1)
        payload = bytes(data)
    roster = encode_roster_iff(original, payload)
    check = EditorModel(load_bytes(roster))
    if not check.validate()['valid']:
        raise ValueError('Expanded roster failed validation')
    replacements['roster_english.iff'] = roster
    base = getattr(archive, 'base', archive)
    return dict(additions=additions, replacements=replacements, teams=changes, logo_templates=logo_templates, fallbacks=fallbacks, runtime_verified=False,
                source_roster_sha256=digest(read_named(base, 'roster_english.iff')))


def export_folder(plan, output, source):
    """Publish a new editable loose folder; stage_folder applies it to normal builds."""
    output = safe_output(output, [source])
    if output.exists():
        raise ValueError('Choose a new overrides folder')
    output.parent.mkdir(parents=True, exist_ok=True)
    pending = output.parent / ('.team_assets_' + uuid.uuid4().hex)
    try:
        pending.mkdir()
        for name, data in {**plan['additions'], **plan['replacements']}.items():
            folder = pending / Path(name).stem
            folder.mkdir(exist_ok=True)
            (folder / name).write_bytes(data)
        marker = dict(schema=1, source_roster_sha256=plan['source_roster_sha256'], logo_templates=plan['logo_templates'], fallbacks=plan['fallbacks'], additions=[dict(name=n, path=f'{Path(n).stem}/{n}') for n in plan['additions']], teams=plan['teams'])
        (pending / 'team_assets.json').write_text(json.dumps(marker, indent=2), encoding='utf8')
        pending.rename(output)
    except BaseException:
        import shutil
        if pending.exists():
            shutil.rmtree(pending)
        raise
    return output


def roster_plan(archive, payload):
    original,_=roster_model(archive)
    base=getattr(archive,'base',archive)
    return dict(additions={},replacements={'roster_english.iff':encode_roster_iff(original,bytes(payload))},teams=[],
                logo_templates=dict(getattr(archive,'logo_templates',{})),fallbacks=list(getattr(archive,'alternate_fallbacks',[])),
                source_roster_sha256=digest(read_named(base,'roster_english.iff')))


def apply_plan(source,plan,archive,folder,workspace,job=None):
    """Preserve the currently selected complete overrides before normal preparation."""
    plan={**plan,'additions':dict(plan['additions']),'replacements':dict(plan['replacements'])}
    if hasattr(archive,'replacements'):
        for entry in archive.entries:
            if entry['index'] in archive.replacements:
                name=entry.get('name') or f"hash_{entry['hash']:08x}.iff"
                target=plan['additions'] if entry['index']>=len(archive.base.entries) else plan['replacements']
                target.setdefault(name,archive.read(entry))
    export_folder(plan,folder,source)
    from ..studio.services import stage_folder
    return stage_folder(source,folder,workspace,job)


def loose_alternate_document(base, root):
    """Recognize absent uniform archives only when linked by the effective roster."""
    import re
    candidates = defaultdict(list)
    roster_files = []
    pending = [root]
    while pending:
        parent = pending.pop()
        for path in parent.iterdir():
            if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
                raise ValueError('Linked replacement path is blocked')
            if path.is_dir():
                pending.append(path)
            if path.is_file() and path.name.casefold() == 'roster_english.iff':
                roster_files.append(path)
            name = path.name.casefold().removesuffix('.subfiles')
            if path.is_dir() and not name.endswith('.iff'):name += '.iff'
            if re.fullmatch(r'(?:sel)?u[xyz]\d{3,4}\.iff', name):
                candidates[name].append(path)
    hashes = {e['hash'] for e in base.entries}
    candidates = {n: paths for n, paths in candidates.items() if hash_name(n) not in hashes}
    if not candidates:return None
    original, model = roster_model(base)
    if len(roster_files) > 1:
        raise ValueError('Multiple roster_english.iff overrides; choose one effective roster')
    if roster_files:
        if roster_files[0].stat().st_size > 64 * 1024 * 1024:
            raise ValueError('Roster override exceeds 64 MiB')
        model = EditorModel(load_bytes(roster_files[0].read_bytes()))
        if not model.validate()['valid']:raise ValueError('Invalid roster override for alternate discovery')
    allowed = {}
    for row in model.rows['uniforms']:
        if row['variant_code'] not in (2, 3, 4):continue
        home = [u for u in model.rows['uniforms'] if u['team_asset_id'] == row['team_asset_id'] and u['variant_code'] == 0]
        for selection in (False, True):
            name = asset_name(row, selection)
            if name not in candidates:continue
            if len(home) != 1:raise ValueError(name + ': no unique Home template')
            donor = asset_name(home[0], selection)
            if name in allowed and allowed[name] != donor:
                raise ValueError(name + ': conflicting Home templates')
            allowed[name] = donor
    unknown = sorted(set(candidates) - set(allowed))
    if unknown:
        raise ValueError('New alternate is not enabled in the loaded JB or overrides roster: '
                         + ', '.join(unknown[:8]) + '. Save the enabled roster to this overrides folder first.')
    additions = []
    for name in sorted(allowed):
        files = [p for p in candidates[name] if p.is_file()]
        if len(files) > 1:raise ValueError('Duplicate new alternate archive: ' + name)
        if files:
            additions.append(dict(name=name, path=files[0].relative_to(root).as_posix()))
        else:
            additions.append(dict(name=name, template=allowed[name]))
    return dict(schema=1, source_roster_sha256=digest(original), additions=additions,
                inferred=True, logo_templates={}, fallbacks=[])


class AdditionInputs:
    """Bounded virtual source entries for explicitly planned loose additions."""
    def __init__(self, base, folder):
        self.base = base; self.path = base.path
        self.entries = [dict(e) for e in base.entries]; self.additions = {}
        self.parts = base.parts; self.read_only = base.read_only
        self.game_info = getattr(base, 'game_info', {})
        self.toc_layout = base.toc_layout
        root = Path(folder).resolve(); reject_links(root); self.addition_folder = str(root)
        marker = root / 'team_assets.json'
        inferred = not marker.is_file()
        document = loose_alternate_document(base, root) if inferred else json.loads(marker.read_text(encoding='utf8'))
        self.discovery_warnings = []
        if document is None:return
        if document.get('schema') != 1 or not isinstance(document.get('additions'), list) or len(document['additions']) > 16384:
            raise ValueError('Invalid team asset folder manifest')
        require_college(base)
        if document.get('source_roster_sha256') != digest(read_named(base, 'roster_english.iff')):
            raise ValueError('Team asset folder belongs to another or changed source roster')
        self.logo_templates = document.get('logo_templates', {})
        self.alternate_fallbacks = document.get('fallbacks', [])
        import re
        if not isinstance(self.logo_templates, dict) or len(self.logo_templates)>1024 or any(not re.fullmatch(r'logo\d{3,4}', key) or not isinstance(value,str) or not re.fullmatch(r'logo\d{3,4}', value) for key,value in self.logo_templates.items()):
            raise ValueError('Invalid menu logo template mapping')
        hashes = {e['hash'] for e in base.entries}
        for row in document['additions']:
            name = row['name']
            if not re.fullmatch(r'(?:s\d{3,4}n?|(?:sel)?u[haxyz]\d{3,4})\.iff', name):
                raise ValueError('Unsupported team addition filename')
            if inferred and 'template' in row:
                matches = [e for e in base.entries if e['hash'] == hash_name(row['template'])]
                if len(matches) != 1:raise ValueError(name + ': Home template is missing or ambiguous')
                target = dict(matches[0])
                size = target['size']
                self.discovery_warnings.append(name + ': new alternate uses Home template ' + row['template'] + '; nested overrides will be applied')
            else:
                target = (root / row['path']).resolve()
                if not target.is_relative_to(root) or not target.is_file() or target.stat().st_size > 128 * 1024 * 1024:
                    raise ValueError('Invalid team addition file')
                size = target.stat().st_size
            identity = hash_name(name)
            if identity in hashes:
                raise ValueError('Team addition already exists in the selected JB: ' + name)
            hashes.add(identity)
            if size > 128 * 1024 * 1024:raise ValueError('New team asset exceeds 128 MiB')
            entry = dict(index=len(self.entries), hash=identity, name=name, name_hint=None, size=size, stored_size=size, content_size=size, offset=0, toc_flags=0, size_derived=False)
            self.entries.append(entry); self.additions[entry['index']] = (name, target)

    def read(self, entry):
        if entry['index'] in self.additions:
            target = self.additions[entry['index']][1]
            if isinstance(target, dict):data = self.base.read(target)
            else:
                if target.stat().st_size > 128 * 1024 * 1024:
                    raise ValueError('New team asset exceeds 128 MiB')
                data = target.read_bytes()
            start = entry.get('offset', 0); end = start + entry['size']
            if not 0 <= start <= end <= len(data):raise ValueError('Invalid new team asset read extent')
            return data[start:end]
        return self.base.read(entry)

    def chunks(self, entry, size=1024 * 1024):
        if entry['index'] in self.additions:
            data = self.read(entry)
            for offset in range(0, len(data), size):
                yield data[offset:offset + size]
        else:
            yield from self.base.chunks(entry, size)


def build_alternates(archive, patches, additions):
    """Resolve missing linked alternate containers against the final build inputs."""
    names = {e['hash']: e for e in archive.entries}
    edited = {e['hash']: data for e, data in patches}
    added = dict(additions)
    def read(name):
        identity = hash_name(name)
        if name in added:return added[name]
        if identity in edited:return edited[identity]
        if identity in names:return archive.read(names[identity])
        return None
    original = read('roster_english.iff')
    title = getattr(archive, 'game_info', {}).get('TITLE', '')
    if original is None or archive.read_only or (title and 'college hoops 2k8' not in title.casefold()):return added, []
    model = EditorModel(load_bytes(original))
    warnings = []
    for row in model.rows['uniforms']:
        if row['variant_code'] not in (2, 3, 4):continue
        home = [u for u in model.rows['uniforms'] if u['team_asset_id']==row['team_asset_id'] and u['variant_code']==0]
        for selection in (False, True):
            name = asset_name(row, selection)
            if hash_name(name) in names or name in added:continue
            if len(home)!=1:raise ValueError(f'{name}: missing alternate has no unique Home slot to clone')
            donor = asset_name(home[0], selection); raw = read(donor)
            if raw is None:raise ValueError(f'{name}: missing alternate and Home template {donor}')
            added[name] = raw
            warnings.append(f'{name}: alternate missing in overrides and JB; cloned Home slot {donor}')
    return added, warnings
