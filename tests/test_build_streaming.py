"""Rebuild verification covers bank boundaries, padding, rollback and extra files."""
import json
import shutil
from contextlib import ExitStack
from types import SimpleNamespace

import pytest

from support import game_fixture, iff_fixture
from choops_py.archive import build_copy, add_assets, repack
from choops_py.archive.build_io import BankReader, BankWriter, verify_body
from choops_py.archive.manifests import digest
from choops_py.archive.usrdir_reader import Archive


def test_bank_reader_reuses_handles_and_spans_split_boundaries(tmp_path):
    for name, data in [('0A', b'abc'), ('0B', b'defg')]:
        (tmp_path/name).write_bytes(data)
    archive = SimpleNamespace(path=tmp_path, parts=[dict(name='0A', size=3), dict(name='0B', size=4)])
    with ExitStack() as stack:
        reader = BankReader(archive, stack)
        assert reader.read(1, 5) == b'bcdef'
        handles = dict(reader.streams)
        assert reader.read(0, 7) == b'abcdefg'
        assert reader.streams == handles
        with pytest.raises(ValueError, match='outside'):
            reader.read(6, 2)
    assert all(stream.closed for stream in handles.values())


def test_preservation_verifies_padding_and_merges_overlapping_exclusions(tmp_path):
    src = game_fixture(tmp_path/'source', iff_fixture())
    dst = tmp_path/'copy'
    shutil.copytree(src, dst)
    left, right = Archive(src), Archive(dst)
    path = dst/'PS3_GAME/USRDIR/0A'
    raw = bytearray(path.read_bytes());raw[3000] = 7;path.write_bytes(raw)
    with pytest.raises(ValueError, match='body differs'):
        verify_body(left, right)
    assert verify_body(left, right, [(2999, 2), (3000, 2)]) == 2045
    with pytest.raises(ValueError, match='exclusion'):
        verify_body(left, right, [(0, 1)])


@pytest.mark.parametrize('builder', [add_assets.build, repack.build])
@pytest.mark.parametrize('corruption', ['padding', 'ancillary'])
def test_growing_build_detects_corruption_and_cleans_pending(tmp_path, monkeypatch, builder, corruption):
    source = game_fixture(tmp_path/'source', iff_fixture())
    original_copy = shutil.copytree
    def corrupt(src, dst, *args, **kwargs):
        result = original_copy(src, dst, *args, **kwargs)
        # Called after the recursive copy completes, before bank writes.
        if src == source:
            if corruption == 'ancillary':
                (dst/'PS3_DISC.SFB').write_bytes(b'bad metadata!')
            elif builder is add_assets.build:
                bank = dst/'PS3_GAME/USRDIR/0A'
                raw = bytearray(bank.read_bytes());raw[3000] = 9;bank.write_bytes(raw)
        return result
    monkeypatch.setattr(shutil, 'copytree', corrupt)
    if corruption == 'padding' and builder is repack.build:
        # Repack writes banks after copytree. Inject immediately before verification.
        real_verify = repack.verify_body
        def damage(left, right, **kwargs):
            path = right.path/'0A'
            raw = bytearray(path.read_bytes());raw[3000] ^= 1;path.write_bytes(raw)
            return real_verify(left, right, **kwargs)
        monkeypatch.setattr(repack, 'verify_body', damage)
    with pytest.raises(ValueError, match='differs|resized'):
        builder(source, {'uy777.iff': iff_fixture()}, tmp_path/'result')
    assert not (tmp_path/'result').exists()
    assert not list(tmp_path.glob('.asset_build_*'))
    assert not list(tmp_path.glob('.archive_repack_*'))


