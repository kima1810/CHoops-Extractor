# Development

Read AGENTS.md, CURRENT_STATUS.md, SECONDARY_CODEX_PROMPT.md and COLLABORATION.md.
Upstream is ZMO34/CHoops-Extractor-Reborn; use documented feature PRs to master.
Python 3.11+ supported; Python 3.12 x64 is the CI/Windows baseline. Git is required.

```powershell
python tools/dev/setup.py
python tools/dev/setup.py --check
python tools/dev/setup.py --audio-encoder
python tools/dev/verify.py
.\.venv\Scripts\python.exe -m choops_py.studio
.\.venv\Scripts\python.exe -m pytest tests/test_audio.py tests/test_cli.py -q
```

Setup installs .[dev]; the encoder option installs Zig 0.13.0 and fetches pinned
LGPL sources. Audio conversion uses the restricted LGPL FFmpeg helper built from
`tools/audio_codec/build_ffmpeg.sh` and the optional ATRAC3 encoder. No PyAV
wheel is required or packaged. No other PC's credentials, environment or paths
are copied. Versions go into ignored dev-setup.txt.
pyproject.toml and tools/dev/setup.py are the portable dependency contract.
The obsolete pinned Windows environment snapshot has been removed.

verify.py excludes real_game/runtime_manual and the optional legacy native
comparison. It runs remaining synthetic/Qt tests, source smoke, fatal-error Ruff
checks and scoped GUI/service mypy. New setup scripts get broader lint. Legacy
style debt is not claimed resolved. CI runs the same checks on Windows/Linux and native Apple Silicon/Intel macOS.
Native audio tests skip explicitly if the optional encoder is absent.

CHOOPS_JB selects a private read-only fixture. Do not run verify_game.py --build,
copy a full game for tests, or launch RPCS3. Tiny synthetic archive copy/rollback
tests are permitted. Record absent private fixture checks as skipped.

GUI/CLI share Archive, studio.services, formats, texture_tools, roster model and
audio_tools. Qt workers return signals/data, never manipulate widgets. Writers
reparse output, preserve unknown bytes/bits and reject ambiguous shared ranges.
Prepared overrides/exports live under output/ and originals remain immutable.
Completed JB builds also support user-selected destinations through
archive.manifests.build_destination; keep safe_output for other workflows.
Destination validation must protect source/mod trees in both directions. Build
reports and temporary/backup folders use the same validated destination drive.

`tools/rebuild/package_windows.ps1` packages the Windows GUI and audio helpers.
The FFmpeg helper is configured without GPL/nonfree components and uses only the
PCM formats and ATRAC3 decoder needed for WAV/audio operations. Its FFmpeg and
AtracDEnc source archives and applicable notices accompany the package. Confirm
the exact configuration and packaged smoke on Windows; no proprietary converters
or game assets are included. See AUDIO_WORKFLOW.md and the encoder README.


## Rebuild I/O (v1.16)

`archive.build_io` verifies preserved source-coordinate spans against their output
coordinates, with a relocation delta when needed. In-place replacement ranges
alone are excluded; old bytes left by relocated replacements and all padding are
still compared. Each bank is opened once per comparison, and ExitStack closes all
handles on cancellation/error. Repack BankWriter closes/flushed handles before
reopening output for validation. Replacement/header verification stays separate.
Copied non-bank files also receive byte comparisons before atomic publication.
Do not cache verification of a fresh output or use hard links to source files.

Use `python tools/dev/benchmark_rebuild.py` for a bounded synthetic-only benchmark.
Its entry count can be changed with `--entries`; it never accepts a game path.


## Automatic shared 2K layouts

`archive.layouts.decode_toc` validates all candidate schemas, requires a unique
answer and exposes canonical row fields to the existing reader/writers.
`pack_row` serializes canonical fields back to the source schema. Do not make
writers infer a game from names, extensions or UI settings. Source size semantics
remain profile-specific: legacy rounded/derived extents versus exact size64 extents.
Keep unknown formats raw and preserve their bytes through builds.

Record CRC labels are case-sensitive and only fill missing labels; authored
trailers take precedence. A matching label does not establish unknown type or
roster semantics. Cache fingerprints include the schema and frozen prepared-cache
fingerprints include layout/label module code. Add malformed/ambiguous fixtures,
synthetic writer round trips and explicit read-only input evidence for another
variant. Never validate by launching an emulator or building a real/testing JB.
See PS3_2K_ARCHIVES.md for current evidence and the standalone research command.

## NBA roster and SDAT extension

Runtime dependency PyCryptodome is declared in pyproject.toml and installed by
tools/dev/setup.py. archive/sdat.py is a bounded read-only stream; Archive opens
plain/encrypted banks through open_part, and BankReader uses the same abstraction.
Bank descriptor sizes 16/72 are structurally selected, not inferred from a title.
All JB writer plans reject encrypted/extended-descriptor archives before output.

EditorModel.open dispatches NBA payloads to roster/nba.py; studio/nba_roster.py
provides separate NBA side panels. Keep unknown NBA offsets out of the College
Hoops schema and vice versa. The source-bound JSON patch backend and wrapper
writers are shared. College-only bulk/research paths reject NBA explicitly.
formats/compression.py handles bounded ZLIB alongside H7A; StandardIFF reads its
record table through +0x1C. Extra IFF metadata remains read-only. New vertex, draw
and instance layouts must uniquely validate; ambiguous geometry is not guessed.
See NBA_ROSTERS_AND_2K14.md and ANIMATION_PORTABILITY.md for reproducible evidence,
limitations and the read-only animation survey command. Neither animation ports
nor SDAT rebuild/signature writers are enabled.

Mac packaging uses `tools/rebuild/package_macos.py`; see [release procedure](RELEASING.md).
