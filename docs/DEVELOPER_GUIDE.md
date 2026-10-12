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
requirements-windows-dev.txt is an old environment snapshot; pyproject/setup
are the portable dependency contract.

verify.py excludes real_game/runtime_manual and the optional legacy native
comparison. It runs remaining synthetic/Qt tests, source smoke, fatal-error Ruff
checks and scoped GUI/service mypy. New setup scripts get broader lint. Legacy
style debt is not claimed resolved. CI runs the same runner on Windows/Linux.
Native audio tests skip explicitly if the optional encoder is absent.

CHOOPS_JB selects a private read-only fixture. Do not run verify_game.py --build,
copy a full game for tests, or launch RPCS3. Tiny synthetic archive copy/rollback
tests are permitted. Record absent private fixture checks as skipped.

GUI/CLI share Archive, studio.services, formats, texture_tools, roster model and
audio_tools. Qt workers return signals/data, never manipulate widgets. Writers
reparse output, preserve unknown bytes/bits and reject ambiguous shared ranges.
Generated outputs live under output/ and originals remain immutable.

`tools/rebuild/package_windows.ps1` packages the Windows GUI and audio helpers.
The FFmpeg helper is configured without GPL/nonfree components and uses only the
PCM formats and ATRAC3 decoder needed for WAV/audio operations. Its FFmpeg and
AtracDEnc source archives and applicable notices accompany the package. Confirm
the exact configuration and packaged smoke on Windows; no proprietary converters
or game assets are included. See AUDIO_WORKFLOW.md and the encoder README.
