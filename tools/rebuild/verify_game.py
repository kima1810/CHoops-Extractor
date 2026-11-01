"""Private workstation evidence. Inputs immutable; outputs ignored."""
import argparse
import hashlib
import json
import platform
import time
import uuid
from pathlib import Path

from choops_py.archive.usrdir_reader import Archive
from choops_py.archive.manifests import OUTPUT
from choops_py.studio.services import extract, stage_folder
from choops_py.formats.standard_iff import StandardIFF
from choops_py.formats.standard_iff_writer import record_blocks, replace_records
from choops_py.formats.cdf_backed_iff import CDFPair
from choops_py.roster.editor_model import EditorModel
from choops_py.roster.adapters import load_bytes
from choops_py.roster.workflow import save_model
from choops_py.texture_tools.pipeline import export, import_texture
from choops_py.archive.build_copy import build


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('--full-rip', action='store_true')
    parser.add_argument('--build', action='store_true')
    args = parser.parse_args()
    work = OUTPUT/'smoke_tests'/('rebuild_'+uuid.uuid4().hex)
    work.mkdir(parents=True)
    result = {'platform': platform.platform(), 'python': platform.python_version(),
              'work': str(work), 'measurements': {}, 'runtime': 'NOT RUN'}
    def timed(name, function):
        start = time.perf_counter()
        value = function()
        result['measurements'][name] = round(time.perf_counter()-start, 4)
        print(name, result['measurements'][name], flush=True)
        return value
    archive = timed('index_seconds', lambda: Archive(args.source))
    result['archive_entries'] = len(archive.entries)
    names = ('ua000.iff', 'uh000.iff', 's000.iff', 'roster_english.iff',
             'teamselectlogo.iff', 'teamselectlogo.cdf', 'sideline_items.iff', 'sideline_items.cdf')
    entries = [e for e in archive.entries if e['name'] in names]
    result['absent'] = sorted(set(names)-{e['name'] for e in entries})
    rip = work/'selected'
    result['selective'] = timed('selective_seconds', lambda: extract(archive, entries, rip))
    replacement = work/'replacements'
    replacement.mkdir()
    texture_results = {}
    for name in ('ua000.iff','uh000.iff','s000.iff','teamselectlogo.iff','sideline_items.iff'):
        source = rip/name
        if not source.exists():
            continue
        cdf = source.with_suffix('.cdf')
        report = timed(name+'_export_seconds', lambda: export(source, work/(name+'_textures'), cdf if cdf.exists() else None))
        texture_results[name] = {'raw':report['raw_exported'], 'dds':report['dds_exported'],
            'failures':[{'name':t['texture_name'],'status':t['converter_status'],'warnings':t['warnings']} for t in report['textures'] if not t['dds_output_path']]}
        if name == 'ua000.iff':
            atlas = next(t for t in report['textures'] if t['texture_name']=='jersey_numbers')
            modified = bytearray(Path(atlas['dds_output_path']).read_bytes())
            modified[128] ^= 1
            edited = work/'edited_atlas.dds'
            edited.write_bytes(modified)
            result['atlas_edit'] = timed('atlas_import_seconds', lambda: import_texture(source, 'jersey_numbers', edited, replacement/name))
        if not cdf.exists():
            iff=StandardIFF(source.read_bytes())
            result[name+'_unchanged_roundtrip'] = replace_records(iff, {}) == iff.raw
        else:
            pair=CDFPair(source.read_bytes(),cdf.read_bytes())
            result[name+'_pair_records']=len(pair.records)
    result['texture_exports'] = texture_results
    source = rip/'roster_english.iff'
    model = timed('roster_load_seconds', lambda: EditorModel.open(source))
    row = next(r for r in model.rows['players'] if 0<=r['jersey_number']<99)
    timed('roster_edit_seconds', lambda: model.edit('players',row['index'],'jersey_number',row['jersey_number']+1))
    result['roster_edit'] = timed('roster_save_seconds', lambda: save_model(model,replacement/source.name))
    reopened=EditorModel.open(replacement/source.name)
    assert reopened.rows['players'][row['index']]['jersey_number']==row['jersey_number']+1
    result['roster_changed_bytes'] = sum(a!=b for a,b in zip(model.original,model.data))
    if args.full_rip:
        result['full_rip'] = timed('full_rip_seconds', lambda: extract(archive,archive.entries,work/'full_raw'))
    mod = OUTPUT/'builds'/('mod_'+uuid.uuid4().hex)
    result['stage'] = timed('stage_seconds', lambda: stage_folder(args.source,replacement,mod))
    result['dry_run'] = timed('dry_run_seconds', lambda: build(args.source,mod,OUTPUT/'builds'/('preview_'+uuid.uuid4().hex),dry_run=True))
    if args.build:
        result['build'] = timed('build_seconds', lambda: build(args.source,mod,OUTPUT/'builds'/('verified_'+uuid.uuid4().hex)))
    (work/'evidence.json').write_text(json.dumps(result,indent=2,default=str))
    print('Evidence',work/'evidence.json',flush=True)

if __name__ == '__main__':
    main()
