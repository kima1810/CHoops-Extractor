import json
import struct
import uuid
from pathlib import Path

import pytest

from support import iff_fixture, txtr_fixture
from test_roster_semantics import header_roster
from choops_py.archive.hash_names import hash_name
from choops_py.archive.manifests import OUTPUT
from choops_py.archive.usrdir_reader import Archive
from choops_py.modding.team_assets import prepare, inventory, available_ids, roster_model, export_folder, arena_selector
from choops_py.roster.adapters import load_bytes
from choops_py.roster.editor_model import EditorModel


def logo_fixture():
    import zlib
    from choops_py.formats.cdf_backed_iff_writer import name_trailer
    head, image = txtr_fixture(split=True)
    name='teamselectlogo.cdf'; end=148+len(name.encode('utf-16-be'))+2
    header=bytearray(end)
    struct.pack_into('>10I',header,0,0xf0985030,end,end,0,2,21,1,77,97,113)
    for off,start,size in ((40,end,len(head)),(72,end+176,len(image))):
        struct.pack_into('>8I',header,off,1,1,16,size,0,start,size,0)
    struct.pack_into('>I',header,104,5)
    struct.pack_into('>5I',header,108,zlib.crc32(b'logo003'),0x5c369069,2,0,0)
    struct.pack_into('>I',header,128,5)
    struct.pack_into('>4I',header,132,0,len(head),len(head),len(image))
    header[148:]=name.encode('utf-16-be')+b'\0\0'
    return bytes(header)+name_trailer([{'name':'logo003','type':'TXTR'}]), head+image