def test_preflight_checks_source_once_and_rejects_changed_fingerprint(tmp_path, monkeypatch):
    source = game_fixture(tmp_path/'source', iff_fixture())
    archive = Archive(source);entry = archive.entries[0]
    original = archive.read(entry)
    mod = tmp_path/'mod';mod.mkdir()
    (mod/'asset.iff').write_bytes(original)
    row = dict(archive='ua000.iff', subfile=None, kind='archive', path='asset.iff',
               sha256=digest(original), size=len(original))
    (mod/'overrides.json').write_text(json.dumps([row]), encoding='utf8')
    expected = dict(index=0, hash=entry['hash'], sha256=digest(original))
    conditions = mod/'source_preconditions.json'
    conditions.write_text(json.dumps(dict(schema=1, entries=[expected])), encoding='utf8')
    real_read = Archive.read;reads = []
    def read(self, item):
        reads.append(item['index']);return real_read(self, item)
    monkeypatch.setattr(Archive, 'read', read)
    build_copy.preflight(source, mod)
    assert reads == [0]
    expected['sha256'] = '0'*64
    conditions.write_text(json.dumps(dict(schema=1, entries=[expected])), encoding='utf8')
    with pytest.raises(ValueError, match='changed'):
        build_copy.preflight(source, mod)


def test_stream_verification_cancellation_closes_files(tmp_path):
    source = game_fixture(tmp_path/'source', iff_fixture())
    archive = Archive(source)
    def cancel():
        raise InterruptedError('cancelled')
    with pytest.raises(InterruptedError):
        verify_body(archive, archive, job=SimpleNamespace(check=cancel))
    path = archive.path/'0A'
    path.rename(path.with_name('closed'))


def test_bank_writer_spans_banks_and_flushes_before_verification(tmp_path):
    for name in ('0A', '0B'):
        (tmp_path/name).write_bytes(b'xxxx')
    with ExitStack() as stack:
        writer = BankWriter(tmp_path, ['0A', '0B'], [4, 4], stack)
        writer.write(2, b'abcdef')
        writer.write(0, b'12')
        assert len(writer.streams) == 2
        with pytest.raises(ValueError, match='Incomplete'):
            writer.write(8, b'!')
    assert (tmp_path/'0A').read_bytes() == b'12ab'
    assert (tmp_path/'0B').read_bytes() == b'cdef'


@pytest.mark.parametrize('fail', [False, True])
def test_dds_preflight_removes_owned_temporary_folder(tmp_path, monkeypatch, fail):
    source = game_fixture(tmp_path/'source', iff_fixture())
    original = Archive(source).read(Archive(source).entries[0])
    mod = tmp_path/'mod';mod.mkdir();(mod/'input.dds').write_bytes(b'artwork')
    output = tmp_path/'output';(output/'temp').mkdir(parents=True)
    monkeypatch.setattr(build_copy, 'OUTPUT', output)
    monkeypatch.setattr(build_copy, 'validate', lambda _: [dict(
        archive='ua000.iff', kind='dds', subfile='texture', path='input.dds')])
    def container(path):
        if fail:
            raise ValueError('bad DDS')
        return SimpleNamespace(select=lambda _: object(), replacement=lambda *a: original)
    monkeypatch.setattr(build_copy, 'Container', container)
    monkeypatch.setattr(build_copy, 'imported_image', lambda *a: (b'image', {}))
    if fail:
        with pytest.raises(ValueError, match='bad DDS'):
            build_copy.preflight(source, mod)
    else:
        build_copy.preflight(source, mod)
    assert not list((output/'temp').iterdir())


def test_cli_manual_build_output_uses_builder_policy_without_relaxing_exports(tmp_path, monkeypatch):
    from choops_py.cli import main
    source = game_fixture(tmp_path/'source', iff_fixture())
    mod = tmp_path/'mod';mod.mkdir()
    (mod/'overrides.json').write_text('[]', encoding='utf8')
    output = tmp_path/'chosen-drive'/'build'
    assert main(['build-copy', str(source), str(mod), str(output)]) == 0
    assert (output/'build_manifest.json').is_file()
    # General-purpose exports still retain their project output restriction.
    assert main(['inspect-iff', str(source/'PS3_GAME/USRDIR/0A'), str(tmp_path/'export')]) == 1
