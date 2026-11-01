import json
import shutil
import uuid
from pathlib import Path
import pytest
from support import game_fixture,iff_fixture
from choops_py.archive.usrdir_reader import Archive
from choops_py.archive.manifests import OUTPUT,digest,safe_output
from choops_py.archive.folder_import import discover
from choops_py.studio.live_overrides import describe_groups
from choops_py.studio.preview_source import PreviewArchive
from choops_py.studio import services


def test_live_files_replace_stale_snapshot_and_invalidate_materialized_cache(monkeypatch):
    work=OUTPUT/'temp'/('live_preview_'+uuid.uuid4().hex);work.mkdir(parents=True)
    monkeypatch.setattr(services,'OUTPUT',work)
    try:
        original=iff_fixture([b'base'],[(0xa7701f00,[0])])
        base=Archive(game_fixture(work/'game',original));entry=base.entries[0]
        folder=work/'loose';folder.mkdir();loose=folder/entry['name']
        current=iff_fixture([b'current'],[(0xa7701f00,[0])]);loose.write_bytes(current)
        mod=work/'mod';mod.mkdir();old=iff_fixture([b'stale'],[(0xa7701f00,[0])]);(mod/'old.bin').write_bytes(old)
        (mod/'overrides.json').write_text(json.dumps([dict(archive=entry['name'],kind='archive',subfile=None,path='old.bin',sha256=digest(old))]),encoding='utf8')
        (mod/'source_preconditions.json').write_text(json.dumps(dict(entries=[dict(index=entry['index'],hash=entry['hash'],sha256=digest(base.read(entry)))])),encoding='utf8')
        groups=discover(base,folder)['groups']
        (mod/'preview_inputs.json').write_text(json.dumps(describe_groups(groups,folder,base)),encoding='utf8')
        archive=PreviewArchive(base,mod)
        path=services.materialize(archive,archive.entries[0])
        assert path.read_bytes()==current and path.read_bytes()!=old
        assert services.materialize(archive,archive.entries[0])==path
        updated=iff_fixture([b'updated artwork'],[(0xa7701f00,[0])]);loose.write_bytes(updated)
        changed=services.materialize(archive,archive.entries[0])
        assert changed!=path and changed.read_bytes()==updated
        assert (mod/'old.bin').read_bytes()==old
        assert base.read(entry).startswith(original)
        metadata=json.loads((mod/'preview_inputs.json').read_text(encoding='utf8'))
        metadata['groups'][0]['source_sha256']='wrong'
        (mod/'preview_inputs.json').write_text(json.dumps(metadata),encoding='utf8')
        with pytest.raises(ValueError,match='changed JB'):
            services.materialize(PreviewArchive(base,mod),archive.entries[0])
        loose.unlink()
        with pytest.raises(OSError):services.materialize(archive,archive.entries[0])
    finally:shutil.rmtree(safe_output(work))
