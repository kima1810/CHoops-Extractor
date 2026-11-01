"""PR30 legacy inputs must retain the v1.16-v1.19 import/build contracts."""
import struct

import pytest

from support import game_fixture, iff_fixture
from test_folder_overrides import named_iff, txtr_header
from choops_py.archive.folder_import import discover, compile_group
from choops_py.archive.hash_names import hash_name
from choops_py.archive.usrdir_reader import Archive
from choops_py.formats.standard_iff import StandardIFF
from choops_py.formats.standard_iff_writer import record_blocks
from choops_py.formats.tool_wrapper import wrap
from choops_py.texture_tools import override_import


@pytest.mark.parametrize('owner', ['ua000', '0'])
@pytest.mark.parametrize('record', ['unif', 'icon_tatoo'])
def test_numeric_and_named_folders_keep_dds_priority(tmp_path, monkeypatch, owner, record):
    canonical = 'icon_tattoo' if record == 'icon_tatoo' else record
    original = named_iff([txtr_header(), b'oldimage'],
        [(0x5c369069, [0, 0])], [(canonical, 'TXTR')])
    source = game_fixture(tmp_path/'source', original)
    root = tmp_path/'overrides'
    folder = root/owner
    folder.mkdir(parents=True)
    raw = folder/(record+'.txtr')
    raw.write_bytes(wrap(1, [txtr_header(), b'rawimage']))
    artwork = folder/'TXTR'/record/'artwork.dds'
    artwork.parent.mkdir(parents=True)
    artwork.write_bytes(b'DDS fixture')
    original_converter = override_import.apply_dds
    def convert(parts, kind, selector, path, job=None, **options):
        if isinstance(path, bytes):
            return original_converter(parts, kind, selector, path, job, **options)
        assert parts[1] == b'oldimage' and kind == 'TXTR'
        assert selector == canonical and path == artwork
        return [parts[0], b'DDS wins'], dict(width=4, height=4, format='DXT1', mip_count=1)
    monkeypatch.setattr(override_import, 'apply_dds', convert)
    archive = Archive(source)
    group, = discover(archive, root)['groups']
    assert group['name'] == 'ua000.iff'
    assert list(group['records']) == [(canonical, 'TXTR')]
    rebuilt, _ = compile_group(archive, group)
    iff = StandardIFF(rebuilt)
    assert record_blocks(iff, iff.records[0])[1][3].startswith(b'DDS wins')
    assert raw.read_bytes() == wrap(1, [txtr_header(), b'rawimage'])
    assert artwork.read_bytes() == b'DDS fixture'
    assert archive.read(archive.entries[0]).startswith(original)


def test_numeric_folder_accepts_complete_iff_with_exported_name(tmp_path):
    source = game_fixture(tmp_path/'source', iff_fixture([b'original'], [(0xa7701f00, [0])]))
    root = tmp_path/'overrides'
    folder = root/'0'
    folder.mkdir(parents=True)
    changed = iff_fixture([b'replacement'], [(0xa7701f00, [0])])
    (folder/'exported.iff').write_bytes(changed)
    archive = Archive(source)
    group, = discover(archive, root)['groups']
    assert group['name'] == 'ua000.iff'
    assert compile_group(archive, group)[0] == changed


@pytest.mark.parametrize('owner', ['1', 'nested/0'])
def test_numeric_folders_outside_source_or_root_are_rejected(tmp_path, owner):
    source = game_fixture(tmp_path/'source', iff_fixture())
    root = tmp_path/'overrides'
    folder = root/owner
    folder.mkdir(parents=True)
    (folder/'exported.iff').write_bytes(iff_fixture())
    with pytest.raises(ValueError, match='Unknown archive filename'):
        discover(Archive(source), root)


@pytest.mark.parametrize('method', ['append', 'repack'])
def test_raw_audio_replacement_preserves_bytes_and_source(tmp_path, method):
    from choops_py.archive import add_assets, repack
    source = game_fixture(tmp_path/'source', b'original opaque bank')
    bank = source/'PS3_GAME/USRDIR/0A'
    original = bytearray(bank.read_bytes())
    struct.pack_into('>I', original, 40, hash_name('cribmusic.bin'))
    original[100:108] = b'OPAQUE!!'
    bank.write_bytes(original)
    # Trailing nonzero bytes must survive without IFF interpretation/trimming.
    replacement = b'new audio'*500 + b'\0\0TAIL'
    overrides = tmp_path/'overrides'
    overrides.mkdir()
    (overrides/'cribmusic.bin').write_bytes(replacement)
    archive = Archive(source)
    group, = discover(archive, overrides)['groups']
    assert compile_group(archive, group)[0] == replacement
    output = tmp_path/'manual-output'
    builder = add_assets if method == 'append' else repack
    report = builder.build(source, {}, output, {'cribmusic.bin': replacement})
    rebuilt = Archive(output)
    entry = rebuilt.entries[0]
    assert entry['content_size'] == len(replacement)
    stored = rebuilt.read(entry)
    assert stored[:len(replacement)] == replacement
    assert not any(stored[len(replacement):])
    assert (output/'PS3_GAME/USRDIR/0A').read_bytes()[100:108] == b'OPAQUE!!'
    assert bank.read_bytes() == original
    assert report['source_unchanged']
    with pytest.raises(ValueError):
        builder.plan(source, {'new_audio.bin': replacement})
