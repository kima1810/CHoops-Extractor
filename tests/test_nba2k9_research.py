"""Synthetic evidence for the NBA 2K9 TOC variant; no private game inputs."""
import json
import struct

import pytest

from support import iff_fixture, pair_fixture
from choops_py.archive.hash_names import hash_name
from choops_py.archive.usrdir_reader import Archive
from choops_py.research.nba2k9 import NBA2K9Archive, extract, resource_kind


def nba_fixture(path, contents):
    usr = path/'PS3_GAME/USRDIR';usr.mkdir(parents=True)
    body = bytearray(8192)
    struct.pack_into('>6I', body, 0, 0xaa00b3bf, 2048, 2, 0, len(contents), 0)
    for i, name in enumerate(('0A', '0B')):
        struct.pack_into('>II8s', body, 24+i*16, 2, 0, (name+'\0\0').encode('utf-16-be'))
    for i, (name, data, sector) in enumerate(contents):
        struct.pack_into('>QII', body, 56+i*16, len(data), hash_name(name), sector)
        body[sector*2048:sector*2048+len(data)] = data
    (usr/'0A').write_bytes(body[:4096]);(usr/'0B').write_bytes(body[4096:])
    return path


def test_nba_size_hash_offset_layout_and_cross_bank_reads(tmp_path):
    data = iff_fixture([b'payload'*400])
    source = nba_fixture(tmp_path/'source', [('ua000.iff', data, 1)])
    arc = NBA2K9Archive(source)
    entry = arc.select('ua000.iff')
    assert arc.read(entry) == data
    assert b''.join(arc.chunks(entry, 17)) == data
    assert arc.select('index:0') == arc.select('hash:'+hex(hash_name('ua000.iff')))
    assert Archive(source).toc_layout == 'size64-hash-offset'


@pytest.mark.parametrize('damage', ['size', 'offset', 'duplicate', 'bank'])
def test_nba_rejects_bad_toc_and_bank_bounds(tmp_path, damage):
    source = nba_fixture(tmp_path/'source', [('ua000.iff', b'one', 1), ('uh000.iff', b'two', 2)])
    bank = source/'PS3_GAME/USRDIR/0A'
    raw = bytearray(bank.read_bytes())
    if damage == 'size':struct.pack_into('>Q', raw, 56, 100000)
    elif damage == 'offset':struct.pack_into('>I', raw, 68, 0)
    elif damage == 'duplicate':struct.pack_into('>I', raw, 80, hash_name('ua000.iff'))
    else:struct.pack_into('>I', raw, 24, 3)
    bank.write_bytes(raw)
    with pytest.raises(ValueError):NBA2K9Archive(source)


def test_nba_resource_signatures_do_not_mislabel_compressed_gpu_data_as_iff():
    assert resource_kind(bytes.fromhex('ff3bef94')) == 'standard_iff'
    assert resource_kind(bytes.fromhex('f0985030')) == 'cdf_metadata'
    assert resource_kind(bytes.fromhex('010e4837c3')) == 'flagged_h7a_resource'
    assert resource_kind(bytes.fromhex('0e4837c3')) == 'h7a_prefixed_resource'
    assert resource_kind(b'raw graphics') == 'other_resource'


def test_nba_extracts_exact_payload_and_cdf_partner_with_researched_name(tmp_path, monkeypatch):
    from choops_py.research import nba2k9
    meta, payload = pair_fixture()
    source = nba_fixture(tmp_path/'source', [('x.iff', meta, 1), ('x.cdf', payload, 2)])
    monkeypatch.setattr(nba2k9, 'safe_output', lambda p, _: p)
    output = tmp_path/'export'
    before = (source/'PS3_GAME/USRDIR/0A').read_bytes()
    report = extract(source, output, ['x.iff'])
    assert report['source_inventory_unchanged']
    assert (output/'x.iff').read_bytes() == meta
    assert (output/'x.cdf').read_bytes() == payload
    assert len(json.loads((output/'inventory.json').read_text(encoding='utf8'))['extracted']) == 2
    assert (source/'PS3_GAME/USRDIR/0A').read_bytes() == before
    with pytest.raises(ValueError, match='new NBA'):extract(source, output)


def test_nba_failed_selection_rolls_back_scratch_output(tmp_path, monkeypatch):
    from choops_py.research import nba2k9
    source = nba_fixture(tmp_path/'source', [('ua000.iff', iff_fixture(), 1)])
    monkeypatch.setattr(nba2k9, 'safe_output', lambda p, _: p)
    with pytest.raises(ValueError, match='unique'):
        extract(source, tmp_path/'out', ['missing.iff'])
    assert not (tmp_path/'out').exists()
    assert not list(tmp_path.glob('.nba2k9_extract_*'))
