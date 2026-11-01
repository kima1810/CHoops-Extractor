"""Queued edits, opaque archive gaps and user-chosen build destinations."""
import wave

import pytest

from support import game_fixture,iff_fixture
from choops_py.archive.add_assets import build,plan
from choops_py.archive.manifests import build_destination
from choops_py.archive.usrdir_reader import Archive
from choops_py.audio_tools.pending import PendingSongs


def wav(path):
    with wave.open(str(path),'wb') as stream:
        stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(48000)
        stream.writeframes(b'\0\0'*32)
    return path


def test_queue_accumulates_replaces_removes_and_protects_source(tmp_path):
    queue=PendingSongs();archive=object();other=object();path=wav(tmp_path/'one.wav')
    for i in (1,2):queue.add(archive,dict(bank='cribmusic',index=i,title=str(i)),path)
    queue.add(archive,dict(bank='cribmusic',index=1,title='updated'),path)
    assert len(queue.replacements(archive))==2
    assert queue.replacements(archive)[0][0]['title']=='updated'
    with pytest.raises(ValueError,match='different JB'):queue.replacements(other)
    with pytest.raises(ValueError,match='changing'):queue.add(other,dict(bank='cribmusic',index=3),path)
    queue.clear()
    with pytest.raises(ValueError,match='at least'):queue.replacements(archive)


def test_queue_reopens_same_source_and_preserves_new_choices_during_save(tmp_path):
    from types import SimpleNamespace
    source=tmp_path/'source';source.mkdir();(source/'0A').write_bytes(b'bank')
    archive=SimpleNamespace(path=source,parts=[dict(name='0A')])
    reopened=SimpleNamespace(path=source,parts=[dict(name='0A')])
    queue=PendingSongs();row=dict(bank='cribmusic',index=0,title='one')
    queue.add(archive,row,wav(tmp_path/'old.wav'));snapshot=queue.replacements(reopened)
    queue.add(reopened,row,wav(tmp_path/'new.wav'))
    queue.saved(archive,snapshot)
    assert queue.replacements(reopened)[0][1].name=='new.wav'
    (source/'0A').write_bytes(b'changed bank')
    with pytest.raises(ValueError,match='different JB'):queue.replacements(reopened)


def test_replacement_keeps_nonzero_header_gap_and_external_output(tmp_path):
    source=game_fixture(tmp_path/'source',iff_fixture([b'original']))
    path=source/'PS3_GAME/USRDIR/0A';raw=bytearray(path.read_bytes());raw[100:108]=b'OPAQUE!!';path.write_bytes(raw)
    changed=iff_fixture([b'changed'*400])
    output=tmp_path/'user-chosen-drive'/'New JB'
    result=build(source,{},output,{'ua000.iff':changed})
    rebuilt=(output/'PS3_GAME/USRDIR/0A').read_bytes()
    assert rebuilt[56:2048]==raw[56:2048]
    assert path.read_bytes()==raw
    archive=Archive(output)
    assert archive.read(archive.entries[0])[:len(changed)]==changed
    assert result['source_unchanged']
    # An addition may consume zeros at 56..72 without touching opaque 100..108.
    _,header,*_=plan(source,{'uy777.iff':iff_fixture()})
    assert header[100:108]==b'OPAQUE!!'
    raw[56]=1;path.write_bytes(raw)
    with pytest.raises(ValueError,match='TOC slots'):plan(source,{'uy777.iff':iff_fixture()})


def test_build_destination_protects_inputs_and_parent(tmp_path):
    source=tmp_path/'source';source.mkdir()
    for path in (source,source/'child',tmp_path):
        with pytest.raises(ValueError,match='overlaps'):build_destination(path,[source])
    assert build_destination(tmp_path/'sibling',[source])==tmp_path/'sibling'


def test_repack_preserves_opaque_gap_when_body_addresses_do_not_shift(tmp_path):
    from choops_py.archive.repack import build as repack
    source=game_fixture(tmp_path/'source',iff_fixture([b'original']))
    path=source/'PS3_GAME/USRDIR/0A';raw=bytearray(path.read_bytes());raw[100:108]=b'OPAQUE!!';path.write_bytes(raw)
    output=tmp_path/'repacked'
    report=repack(source,{},output,{'ua000.iff':iff_fixture([b'changed'*400])})
    assert report['bank_count']>1
    assert (output/'PS3_GAME/USRDIR/0A').read_bytes()[100:2048]==raw[100:2048]
    assert path.read_bytes()==raw


@pytest.mark.gui
def test_gui_queues_two_songs_then_saves_once_and_keeps_queue_on_failure(qtbot,monkeypatch,tmp_path):
    from choops_py.studio.app import Window
    from choops_py.audio_tools import workflow
    window=Window();qtbot.addWidget(window);window.archive=object()
    path=wav(tmp_path/'one.wav')
    monkeypatch.setattr('choops_py.studio.app.QFileDialog.getOpenFileName',lambda *a:(str(path),''))
    for index in (0,1):
        monkeypatch.setattr(window,'audio_selected',lambda index=index:[dict(bank='cribmusic',index=index,title=str(index))])
        window.audio_replace_selected()
    assert len(window.pending_songs.items)==2
    output=tmp_path/'songs'
    monkeypatch.setattr(window,'audio_output_path',lambda *a:output)
    calls=[]
    def replace(archive,rows,out,job):
        calls.append((rows,out));return {}
    monkeypatch.setattr(workflow,'replace_tracks',replace)
    monkeypatch.setattr(window,'run_job',lambda label,work,callback,**kw:work(None))
    window.audio_save_pending()
    assert len(window.pending_songs.items)==2  # No success callback: preserve pending edits.
    assert len(calls)==1 and len(calls[0][0])==2 and calls[0][1]==output
    monkeypatch.setattr(window,'run_job',lambda label,work,callback,**kw:callback(work(None)))
    window.audio_save_pending()
    assert not window.pending_songs.items


def test_fixed_size_builder_accepts_external_destination_and_report(tmp_path,monkeypatch):
    from choops_py.archive import build_copy
    original=iff_fixture([b'original'])
    source=game_fixture(tmp_path/'source',original);mod=tmp_path/'mod';mod.mkdir()
    archive=Archive(source);entry=archive.entries[0];data=archive.read(entry)
    monkeypatch.setattr(build_copy,'preflight',lambda *a:(archive,[(entry,data)]))
    output=tmp_path/'manual'/'my build'
    output.mkdir(parents=True)
    report=build_copy.build(source,mod,output)
    assert (output/'build_manifest.json').is_file()
    assert report['validation']['all_unpatched_bytes_exact']
    assert (source/'PS3_GAME/USRDIR/0A').read_bytes()==(output/'PS3_GAME/USRDIR/0A').read_bytes()
