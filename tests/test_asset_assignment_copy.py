import struct

import pytest

from test_team_assets import game, request
from choops_py.archive.usrdir_reader import Archive
from choops_py.modding.team_assets import prepare, roster_model, arena_selector, roster_plan, apply_plan
from choops_py.roster.asset_assignments import copy_assignments, apply_to_editor
from choops_py.roster.editor_model import EditorModel
from choops_py.roster.adapters import load_bytes
from choops_py.roster.uniforms import set_alternate_enabled, disabled_uniforms
from choops_py.archive.manifests import OUTPUT
import uuid


def test_copy_activation_and_arena_preserves_destination_roster_and_undo(tmp_path):
    archive=Archive(game(tmp_path));_,target=roster_model(archive)
    plan=prepare(archive,request(['stadium','x']))
    donor=EditorModel(load_bytes(plan['replacements']['roster_english.iff']))
    donor=EditorModel(load_bytes(set_alternate_enabled(bytes(donor.data),900,2,False)))
    original=bytes(target.data);old_tables=dict(target.tables)
    result,changes=copy_assignments(target,donor,[0])
    check=EditorModel(load_bytes(result))
    assert arena_selector(check,check.rows['teams'][0])==(900,0)
    assert arena_selector(check,check.rows['teams'][1])==(77,0)
    assert changes[0]['active']==[0,1] and changes[0]['inactive']==[2]
    assert len(disabled_uniforms(result))==1
    start=target.row_offset('players',0)
    assert result[start:start+616]==original[start:start+616]
    start=target.row_offset('conferences',0)
    assert result[start:start+2964*2]==original[start:start+2964*2]
    apply_to_editor(target,result)
    assert target.tables['arenas'][1]==3
    target.undo();assert bytes(target.data)==original and target.tables==old_tables
    target.redo();assert bytes(target.data)==result and target.validate()['valid']


def test_copy_shared_owner_activation_isolates_unselected_team(tmp_path):
    from choops_py.roster.uniforms import append_uniform
    archive=Archive(game(tmp_path));_,target=roster_model(archive)
    donor=EditorModel(load_bytes(append_uniform(bytes(target.data),0,888,2)))
    result,_=copy_assignments(target,donor,[0])
    check=EditorModel(load_bytes(result))
    first,second=check.rows['teams']
    assert first['uniform_owner_id']!=second['uniform_owner_id']
    assert [u['variant_code'] for u in check.rows['uniforms'] if u['team_asset_id']==second['uniform_owner_id']]==[0,1]
    assert [u['uniform_asset_id'] for u in check.rows['uniforms'] if u['team_asset_id']==first['uniform_owner_id']]==[77,77,888]


def test_copy_mismatched_team_id_is_rejected_without_changes(tmp_path):
    archive=Archive(game(tmp_path));_,target=roster_model(archive);_,donor=roster_model(archive)
    original=bytes(target.data)
    struct.pack_into('>H',donor.data,donor.row_offset('teams',0)+0x18e,99);donor.reload()
    with pytest.raises(ValueError,match='Team ID'):copy_assignments(target,donor,[0])
    assert bytes(target.data)==original and not target.history


def test_save_community_roster_changes_to_overrides_before_build(tmp_path):
    archive=Archive(game(tmp_path));_,model=roster_model(archive)
    model.edit('players',0,'jersey_number',23)
    root=OUTPUT/'temp'/('team_assets_test_'+uuid.uuid4().hex)
    result=apply_plan(archive.path,roster_plan(archive,model.data),archive,root/'loose',root/'prepared')
    from choops_py.studio.preview_source import PreviewArchive
    _,saved=roster_model(PreviewArchive(archive,result['mod']))
    assert saved.rows['players'][0]['jersey_number']==23


def test_applied_expansion_syncs_open_roster_so_later_save_keeps_new_links(tmp_path):
    from types import SimpleNamespace
    from choops_py.studio.team_assets import synchronize_editor
    archive=Archive(game(tmp_path));_,editor=roster_model(archive)
    editor.edit('players',0,'jersey_number',23)
    before=bytes(editor.data)
    plan=prepare(archive,request(['stadium','x']),roster_payload=before)
    seen=[];owner=SimpleNamespace(roster=editor,display_roster=seen.append)
    synchronize_editor(owner,plan['replacements']['roster_english.iff'])
    assert seen==[editor] and editor.rows['teams'][0]['uniform_owner_id']==900
    assert editor.rows['players'][0]['jersey_number']==23
    assert arena_selector(editor,editor.rows['teams'][0])==(900,0)
    editor.undo();assert bytes(editor.data)==before
