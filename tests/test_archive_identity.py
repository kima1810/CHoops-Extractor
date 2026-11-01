import struct
from support import game_fixture,iff_fixture
from choops_py.archive.usrdir_reader import Archive
from choops_py.archive.hash_names import hash_name
from choops_py.archive.identity import recover,apply
from choops_py.formats.cdf_backed_iff_writer import name_trailer


def test_internal_labels_preserve_hash_and_candidate_names_require_crc(tmp_path):
    payload=iff_fixture(records=[(0xe26c9b5d,[0])])+name_trailer([{'name':'hi_shoe1','type':'SCNE'}])
    source=game_fixture(tmp_path/'game',payload)
    bank=source/'PS3_GAME'/'USRDIR'/'0A'
    raw=bytearray(bank.read_bytes());identity=hash_name('mystery_model.iff')
    struct.pack_into('>I',raw,40,identity);bank.write_bytes(raw)
    archive=Archive(source);assert archive.entries[0]['name'] is None
    result=recover(archive,['wrong_name.iff']);apply(archive,result['identities'])
    assert result['matched_names']==0
    assert archive.entries[0]['name'] is None and archive.entries[0]['hash']==identity
    assert archive.entries[0]['name_hint']=='SCNE: hi_shoe1'
    assert Archive(source).entries[0]['name_hint']=='SCNE: hi_shoe1'
    result=recover(archive,['mystery_model.iff']);apply(archive,result['identities'])
    assert result['matched_names']==1 and archive.entries[0]['name']=='mystery_model.iff'
    assert Archive(source).entries[0]['name']=='mystery_model.iff'
    assert bank.read_bytes()==bytes(raw)


def test_identity_cache_is_invalidated_when_source_changes(tmp_path):
    source=game_fixture(tmp_path/'game',iff_fixture())
    bank=source/'PS3_GAME'/'USRDIR'/'0A';raw=bytearray(bank.read_bytes())
    identity=hash_name('custom_unnamed.iff');struct.pack_into('>I',raw,40,identity);bank.write_bytes(raw)
    archive=Archive(source);result=recover(archive,['custom_unnamed.iff']);apply(archive,result['identities'])
    assert Archive(source).entries[0]['name']=='custom_unnamed.iff'
    import os
    stat=bank.stat();os.utime(bank,ns=(stat.st_atime_ns,stat.st_mtime_ns+1_000_000))
    assert Archive(source).entries[0]['name'] is None
