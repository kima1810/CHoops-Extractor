import struct

import pytest

from support import iff_fixture
from choops_py.archive.usrdir_reader import Archive
from choops_py.archive.hash_names import hash_name
from choops_py.archive.build_io import archive_header
from choops_py.archive.add_assets import build as append_build
from choops_py.archive.repack import build as repack_build
from choops_py.studio.build_diagnostics import diagnose,failure_summary


def split_header_game(path):
    root=path/'PS3_GAME/USRDIR';root.mkdir(parents=True)
    data=bytearray(12288)
    struct.pack_into('>6I',data,0,0xaa00b3bf,2048,2,0,1,0)
    for i,(name,size) in enumerate((('0A',4096),('0B',8192))):struct.pack_into('>II8s',data,24+i*16,size//2048,0,name.ljust(4,'\0').encode('utf-16-be'))
    payload=iff_fixture([b'original'],[(0xa7701f00,[0])])
    struct.pack_into('>4I',data,56,hash_name('ua000.iff'),3,0,len(payload))
    data[4300:4308]=b'KEEPTHIS';data[6144:6144+len(payload)]=payload
    (root/'0A').write_bytes(data[:4096]);(root/'0B').write_bytes(data[4096:])
    return path,bytes(data[:6144])


@pytest.mark.parametrize('writer',[append_build,repack_build])
def test_header_prefix_spanning_banks_is_preserved_on_replacement(tmp_path,writer):
    source,original_header=split_header_game(tmp_path/'source')
    archive=Archive(source);assert archive_header(archive)==original_header
    snapshots={p['name']:(archive.path/p['name']).read_bytes() for p in archive.parts}
    payload=iff_fixture([b'replaced'],[(0xa7701f00,[0])])
    output=tmp_path/'manual_output'
    writer(source,{},output,replacements={'ua000.iff':payload})
    result=Archive(output)
    assert result.read(result.entries[0])[:len(payload)]==payload
    assert result.read(dict(offset=4300,size=8))==b'KEEPTHIS'
    assert all((archive.path/name).read_bytes()==data for name,data in snapshots.items())
    if writer==append_build:assert result.parts[0]['size']==4096


def test_header_source_damage_names_bank_and_resolution(tmp_path):
    source,_=split_header_game(tmp_path/'source');archive=Archive(source)
    (archive.path/'0B').write_bytes(b'short')
    with pytest.raises(ValueError,match='0B') as raised:archive_header(archive)
    assert 'Restore missing/truncated source banks' in str(raised.value)
    issue=diagnose(raised.value)
    assert 'source archive header' in issue['problem']
    assert 'DDS' in issue['suggested_fix']
    assert '0B' in failure_summary('Build JB',raised.value)


def test_toc_can_cross_first_bank_boundary(tmp_path):
    root=tmp_path/'PS3_GAME/USRDIR';root.mkdir(parents=True)
    # 130 rows put the TOC end beyond the first 2 KiB bank.
    count=130;first=4096;data=bytearray(first+count*2048)
    struct.pack_into('>6I',data,0,0xaa00b3bf,2048,2,0,count,0)
    for i,(name,size) in enumerate((('0A',2048),('0B',len(data)-2048))):struct.pack_into('>II8s',data,24+i*16,size//2048,0,name.ljust(4,'\0').encode('utf-16-be'))
    for i in range(count):struct.pack_into('>4I',data,56+i*16,i+1,2+i,0,16)
    (root/'0A').write_bytes(data[:2048]);(root/'0B').write_bytes(data[2048:])
    archive=Archive(tmp_path)
    assert len(archive.entries)==count and archive_header(archive)==data[:first]


def test_override_error_advice_keeps_named_target():
    message='ValueError: ua001.iff: texture_4: unsupported_texture_layout'
    issue=diagnose(message)
    assert issue['detail']==message and 'DDS' in issue['problem']
    assert 'ua001.iff' in failure_summary('Load overrides',message)
    assert 'manual resolution' in diagnose('Duplicate DDS target: s258/floor/texture_0.dds')['suggested_fix']


def test_truncated_bank_in_archive_constructor_keeps_filename_and_sizes(tmp_path):
    source,_=split_header_game(tmp_path/'source')
    (source/'PS3_GAME/USRDIR/0B').write_bytes(b'short')
    with pytest.raises(ValueError,match='0B; expected 8,192 bytes, found 5') as error:Archive(source)
    assert 'restore' in diagnose(error.value)['suggested_fix'].lower()


@pytest.mark.gui
def test_gui_keeps_actionable_override_failure_details(qtbot,monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    from choops_py.studio.app import Window
    window=Window();qtbot.addWidget(window);messages=[]
    monkeypatch.setattr(QMessageBox,'warning',lambda *args:messages.append(args[2]))
    window._job_label='Load overrides folder and check compatibility'
    window.show_error('ValueError: s258.iff / floor / texture_0: Duplicate DDS target')
    detail=window.build_details.toPlainText()
    assert 's258.iff / floor / texture_0' in detail and 'Suggested fix:' in detail
    assert 'manual resolution' in detail and messages[0]==detail
    window.job_finished();assert not window._job_label
