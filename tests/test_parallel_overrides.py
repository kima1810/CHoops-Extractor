import json
import multiprocessing
import shutil
import struct
import uuid
from pathlib import Path
import pytest
from support import iff_fixture
from choops_py.archive.hash_names import hash_name
from choops_py.archive.manifests import OUTPUT,safe_output
from choops_py.archive.parallel_import import policy
from choops_py.studio.services import stage_folder,JobContext,Cancelled


@pytest.fixture
def workspace():
    root=OUTPUT/'temp'/('parallel_import_'+uuid.uuid4().hex);root.mkdir(parents=True)
    yield root
    shutil.rmtree(safe_output(root))


def inputs(root,count=3):
    source=root/'game';usr=source/'PS3_GAME'/'USRDIR';usr.mkdir(parents=True)
    base=iff_fixture(records=[(0xa7701f00,[0])]);size=(count+1)*2048
    data=bytearray(size);struct.pack_into('>6I',data,0,0xaa00b3bf,2048,1,0,count,0)
    struct.pack_into('>II8s',data,24,size//2048,0,'0A\0\0'.encode('utf-16-be'))
    folder=root/'overrides';folder.mkdir()
    for i in range(count):
        name=f'ua{i:03d}.iff';offset=(i+1)*2048
        struct.pack_into('>4I',data,40+i*16,hash_name(name),offset//2048,0,len(base))
        data[offset:offset+len(base)]=base
        (folder/name).write_bytes(iff_fixture([('edited'+str(i)).encode()],[(0xa7701f00,[0])]))
    (usr/'0A').write_bytes(data);return source,folder


def rows(mod):
    return json.loads((Path(mod)/'overrides.json').read_text(encoding='utf8'))


def test_policy_caps_cpu_and_memory(monkeypatch):
    monkeypatch.setattr('choops_py.archive.parallel_import.resources',lambda:(32,16*1024**3))
    assert policy(100)[0]==6
    assert policy(2)[0]==2
    assert policy(100,2)[0]==2
    monkeypatch.setattr('choops_py.archive.parallel_import.resources',lambda:(2,512*1024**2))
    assert policy(100)[0]==1


def test_spawn_parallel_matches_serial_and_reuses_unchanged_archives(workspace,monkeypatch):
    monkeypatch.setattr('choops_py.archive.parallel_import.resources',lambda:(8,8*1024**3))
    source,folder=inputs(workspace)
    serial=stage_folder(source,folder,workspace/'serial',workers=1)
    parallel=stage_folder(source,folder,workspace/'parallel',workers=2)
    assert parallel['parallel_workers']==2
    assert rows(serial['mod'])==rows(parallel['mod'])
    for row in rows(serial['mod']):assert (Path(serial['mod'])/row['path']).read_bytes()==(Path(parallel['mod'])/row['path']).read_bytes()
    def should_not_compile(*args):pytest.fail('Unchanged archives should reuse completed preparation')
    monkeypatch.setattr('choops_py.archive.folder_import.compile_group',should_not_compile)
    cached=stage_folder(source,folder,Path(serial['mod']),workers=1)
    assert cached['reused_archives']==3 and rows(cached['mod'])==rows(serial['mod'])


def test_input_change_and_tampered_cached_output_recompile_only_affected(workspace,monkeypatch):
    source,folder=inputs(workspace)
    first=stage_folder(source,folder,workspace/'first',workers=1)
    (folder/'ua001.iff').write_bytes(iff_fixture([b'new artwork'],[(0xa7701f00,[0])]))
    changed=stage_folder(source,folder,Path(first['mod']),workers=1)
    assert changed['reused_archives']==2
    row=rows(changed['mod'])[0];path=Path(changed['mod'])/row['path'];path.write_bytes(b'tampered')
    repaired=stage_folder(source,folder,Path(changed['mod']),workers=1)
    assert repaired['reused_archives']==2
    assert (Path(repaired['mod'])/row['path']).read_bytes()!=b'tampered'
    assert path.read_bytes()==b'tampered'


def test_parallel_error_and_cancellation_remove_partial_workspace(workspace,monkeypatch):
    monkeypatch.setattr('choops_py.archive.parallel_import.resources',lambda:(8,8*1024**3))
    source,folder=inputs(workspace)
    from choops_py.archive.folder_import import discover
    def corrupt_after_discovery(*args):
        result=discover(*args)
        (folder/'ua001.iff').write_bytes(bytes.fromhex('ff3bef94')+b'invalid IFF')
        return result
    with monkeypatch.context() as context:
        context.setattr('choops_py.archive.folder_import.discover',corrupt_after_discovery)
        with pytest.raises(ValueError,match='ua001.iff'):stage_folder(source,folder,workspace/'failed',workers=2)
    assert not (workspace/'failed').exists() and not list(workspace.glob('.mod_*'))
    (folder/'ua001.iff').write_bytes(iff_fixture([b'fixed'],[(0xa7701f00,[0])]))
    job=JobContext()
    def cancel(done,total,label):
        if label.startswith('Overrides prepared:'):job.cancelled.set()
    job.progress=cancel
    with pytest.raises(Cancelled):stage_folder(source,folder,workspace/'cancelled',job,workers=2)
    assert not (workspace/'cancelled').exists() and not list(workspace.glob('.mod_*'))
    assert not any(p.name.startswith('CHoops-DDS-') for p in multiprocessing.active_children())


def test_module_fingerprints_work_without_source_files(monkeypatch):
    from types import SimpleNamespace
    from choops_py.core.code_identity import module_bytes
    class Loader:
        def get_code(self,name):return compile('answer=42','frozen-module','exec')
    monkeypatch.setattr('importlib.util.find_spec',lambda name:SimpleNamespace(origin='missing.py',loader=Loader()))
    assert module_bytes('frozen.module')==module_bytes('frozen.module')
    assert b'answer' in module_bytes('frozen.module')


def test_added_archive_does_not_collide_with_reused_output_names(workspace):
    source,folder=inputs(workspace)
    path=folder/'ua000.iff';payload=path.read_bytes();path.unlink()
    first=stage_folder(source,folder,workspace/'first',workers=1)
    path.write_bytes(payload)
    second=stage_folder(source,folder,Path(first['mod']),workers=1)
    assert second['reused_archives']==2 and second['staged']==3
    assert len({row['path'] for row in rows(second['mod'])})==3
