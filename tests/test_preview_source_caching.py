import json
import shutil
import uuid
from types import SimpleNamespace

import pytest
from choops_py.archive.manifests import OUTPUT, digest, safe_output
from choops_py.archive.usrdir_reader import Archive
from choops_py.studio.app import Window
from choops_py.studio.preview_cache import ImageCache
from choops_py.studio.preview_source import PreviewArchive
from choops_py.studio import services
from support import game_fixture, iff_fixture


def test_both_image_sources_remain_cached_and_memory_is_bounded():
    cache=ImageCache(limit=8);calls=[]
    def decode(value):
        calls.append(value)
        return (1,1),value
    assert cache.get('JB',lambda:decode(b'base'))[1]==b'base'
    assert cache.get('DDS',lambda:decode(b'over'))[1]==b'over'
    for key in ('JB','DDS'):
        cache.get(key,lambda:pytest.fail('unchanged source decoded again'))
    cache.get('third',lambda:decode(b'next'))
    assert cache.bytes==8 and len(cache.items)==2
    assert calls==[b'base',b'over',b'next']


@pytest.mark.gui
def test_archive_indexes_survive_source_switch_and_manifest_change_invalidates(qtbot,monkeypatch,tmp_path):
    window=Window();qtbot.addWidget(window)
    base=object();window.archive=base
    mod=tmp_path/'mod';mod.mkdir()
    for name in ('overrides.json','source_preconditions.json'):
        (mod/name).write_text('{}',encoding='utf8')
    window.mod_path.setText(str(mod))
    created=[]
    def snapshot(*args):
        result=SimpleNamespace(base=base);created.append(result);return result
    monkeypatch.setattr('choops_py.studio.preview_source.PreviewArchive',snapshot)
    def mode(checked):
        window.preview_overrides.blockSignals(True)
        window.preview_overrides.setChecked(checked)
        window.preview_overrides.blockSignals(False)
    mode(True);first=window.preview_archive()
    mode(False);assert window.preview_archive() is base
    mode(True);assert window.preview_archive() is first
    assert len(created)==1
    (mod/'overrides.json').write_text('{} ',encoding='utf8')
    assert window.preview_archive() is not first and len(created)==2


def test_materialized_jb_and_override_caches_are_separate_and_guard_tampering(monkeypatch):
    work=OUTPUT/'temp'/('preview_cache_'+uuid.uuid4().hex);work.mkdir(parents=True)
    monkeypatch.setattr(services,'OUTPUT',work)
    try:
        original=iff_fixture([b'base'],[(0xa7701f00,[0])])
        base=Archive(game_fixture(work/'game',original));entry=base.entries[0]
        mod=work/'mod';mod.mkdir()
        changed=iff_fixture([b'edit'],[(0xa7701f00,[0])]);asset=mod/'asset.bin';asset.write_bytes(changed)
        (mod/'overrides.json').write_text(json.dumps([dict(archive=entry['name'],kind='archive',subfile=None,path='asset.bin',sha256=digest(changed))]),encoding='utf8')
        (mod/'source_preconditions.json').write_text(json.dumps(dict(entries=[dict(index=0,hash=entry['hash'],sha256=digest(base.read(entry)))])),encoding='utf8')
        override=PreviewArchive(base,mod)
        jb_path=services.materialize(base,entry)
        override_path=services.materialize(override,override.entries[0])
        assert jb_path!=override_path
        assert jb_path.read_bytes().startswith(original)
        assert override_path.read_bytes()==changed
        assert services.materialize(base,entry)==jb_path
        assert services.materialize(override,override.entries[0])==override_path
        asset.write_bytes(changed+b'tampered')
        with pytest.raises(ValueError,match='checksum'):
            services.materialize(override,override.entries[0])
        assert services.materialize(base,entry)==jb_path
    finally:shutil.rmtree(safe_output(work))
