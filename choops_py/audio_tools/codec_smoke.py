"""Synthetic WAV round-trip check for the frozen Windows audio helpers."""
import math
import struct
import tempfile
from pathlib import Path

from ..archive.manifests import OUTPUT
from .codec import encode_wav, encoder_path, ffmpeg_path


def main():
    if not ffmpeg_path().is_file() or not encoder_path().is_file():
        raise SystemExit("Bundled LGPL audio helper is missing")
    temp_root = OUTPUT / "temp"
    temp_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="packaged_audio_smoke_", dir=temp_root) as folder:
        source = Path(folder) / "source.wav"
        pcm = b"".join(
            struct.pack("<f", 1.5 * math.sin(2 * math.pi * 440 * i / 24000))
            for i in range(24000)
        )
        fmt = struct.pack("<HHIIHH", 3, 1, 24000, 24000 * 4, 4, 32)
        body = b"WAVEfmt " + struct.pack("<I", len(fmt)) + fmt
        body += b"data" + struct.pack("<I", len(pcm)) + pcm
        source.write_bytes(b"RIFF" + struct.pack("<I", len(body)) + body)
        encoded, samples = encode_wav(source, 2, 48000)
        if samples != 48000 or not encoded:
            raise SystemExit("Bundled audio helpers failed the WAV round trip")
    print("Bundled LGPL audio helpers passed a synthetic WAV round trip")
    return 0
