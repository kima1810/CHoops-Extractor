"""Clone an existing uniform into a new bank and append its roster record."""
from pathlib import Path
from ..archive.usrdir_reader import Archive
from ..archive.hash_names import hash_name
from ..archive.add_assets import build,validate_plan
from ..roster.editor_model import EditorModel
from ..roster.adapters import load_bytes
from ..roster.uniforms import append_uniform,encode_roster_iff,asset_name


def prepare(source, template, asset, variant, roster_payload=None):
    archive=Archive(source)
    by_hash={e['hash']:e for e in archive.entries}
    roster_entry=by_hash.get(hash_name('roster_english.iff'))
    if roster_entry is None:raise ValueError('Current JB folder has no roster_english.iff')
    original=archive.read(roster_entry)
    model=EditorModel(load_bytes(original))
    payload=bytes(model.data) if roster_payload is None else bytes(roster_payload)
    if roster_payload is not None:model=EditorModel(load_bytes(payload))
    if not 0<=template<len(model.rows.get('uniforms',[])):raise ValueError('Select an existing uniform record')
    row=model.rows['uniforms'][template]
    new_row={**row,'uniform_asset_id':asset,'variant_code':variant}
    additions={}
    for selection in (False,True):
        old_name=asset_name(row,selection);new_name=asset_name(new_row,selection)
        entry=by_hash.get(hash_name(old_name))
        if entry is None:raise ValueError('Template is missing uniform/menu asset: '+old_name)
        additions[new_name]=archive.read(entry)
    payload=append_uniform(payload,template,asset,variant)
    expanded=encode_roster_iff(original,payload)
    rebuilt=EditorModel(load_bytes(expanded))
    added=rebuilt.rows['uniforms'][-1]
    if asset_name(added)!=asset_name(new_row) or added['team_asset_id']!=row['team_asset_id'] or added['unlock_id']!=0:
        raise ValueError('New uniform routing failed validation')
    replacements={'roster_english.iff':expanded}
    validate_plan(source,additions,replacements)
    return additions,replacements


def add(source, template, asset, variant, output, job=None, roster_payload=None):
    additions,replacements=prepare(source,int(template),int(asset),int(variant),roster_payload)
    return build(source,additions,output,replacements,job)


def fill_five(source, output, job=None, roster_payload=None):
    """Give every current/classic school owner its missing supported banks."""
    from ..roster.uniforms import append_uniform_records,disabled_uniforms
    archive=Archive(source);by_hash={e['hash']:e for e in archive.entries}
    root=by_hash[hash_name('roster_english.iff')];original=archive.read(root)
    model=EditorModel(load_bytes(original if roster_payload is None else roster_payload))
    payload=bytes(model.data);rows=model.rows['uniforms']
    owners=sorted({r['uniform_owner_id'] for r in model.rows['teams'] if r['team_type_code'] in (0,1)})
    # Explicit five-bank builds restore already linked dormant alternates.
    dormant=disabled_uniforms(payload)
    for owner in owners:
        team=next(t for t in model.rows['teams'] if t['uniform_owner_id']==owner)
        for a,_ in dormant:
            if a>>22&1023==owner:model.set_alternate_enabled(team['index'],a>>8&7,True)
    payload=bytes(model.data);rows=model.rows['uniforms']
    additions={};specs=[];cache={};reserved=set(by_hash)
    for position,owner in enumerate(owners):
        if job:job.check();job.progress(position,len(owners),'Preparing five-bank school uniforms')
        owned=[r for r in rows if r['team_asset_id']==owner]
        available={r['variant_code']:r for r in owned}
        if 0 not in available or 1 not in available:raise ValueError('School is missing a verified home/away template')
        for variant in (2,3,4):
            if variant in available:continue
            donor=available.get(2,available[1])
            candidates=[owner]+[i for i in range(1024) if i!=owner]
            asset=next((i for i in candidates if all(hash_name(asset_name({'variant_code':variant,'uniform_asset_id':i},selection)) not in reserved for selection in (False,True))),None)
            if asset is None:raise ValueError('No free uniform selector in this bank')
            spec=(donor['index'],asset,variant);specs.append(spec)
            target={'variant_code':variant,'uniform_asset_id':asset}
            for selection in (False,True):
                old_name=asset_name(donor,selection);new_name=asset_name(target,selection)
                entry=by_hash.get(hash_name(old_name))
                if entry is None:raise ValueError('Template menu/uniform asset missing: '+old_name)
                if old_name not in cache:cache[old_name]=archive.read(entry)
                additions[new_name]=cache[old_name];reserved.add(hash_name(new_name))
    if not specs and payload==bytes(EditorModel(load_bytes(original if roster_payload is None else roster_payload)).data):return {'added_assets':[],'message':'All playable school teams already have five banks'}
    expanded=append_uniform_records(payload,specs) if specs else payload
    if job:job.check();job.progress(0,1,"Encoding expanded roster")
    roster=encode_roster_iff(original,expanded)
    check=EditorModel(load_bytes(roster))
    for owner in owners:
        if {r['variant_code'] for r in check.rows['uniforms'] if r['team_asset_id']==owner}!=set(range(5)):
            raise ValueError('Five-bank routing validation failed')
    result=build(source,additions,output,{'roster_english.iff':roster},job)
    result.update(school_owner_count=len(owners),new_uniform_record_count=len(specs))
    import json
    (Path(output)/"asset_build_report.json").write_text(json.dumps(result,indent=2),encoding="utf8")
    return result