def game(tmp_path, *, shared=True, logos=False, collision=False, named=False):
    raw, starts = header_roster()
    for i in range(2):
        off = starts['teams'] + i * 704
        for field in (0x18c, 0x190, 0x194):struct.pack_into('>H', raw, off + field, 3 if shared else 3 + i)
        struct.pack_into('>H', raw, off + 0x18e, i)
        field = off + 0x44
        struct.pack_into('>i', raw, field, starts['arenas'] + 25 - field)
    # String code deliberately differs: native routing must use numeric 77.
    anchor = starts['arenas'] + 24
    struct.pack_into('>H', raw, anchor + 0x12, 77)
    for i, variant in enumerate((0, 1)):
        struct.pack_into('>II', raw, starts['uniforms'] + i * 8, (3 << 22) | (77 << 12) | (variant << 8) | 35, 0x48001000)
    payloads = {'roster_english.iff': iff_fixture([bytes(raw)], [(0xc61649b2, [0])], compressed=True),
                's077.iff': iff_fixture(txtr_fixture()),
                **{f'{prefix}u{bank}077.iff': iff_fixture(txtr_fixture()) for prefix in ('', 'sel') for bank in 'ha'}}
    if named:
        from choops_py.formats.cdf_backed_iff_writer import name_trailer
        for name in list(payloads):
            if name.startswith(('u','selu')):
                payloads[name] += name_trailer([{'name':'unif','type':'TXTR'}])
    if logos:
        logo_iff, cdf = logo_fixture()
        payloads.update({'teamselectlogo.iff':logo_iff,'teamselectlogo.cdf':cdf})
    if collision:payloads['ux003.iff']=iff_fixture(txtr_fixture())
    source = tmp_path / 'game'; usr = source / 'PS3_GAME' / 'USRDIR'; usr.mkdir(parents=True)
    rows = sorted(payloads, key=hash_name); cursor = 2048; body = bytearray(2048)
    for i, name in enumerate(rows):
        payload = payloads[name]
        struct.pack_into('>4I', body, 40 + i * 16, hash_name(name), cursor // 2048, 0, len(payload))
        body += payload + b'\0' * (-len(payload) % 2048); cursor = len(body)
    struct.pack_into('>6I', body, 0, 0xaa00b3bf, 2048, 1, 0, len(rows), 0)
    struct.pack_into('>II8s', body, 24, len(body) // 2048, 0, '0A\0\0'.encode('utf-16-be'))
    (usr / '0A').write_bytes(body)
    return source


def request(assets, team=0, target=900):
    return [dict(team=team, id=target, assets=assets)]


def test_separate_owner_preserves_shared_team_and_orders_all_five(tmp_path):
    source = game(tmp_path); archive = Archive(source); original, before = roster_model(archive)
    result = prepare(archive, request(['z']))
    after = EditorModel(load_bytes(result['replacements']['roster_english.iff']))
    assert [u['variant_code'] for u in after.rows['uniforms'] if u['team_asset_id'] == 900] == [0, 1, 2, 3, 4]
    assert [u['uniform_asset_id'] for u in after.rows['uniforms'] if u['team_asset_id'] == 900] == [77, 77, 900, 900, 900]
    assert len(result['additions']) == 6
    assert after.rows['teams'][0]['uniform_owner_id'] == 900
    assert after.rows['teams'][1] == before.rows['teams'][1]
    assert after.rows['teams'][0]['asset_id'] == 3
    assert bytes(after.data[before.row_offset('players', 0):before.row_offset('players', 0) + 2 * 308]) == bytes(before.data[before.row_offset('players', 0):before.row_offset('players', 0) + 2 * 308])
    assert roster_model(archive)[0] == original


def test_stadium_numeric_route_and_other_arena_references_survive_batch(tmp_path):
    source = game(tmp_path); archive = Archive(source)
    result = prepare(archive, [dict(team=i, id=900+i, assets=['stadium']) for i in range(2)])
    model = EditorModel(load_bytes(result['replacements']['roster_english.iff']))
    assert arena_selector(model, model.rows['teams'][0]) == (900, 0)
    assert arena_selector(model, model.rows['teams'][1]) == (901, 0)
    assert model.tables['arenas'][1] == 4
    assert set(result['additions']) == {'s900.iff', 's901.iff'}
    assert model.rows['arenas'][2]['arena_code']=='900' and model.rows['arenas'][3]['arena_code']=='901'
    for i in (0,1):
        field=model.row_offset('arenas',2+i)+0x24
        target=field+struct.unpack_from('>i',model.data,field)[0]-1
        assert target==model.row_offset('teams',i)+0x30


@pytest.mark.parametrize('changes', [request(['x'], target=1024), request(['x'], target=-1), request(['x'], target=3), request(['bogus']), request(['x'], team=5), request([])])
def test_bad_plans_do_not_write_source(tmp_path, changes):
    source = game(tmp_path); path = source/'PS3_GAME/USRDIR/0A'; old = path.read_bytes()
    with pytest.raises(ValueError):prepare(Archive(source), changes)
    assert path.read_bytes() == old


def test_list_reports_shared_active_inactive_and_numeric_stadium(tmp_path):
    archive = Archive(game(tmp_path)); _, model = roster_model(archive)
    rows = inventory(archive, model)
    assert 's077.iff' in rows[0]['stadium'] and 'Present' in rows[0]['stadium']
    assert 'Active' in rows[0]['h'] and rows[0]['x'] == 'Inactive'
    assert 'Uniforms 2' in rows[0]['shared']
    assert 3 not in available_ids(archive, model) and 77 not in available_ids(archive, model)


def test_unique_owner_can_fill_missing_without_consuming_another_id(tmp_path):
    archive = Archive(game(tmp_path, shared=False))
    result = prepare(archive, request(['x', 'y', 'z'], target=3))
    model = EditorModel(load_bytes(result['replacements']['roster_english.iff']))
    assert model.rows['teams'][0]['uniform_owner_id'] == 3
    assert len(model.rows['uniforms']) == 5
    assert set(result['additions']) == {f'{p}u{b}003.iff' for p in ('', 'sel') for b in 'xyz'}


def test_existing_unrelated_bank_filename_gets_separate_art_selector(tmp_path):
    from choops_py.modding.team_assets import read_named
    archive=Archive(game(tmp_path,shared=False,collision=True))
    before=read_named(archive,'ux003.iff')
    result=prepare(archive,request(['x'],target=3))
    model=EditorModel(load_bytes(result['replacements']['roster_english.iff']))
    alternate=next(u for u in model.rows['uniforms'] if u['team_asset_id']==3 and u['variant_code']==2)
    assert alternate['uniform_asset_id']!=3
    assert 'ux003.iff' not in result['additions']
    assert read_named(archive,'ux003.iff')==before


@pytest.mark.parametrize('workers', [1, 2])
def test_loose_folder_applies_additions_to_normal_preview_and_build(tmp_path, workers):
    from choops_py.studio.services import stage_folder
    from choops_py.studio.preview_source import PreviewArchive
    from choops_py.archive.build_copy import build
    archive = Archive(game(tmp_path)); result = prepare(archive, request(['stadium', 'x']))
    root = OUTPUT/'temp'/('team_assets_test_'+uuid.uuid4().hex)
    folder = export_folder(result, root/'loose', archive.path)
    report = stage_folder(archive.path, folder, root/'prepared', workers=workers)
    assert set(report['added_assets']) == {'s900.iff', 'ux900.iff', 'selux900.iff'}
    preview = PreviewArchive(archive, Path(report['mod']))
    for name in result['additions']:
        entry = next(e for e in preview.entries if e['name'] == name)
        assert preview.read(entry) == result['additions'][name]
    build(archive.path, report['mod'], root/'built')
    rebuilt = Archive(root/'built')
    assert {e['hash'] for e in rebuilt.entries} == {e['hash'] for e in archive.entries} | {hash_name(n) for n in result['additions']}
    assert arena_selector(roster_model(rebuilt)[1], roster_model(rebuilt)[1].rows['teams'][0]) == (900, 0)
    # A stale or tampered added file cannot silently enter a preview/build.
    doc = json.loads((Path(report['mod'])/'additions.json').read_text())
    target = Path(report['mod'])/doc['entries'][0]['path']; target.write_bytes(b'broken')
    with pytest.raises(ValueError, match='changed'):PreviewArchive(archive, report['mod'])


def test_team_matrix_checkboxes_and_auto_id(qtbot, tmp_path):
    from PySide6.QtCore import Qt
    from choops_py.studio.app import Window
    studio = Window(); qtbot.addWidget(studio)
    archive = Archive(game(tmp_path)); _, model = roster_model(archive)
    panel = studio.team_assets_panel
    panel.loaded((archive, model, inventory(archive, model), available_ids(archive, model)))
    assert panel.table.rowCount() == 2
    assert panel.table.item(0, 12).text() == str(model.rows['teams'][0]['asset_id'])
    assert ' * (' in panel.table.item(0, 5).text()
    assert rows_name(model, 1) in panel.table.item(0, 5).text()
    assert [panel.table.item(0, c).checkState() for c in range(5, 12)] == [
        Qt.CheckState.Checked, Qt.CheckState.Checked, Qt.CheckState.Checked,
        Qt.CheckState.Unchecked, Qt.CheckState.Unchecked, Qt.CheckState.Unchecked,
        Qt.CheckState.Unchecked]
    assert panel.requests() == []  # Existing checks must never clone every team.
    panel.check_missing()
    plans = panel.requests()
    assert len(plans) == 2 and plans[0]['id'] != plans[1]['id']
    assert plans[0]['assets'] == ['x', 'y', 'z']
    panel.search.setText('no match')
    assert panel.table.isRowHidden(0)


def rows_name(model, index):
    return model.rows['teams'][index].get('school_name') or 'Team'


def test_sharing_uses_actual_routes_not_just_owner_or_arena_row(qtbot, tmp_path):
    from choops_py.studio.app import Window
    studio = Window(); qtbot.addWidget(studio)
    archive = Archive(game(tmp_path, shared=False)); _, model = roster_model(archive)
    # Different arena rows and uniform owners still resolve to the same files.
    model.rows['teams'][1]['arena_index'] = 1
    physical = model.row_offset('arenas', 1) + 24
    struct.pack_into('>H', model.data, physical + 0x12, 77)
    model.rows['uniforms'] += [dict(u, team_asset_id=4) for u in list(model.rows['uniforms'])]
    rows = inventory(archive, model)
    assert rows[0]['asset_id'] != rows[1]['asset_id']
    for kind in ('stadium', 'h', 'a'):
        assert len(rows[0]['shared_assets'][kind]) == 1
        assert '[Team 1]' in rows[0]['shared_assets'][kind][0]
    assert rows[0]['shared_assets']['menu_logo'] == []
    panel = studio.team_assets_panel
    panel.loaded((archive, model, rows, available_ids(archive, model)))
    for column in (5, 6, 7):
        assert ' * (' in panel.table.item(0, column).text()
        assert '[Team 1]' in panel.table.item(0, column).toolTip()
    assert ' * (' not in panel.table.item(0, 11).text()
    assert panel.requests() == []


def test_existing_logo_and_uniforms_checked_without_mass_cloning(qtbot, tmp_path):
    from PySide6.QtCore import Qt
    from choops_py.studio.app import Window
    studio = Window(); qtbot.addWidget(studio)
    archive = Archive(game(tmp_path, logos=True)); _, model = roster_model(archive)
    rows = inventory(archive, model)
    assert set(rows[0]['present_assets']) == {'stadium', 'h', 'a', 'menu_logo'}
    panel = studio.team_assets_panel
    panel.loaded((archive, model, rows, available_ids(archive, model)))
    assert panel.table.item(0, 11).checkState() == Qt.CheckState.Checked
    panel.table.item(0, 8).setCheckState(Qt.CheckState.Checked)
    assert panel.requests() == [dict(team=0, id=panel.free[0], assets=['x'])]
    # Unchecking a present asset is not a destructive deactivation request.
    panel.table.item(0, 6).setCheckState(Qt.CheckState.Unchecked)
    panel.table.item(0, 8).setCheckState(Qt.CheckState.Unchecked)
    assert panel.requests() == []


@pytest.mark.parametrize('explicit_id', [False, True])
def test_existing_assets_can_still_be_cloned_for_one_team(qtbot, tmp_path, explicit_id):
    from choops_py.studio.app import Window
    studio = Window(); qtbot.addWidget(studio)
    archive = Archive(game(tmp_path, logos=True)); _, model = roster_model(archive)
    panel = studio.team_assets_panel
    result = (archive, model, inventory(archive, model), available_ids(archive, model))
    panel.loaded(result)
    if explicit_id:
        panel.table.item(0, 12).setText('900')
    else:
        panel.table.selectRow(0)
        panel.clone.click()
    plans = panel.requests()
    assert len(plans) == 1 and plans[0]['team'] == 0
    assert plans[0]['assets'] == ['stadium', 'h', 'a', 'menu_logo']
    if explicit_id:assert plans[0]['id'] == 900
    # Reload resets pending copy intent as well as the baseline checks.
    panel.loaded(result)
    assert panel.requests() == []


def test_missing_paired_asset_does_not_start_checked(qtbot, tmp_path):
    from PySide6.QtCore import Qt
    from choops_py.studio.app import Window
    studio = Window(); qtbot.addWidget(studio)
    archive = Archive(game(tmp_path)); _, model = roster_model(archive)
    archive.entries = [e for e in archive.entries if e['hash'] != hash_name('selua077.iff')]
    rows = inventory(archive, model)
    assert 'a' not in rows[0]['present_assets'] and 'Missing' in rows[0]['a']
    panel = studio.team_assets_panel
    panel.loaded((archive, model, rows, available_ids(archive, model)))
    assert panel.table.item(0, 7).checkState() == Qt.CheckState.Unchecked
    assert panel.requests() == []
    panel.table.item(0, 7).setCheckState(Qt.CheckState.Checked)
    assert panel.requests()[0]['assets'] == ['a']


def test_menu_logo_clones_and_stages_with_template_layout_and_live_preview(tmp_path):
    from choops_py.studio.services import stage_folder
    from choops_py.studio.preview_source import PreviewArchive
    from choops_py.formats.cdf_backed_iff import CDFPair
    from choops_py.modding.team_assets import read_named
    archive=Archive(game(tmp_path,logos=True))
    old=read_named(archive,'teamselectlogo.cdf')
    plan=prepare(archive,request(['menu_logo']))
    root=OUTPUT/'temp'/('team_assets_test_'+uuid.uuid4().hex)
    folder=export_folder(plan,root/'loose',archive.path)
    result=stage_folder(archive.path,folder,root/'prepared',workers=1)
    preview=PreviewArchive(archive,result['mod'])
    new_iff=read_named(preview,'teamselectlogo.iff');new_cdf=read_named(preview,'teamselectlogo.cdf')
    assert {r['name'] for r in CDFPair(new_iff,new_cdf).records}=={'logo003','logo900'}
    assert new_cdf[:len(old)]==old
    assert inventory(preview,roster_model(preview)[1])[0]['menu_logo']=='logo900 — Present'


def test_build_preflight_recovers_missing_linked_alternate_from_home(tmp_path):
    from choops_py.roster.uniforms import append_uniform,encode_roster_iff
    from choops_py.archive.importer import stage
    from choops_py.archive.build_copy import build
    archive=Archive(game(tmp_path)); original,model=roster_model(archive)
    modified=encode_roster_iff(original,append_uniform(bytes(model.data),1,888,2))
    root=OUTPUT/'temp'/('team_assets_test_'+uuid.uuid4().hex);root.mkdir(parents=True)
    incoming=root/'roster.iff';incoming.write_bytes(modified)
    stage(root/'prepared',incoming,'roster_english.iff')
    (root/'prepared/import_options.json').write_text('{"schema":1,"allow_archive_growth":true}')
    report=build(archive.path,root/'prepared',root/'built')
    assert set(report['added_assets'])=={'ux888.iff','selux888.iff'}
    assert len(report['warnings'])==2 and all('Home slot' in w for w in report['warnings'])
    from choops_py.modding.team_assets import read_named
    rebuilt=Archive(root/'built')
    from choops_py.archive.add_assets import meaningful_iff
    assert meaningful_iff(read_named(rebuilt,'ux888.iff'))==meaningful_iff(read_named(archive,'uh077.iff'))


def test_classic_shared_arena_forks_without_touching_classification_or_original(tmp_path):
    archive=Archive(game(tmp_path));_,model=roster_model(archive)
    from choops_py.roster.schema import TEAM_TYPE_OFFSET
    payload=bytearray(model.data);off=model.row_offset('teams',1)
    struct.pack_into('>I',payload,off+TEAM_TYPE_OFFSET,1<<15)
    original=bytes(payload)
    plan=prepare(archive,request(['stadium'],team=1),roster_payload=payload)
    updated=EditorModel(load_bytes(plan['replacements']['roster_english.iff']))
    assert updated.rows['teams'][1]['team_type_code']==1
    assert arena_selector(updated,updated.rows['teams'][1])==(900,0)
    assert arena_selector(updated,updated.rows['teams'][0])==(77,0)
    assert bytes(updated.data[off:off+0x44])==original[off:off+0x44]


@pytest.mark.parametrize('workers', [1, 2])
@pytest.mark.parametrize('artwork', [False, True])
def test_enabled_loose_alternate_without_manifest_imports_and_builds(tmp_path, workers, artwork):
    from choops_py.archive.build_copy import preflight
    from choops_py.formats.standard_iff import StandardIFF
    from choops_py.formats.standard_iff_writer import record_blocks
    from choops_py.modding.team_assets import AdditionInputs, read_named
    from choops_py.studio.services import stage_folder
    from choops_py.texture_tools.dds import linear_l8
    archive = Archive(game(tmp_path, shared=False, named=True))
    before = (archive.path/'0A').read_bytes()
    plan = prepare(archive, request(['x'], target=3))
    root = OUTPUT/'temp'/('loose_alternate_'+uuid.uuid4().hex)
    folder = root/'loose'; folder.mkdir(parents=True)
    (folder/'roster_english.iff').write_bytes(plan['replacements']['roster_english.iff'])
    nested = folder/'selux003'/'_unif.txtr'; nested.mkdir(parents=True)
    raw = txtr_fixture()[0]
    (nested.parent/'unif.txtr').write_bytes(raw)
    if artwork:(nested/'artwork.dds').write_bytes(linear_l8(4,4,1,b'\xff'*16))
    virtual = AdditionInputs(archive, folder)
    entry = next(e for e in virtual.entries if e['name']=='selux003.iff')
    template = read_named(archive,'seluh077.iff')
    assert virtual.read({**entry,'offset':4,'size':20}) == template[4:24]
    with pytest.raises(ValueError,match='extent'):virtual.read({**entry,'offset':len(template),'size':1})
    result = stage_folder(archive.path,folder,root/'prepared',workers=workers)
    assert result['added_assets']==['selux003.iff']
    assert any('Home template' in warning for warning in result['warnings'])
    _, patches = preflight(archive.path,Path(result['mod']))
    additions = json.loads((Path(result['mod'])/'additions.json').read_text())['entries']
    row = next(r for r in additions if r['archive']=='selux003.iff')
    payload = (Path(result['mod'])/row['path']).read_bytes()
    iff = StandardIFF(payload)
    block = record_blocks(iff,iff.records[0])[0][3]
    assert block[176:192] == (b'\xff'*16 if artwork else raw[176:192])
    assert (archive.path/'0A').read_bytes()==before
    # The missing gameplay partner must also reach the final synthetic TOC.
    from choops_py.archive.build_copy import build
    build(archive.path,result['mod'],root/'built')
    rebuilt = Archive(root/'built')
    assert hash_name('ux003.iff') in {e['hash'] for e in rebuilt.entries}
    assert read_named(rebuilt,'selux003.iff') == payload


def test_unlinked_loose_alternate_is_not_guessed(tmp_path):
    from choops_py.modding.team_assets import AdditionInputs
    archive = Archive(game(tmp_path))
    folder = tmp_path/'loose'; (folder/'seluz052').mkdir(parents=True)
    (folder/'seluz052/unif.txtr').write_bytes(txtr_fixture()[0])
    with pytest.raises(ValueError,match='not enabled.*Save the enabled roster'):
        AdditionInputs(archive,folder)
