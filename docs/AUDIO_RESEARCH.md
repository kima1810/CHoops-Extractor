# Audio format evidence and development boundaries

Updated 2026-10-11; initial source commit e556e36. This is backend research, not a
claim of complete GUI or gameplay support. EBOOT is read-only evidence.

## Where the soundtrack is stored

The stock JB has split USRDIR archive banks rather than loose song files.
`jukebox.iff` contains UI, artwork TXTR records 000–022, layouts/scenes and
`artist_bio_english` STRG; it is not the soundtrack stream container.
`global.iff` owns AUSB metadata (type hash **61DF2234**) for cribmusic, femusic,
drillmusic, hlmusic, loadm and other speech/crowd banks. Stream filenames in those
records resolve through uppercase ASCII CRC32 (`replacement_hash`).

cribmusic.bin is 126275584 bytes on the inspected stock input; this is a research
observation, not a universal file-size requirement. It has 87 streams: licensed
music indices 0–9 and 74–86, fight songs 10–73. All 87 name/artist/category/artwork
mappings are in `choops_py/audio_tools/soundtrack_names.json`. The same raw bank
may be unnamed in old rips; hashes remain the canonical archive identity.

## AUSB metadata (big endian)

| Offset | Meaning |
| --- | --- |
| 0–63 | UTF-16BE bank filename and padding |
| 64 | u32 stream count |
| 68, 72 | Preserved words; observed 72 = 1 |
| 76 | u32 sample rate; observed 48000 |
| 80 | Preserved buffer parameter; observed 8192 |
| 84 | 14 mono / 15 stereo |
| 88 | float default/first stream duration |
| 92 + 8*i | u32 cumulative boundary, i = 0..count |
| 96 + 8*i | float duration, i = 0..count-1 |

Track i is raw bank `[boundary[i]:boundary[i+1]]`. Metadata used extent is
`88 + (count+1)*8`. Preserve padding, unknown words, raw bank prefix/tail and all
unchanged streams. Stream count, ordering and identity remain unchanged during
replacement. The experimental writer reparses and compares each stream.

## AUDO header and encoding

AUDO (1AEDDA1F) has a 36-byte big-endian header and raw ATRAC3 payload. Rips may
have `.audo.block0` + `.block1`, flat header+payload, or a 2kTl wrapper.

| Offset | Current interpretation |
| --- | --- |
| 0 | Observed version 1 |
| 4 | Codec 5: ATRAC3 mid-rate |
| 8 | 14 mono / 15 stereo |
| 12 | Stored sample count; sometimes stale after resampling |
| 16 | Sample rate |
| 20 | Unconfirmed flags; preserve |
| 24 | Encoded payload byte count |
| 28, 32 | Potential loop fields; not fully traced |

Frames are 152 bytes per channel, 1024 samples. Stock music durations match
physical decoded length minus **2048 priming samples**. Some AUDO/femusic/drill
values appear to retain pre-resampling lengths; do not truncate valid decoded
audio to arbitrary stale metadata. `playback_samples` uses a plausible stored
count only within 8192 samples of physical extent. This is a documented heuristic
that needs regression coverage, not a complete semantic derivation.

The raw float frontend uses AtracDEnc's non-joint-stereo 304-byte output frames;
mono takes one duplicated channel. Encoder priming is 1162 samples, so Python
prepends 886 zeros before encoding for the game's 2048-sample skip. The backend
independently decodes encoded output. Packet/DMA alignment (often 608-byte stock
chunks), exact loop behavior, long audio and cancellation still need validation.
Nonzero AUDO flag/loop words currently block replacement; export remains possible.
CDF AUDO banks exist, but a fully validated growing CDF audio writer is pending.

## Jukebox artwork and names

Artwork 000–020 maps to the first 21 artist groups, **021 is College Fight Songs**,
and **022 is Joe Blaq**. Strange Fruit tracks 2 and 77 share artwork 002; all fight
songs share 021. Use the catalog mapping rather than assuming stream index equals
artwork index. Artwork replacement preserves base texture layout.

EBOOT's constructor at 0x1A27A4..0x1A6500 constructs 36-byte song descriptors:
stream index, title pointer/key, artist key, bio pointer/key, bank key,
duration-display pointer/key. Title/artist keys match uppercase ASCII CRC32 | 1.
English.iff has TXTL type A423B39E with a sorted key table and self-relative
UTF-16LE string pointers. The inspected payload has 21637 keys; root +4 is count,
+8 points relatively to the table at 32. `artist_bio_english` maps bio-token keys
and English group key to localized biography keys.

This does **not** establish that editing English.iff overrides English song titles
at runtime. Defaults are executable strings and getter routing is unresolved.
Do not implement title/artist changes through EBOOT. Keep fields read-only until
an archive-only path is demonstrated. No proprietary biographies or executable
bytes are published here. Private helper scripts and EBOOT copies are not portable
project dependencies.

## Open-source codec provenance

- [FFmpeg ATRAC3 decoder](https://github.com/FFmpeg/FFmpeg/blob/master/libavcodec/atrac3.c): frame sizes, RIFF tag 0270, extradata and sync behavior.
- [vgmstream Sony MSF reader](https://github.com/vgmstream/vgmstream/blob/master/src/meta/msf.c): codec 5/mid-rate observations and encoder delay reference.
- [AtracDEnc](https://github.com/dcherednik/atracdenc), revision
  `cb170709f836cb43dc0312455188c791159d81dc`, LGPL-2.1-or-later. Thin frontend and
  build instructions are in tools/audio_encoder. No Sony SDK executable is used.
- The standalone app's LGPL packaging uses FFmpeg 9.0.2 at revision
  `946fcce07b6dcd0331c8cc609192aeff5e1924f8` (the peeled commit of the annotated
  `n9.0.2` tag), built as a separate CLI with GPL,
  nonfree and autodetected components disabled. Only the PCM formats, WAV/RF64
  demuxer, raw PCM muxers, ATRAC3 decoder, audio resampling/format filters and
  file/pipe protocols used by the workflow are enabled. The exact build script
  and corresponding FFmpeg source archive ship beside the app.
- Do not bundle the default PyAV Windows wheel for this project: the PyAV FFmpeg
  build configuration enables x264/x265, which enables FFmpeg's GPL options.
  See [PyAV's FFmpeg build](https://github.com/PyAV-Org/pyav-ffmpeg/blob/master/scripts/build-ffmpeg.py)
  and [the PyAV wheel licensing discussion](https://github.com/PyAV-Org/PyAV/issues/2270).
  The package instead uses separately executable FFmpeg built from the official
  [FFmpeg source](https://github.com/FFmpeg/FFmpeg) with a pinned revision and
  corresponding source archive.
- Exact-head Windows CI run 54 built the pinned FFmpeg and ATRAC3 helpers,
  packaged/smoke-tested the GUI, and passed the frozen synthetic WAV round trip
  on `e149790005fdaeb14d0a1b79689d0a3de3b8f2da`. The script checks the LGPL-only
  build configuration and required audio components; source archives and license
  files are packaged beside the app. This is branch verification, not a published
  release claim.

See CURRENT_STATUS.md and each PR's exact verification for the latest evidence.
