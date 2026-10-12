# Experimental audio workflow

Batch WAV export publishes its output folder only after all selected tracks and
the manifest succeed. Cancellation/failure removes the owned temporary batch;
existing destinations and unrelated files remain untouched. Scene/shoe preview
actions navigate to Models/Courts by name even with Audio present.

The Qt studio includes an **Audio** workspace with separate Licensed Music and
Fight Songs tabs. It reads the catalog from the selected JB, exports selected
tracks or a full section to WAV, and prepares archive replacements from one WAV
or a previously exported/edited manifest folder. Select one track to export or
replace its mapped shared cover artwork. All output is written under `output/`
for manual staging. Users build their JB themselves.

Song title/artist changes and EBOOT writes are unavailable. Unknown AUDO loop
formats and general CDF audio growth remain blocked. The GUI and commands use
the same Python backend; no emulator or gameplay check is part of these flows.

Launch the studio with `python -m choops_py.studio`, then choose **Audio** in the
left navigation. Open a JB from Explorer first, then use **Load / refresh
catalog**. WAV export needs the LGPL FFmpeg helper. WAV replacement also needs
the LGPL ATRAC3 encoder helper.

From a checkout or the release's **audio-workspace** directory:

```powershell
python tools/dev/setup.py
.\.venv\Scripts\python.exe -m choops_py.cli --help
```

Python 3.12 x64 and Git must already be available. Setup installs the desktop
and development dependencies. On Windows, install MSYS2 with its MINGW64 toolchain,
`make`, `git` and `pkgconf`, then run `bash tools/audio_codec/build_ffmpeg.sh`
from an MSYS2 MINGW64 shell at the repository root. This builds FFmpeg 9.0.2
from pinned upstream source with GPL/nonfree components disabled. Build the
separate ATRAC3 encoder with `python tools/dev/setup.py --audio-encoder`; this
fetches pinned LGPL AtracDEnc source and builds the helper with Zig. WAV export
needs FFmpeg; WAV replacement needs both helpers.

```powershell
.\.venv\Scripts\python.exe -m choops_py.cli audio-catalog "YOUR_JB_ROOT" output/reports/audio.json
.\.venv\Scripts\python.exe -m choops_py.cli export-soundtrack "YOUR_JB_ROOT" output/rips/licensed
.\.venv\Scripts\python.exe -m choops_py.cli export-soundtrack "YOUR_JB_ROOT" output/rips/fight_songs --category fight-songs
.\.venv\Scripts\python.exe -m choops_py.cli replace-song "YOUR_JB_ROOT" cribmusic 0 "MY_EDIT.wav" output/audio/song_edit
.\.venv\Scripts\python.exe -m choops_py.cli import-audio-folder "YOUR_JB_ROOT" output/rips/licensed output/audio/batch_edit
.\.venv\Scripts\python.exe -m choops_py.cli export-audo "RIPPED_SOUND.audo.block0" output/audio/sound.wav
.\.venv\Scripts\python.exe -m choops_py.cli replace-audo "RIPPED_SOUND.audo" "MY_EDIT.wav" output/audio/replaced.audo
.\.venv\Scripts\python.exe -m choops_py.cli export-jukebox-art "YOUR_JB_ROOT" 000 output/audio/cover.dds
.\.venv\Scripts\python.exe -m choops_py.cli replace-jukebox-art "YOUR_JB_ROOT" 000 "MY_COVER.png" output/audio/jukebox.iff
```

Choose a new output name/folder each time. Export defaults to 23 licensed tracks;
fight songs are a separate batch. WAVs are PCM16 at the source bank rate/channels.
Import resamples and ATRAC3-encodes compatible WAVs. Finite floating-point PCM
samples through ±4.0 are accepted by the encoder's 1/4 input scaling; higher
peaks and non-finite samples are rejected. Song replacements are automatically
trimmed to the selected track's catalog sample length; shorter sources are
silence-padded to that same length. Maximum source duration is 30 minutes.
Manifests hold bank/index and original WAV checksums; unchanged files are skipped.
Changing manifest title/artist text does not rename game songs. No changed WAVs
means no replacement folder is created.

Song replacement outputs global.iff and affected .bin files, preserving other
streams and ordering. Stage that folder and manually build your JB when ready.
Standalone AUDO output is a raw/wrapped asset copy, not a complete replacement of
its parent IFF/CDF. Do not stage it as a complete archive. Unknown looped AUDO
replacement and general CDF audio growth remain blocked/pending.

Cover replacement outputs complete jukebox.iff for manual staging. Record 021 is
shared by all fight songs; 002 by both Strange Fruit tracks. DDS or Pillow-readable
artwork such as PNG is normalized to the selected JB's base texture layout.

The Windows standalone GUI includes the restricted LGPL FFmpeg and ATRAC3 helper
executables. Their exact source archives, license texts and build instructions
are distributed in `THIRD-PARTY-SOURCES`. The default PyAV wheel is not bundled.
When building locally, both helpers must be present before running
`tools/rebuild/package_windows.ps1`. See AUDIO_RESEARCH.md for evidence and
format limits.
