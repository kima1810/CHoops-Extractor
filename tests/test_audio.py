"""Synthetic audio layout preservation and optional native codec checks."""
import math
from pathlib import Path
import struct
import tempfile
import wave

import pytest

from choops_py.archive.manifests import OUTPUT
from choops_py.audio_tools.banks import StreamBank
from choops_py.audio_tools.codec import atrac_riff, encode_wav, encoder_path, ffmpeg_path, playback_samples
from choops_py.audio_tools.workflow import names, read_audo
from choops_py.formats import audio
from choops_py.formats.tool_wrapper import wrap

pytestmark = pytest.mark.unit


def metadata(sizes):
    head = bytearray(88 + (len(sizes) + 1) * 8 + 12)
    name = 'cribmusic.bin'.encode('utf-16-be')
    head[:len(name)] = name
    struct.pack_into('>7I', head, 64, len(sizes), 123, 1, 48000, 8192, 15, 0)
    offset = 8
    for i, size in enumerate(sizes):
        struct.pack_into('>If', head, 92 + i * 8, offset, 1.0)
        offset += size
    struct.pack_into('>I', head, 92 + len(sizes) * 8, offset)
    head[-12:] = b'KEEP_PADDING'
    return bytes(head)


def audo():
    payload = b'\xa0' * (304 * 5)
    head = struct.pack('>9I', 1, 5, 15, 3072, 48000, 0, len(payload), 0, 0)
    return [head, payload + b'TAIL']


def test_bank_replacement_preserves_neighbors_unknowns_and_tail():
    streams = [bytes([i + 1]) * (304 * 5) for i in range(3)]
    data = b'PREFIX!!' + b''.join(streams) + b'BANKTAIL'
    original = metadata(list(map(len, streams)))
    bank = StreamBank(original, len(data))
    changed = b'\x99' * (304 * 7)
    head, rebuilt = bank.replace(data, {1: (changed, 4000)})
    parsed = StreamBank(head, len(rebuilt))
    assert rebuilt[:8] == data[:8] and rebuilt[-8:] == b'BANKTAIL'
    assert head[:88] == original[:88] and head[-12:] == original[-12:]
    assert rebuilt[parsed.offsets[0]:parsed.offsets[1]] == streams[0]
    assert rebuilt[parsed.offsets[1]:parsed.offsets[2]] == changed
    assert rebuilt[parsed.offsets[2]:parsed.offsets[3]] == streams[2]
    assert parsed.info(1)['samples'] == 4000
    assert parsed.offsets[2] - bank.offsets[2] == len(changed) - len(streams[1])


@pytest.mark.parametrize('encoded,samples', [(b'', 1), (b'x' * 303, 1), (b'x' * 304, 1), (b'x' * 1520, 99999), (b'x' * 1520, 0)])
def test_bank_rejects_invalid_encoded_extents(encoded, samples):
    bank = StreamBank(metadata([1520]), 1536)
    with pytest.raises(ValueError):
        bank.replace(b'P' * 1536, {0: (encoded, samples)})


def test_bank_rejects_unordered_and_out_of_bounds_offsets():
    head = bytearray(metadata([1520, 1520]))
    struct.pack_into('>I', head, 100, 4)
    with pytest.raises(ValueError):
        StreamBank(head, 4000)
    with pytest.raises(ValueError):
        StreamBank(metadata([1520]), 20)


def test_audo_flat_inline_and_split_replacement_preserve_unknown_tail():
    parts = audo()
    assert audio.info(parts)['samples'] == 3072
    assert audio.info([b''.join(parts)]) == audio.info(parts)
    encoded = b'\xa1' * (304 * 7)
    result = audio.replace(parts, encoded, 4000)
    assert result[1] == encoded + b'TAIL'
    assert result[0][:12] == parts[0][:12]
    assert result[0][16:24] == parts[0][16:24]
    assert audio.info(result)['samples'] == 4000
    assert audio.replace([b''.join(parts)], encoded, 4000) == [b''.join(result)]
    with pytest.raises(ValueError):
        audio.replace(parts, encoded, 99999)


@pytest.mark.parametrize('offset', [20, 28, 32])
def test_unconfirmed_loop_fields_block_replacement(offset):
    parts = audo()
    head = bytearray(parts[0])
    struct.pack_into('>I', head, offset, 1)
    assert audio.info([head, parts[1]])['codec'] == 'ATRAC3'
    with pytest.raises(ValueError, match='Looped'):
        audio.replace([head, parts[1]], parts[1][:-4], 3072)


def test_ripped_audo_pair_and_wrapper(tmp_path):
    parts = audo()
    header = tmp_path / 'sample.audo.block0'
    header.write_bytes(parts[0])
    with pytest.raises(ValueError, match='missing'):
        read_audo(header)
    header.with_suffix('.block1').write_bytes(parts[1])
    assert read_audo(header)[0] == parts
    wrapped = tmp_path / 'sample.audo'
    wrapped.write_bytes(wrap(7, parts))
    assert read_audo(wrapped) == (parts, 7)


def test_frame_extent_and_stale_sample_metadata():
    assert playback_samples(304 * 10, 2, 48000) == 8192
    assert playback_samples(304 * 10, 2, 48000, 4000) == 4000
    assert playback_samples(304 * 10, 2, 48000, 99999) == 8192
    with pytest.raises(ValueError):
        atrac_riff(b'x' * 303, 2, 48000)


def test_replacement_rejects_non_wav_before_codec_lookup(tmp_path):
    source = tmp_path / 'not-audio.bin'
    source.write_bytes(b'not a wav file')
    with pytest.raises(ValueError, match='RIFF or RF64 WAV'):
        encode_wav(source, 2, 48000)


def test_catalog_counts_and_shared_artwork():
    catalog = names()
    assert len(catalog) == 87
    assert sum(r['category'] == 'Soundtrack' for r in catalog.values()) == 23
    assert sum(r['category'] == 'Fight song' for r in catalog.values()) == 64
    assert catalog[2]['cover_record'] == catalog[77]['cover_record'] == '002'
    assert catalog[10]['cover_record'] == '021'
    assert catalog[86]['cover_record'] == '022'


def test_native_wav_roundtrip_resamples_and_keeps_input():
    try:
        encoder_path()
        ffmpeg_path()
    except ValueError:
        pytest.skip('Optional LGPL audio helpers have not been built')
    parent = OUTPUT / 'temp'
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='audio_test_', dir=parent) as folder:
        path = Path(folder) / 'tone.wav'
        pcm = b''.join(struct.pack('<h', round(9000 * math.sin(2 * math.pi * 440 * i / 24000))) for i in range(24000))
        with wave.open(str(path), 'wb') as target:
            target.setnchannels(1)
            target.setsampwidth(2)
            target.setframerate(24000)
            target.writeframes(pcm)
        original = path.read_bytes()
        encoded, samples = encode_wav(path, 2, 48000)
        assert samples == 48000 and len(encoded) % 304 == 0
        assert playback_samples(len(encoded), 2, 48000) >= samples
        trimmed, trimmed_samples = encode_wav(path, 2, 48000, target_samples=24000)
        assert trimmed_samples == 24000
        assert playback_samples(len(trimmed), 2, 48000) >= trimmed_samples
        padded, padded_samples = encode_wav(path, 2, 48000, target_samples=60000)
        assert padded_samples == 60000
        assert playback_samples(len(padded), 2, 48000) >= padded_samples
        assert path.read_bytes() == original
