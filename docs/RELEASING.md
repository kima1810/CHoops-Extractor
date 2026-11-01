# Desktop and GitHub release procedure

## Prepare a reviewable source update

1. Fetch canonical master and inspect open PRs, discussions and dependency changes.
   Work on a release branch; integrate only owner-authorized, reviewed changes.
2. Update `choops_py/__init__.py` and `pyproject.toml` to the same version. Maintain
   CURRENT_STATUS, FEATURE_MATRIX, affected user/format docs, CHANGELOG and test
   evidence. Keep unresolved semantics explicit.
3. Run `python tools/dev/handoff.py`, then portable verification. Commit the final
   source and test its exact head in an isolated checkout. Publish a PR with SHA,
   commands/results, skips, risks and next action. Attach it to the active chat.
4. Check Windows/Linux/macOS CI and review threads. Merge only with owner authorization;
   release authorization in a user request can cover that specific release.

## Build Windows x64

Use the repository's Python 3.12 x64 development environment with PySide6,
PyInstaller and declared dependencies, including PyCryptodome for SDAT reads.
`tools/rebuild/package_windows.ps1` builds an onedir bundle, applies the Qt ICU
compatibility check, includes required data and native helpers, and runs startup
and audio round-trip smoke. Build pinned audio helpers using the documented codec
scripts first. A trusted previously released helper may be reused only with its
exact matching corresponding sources/notices and recorded provenance.

Keep `_internal` with the executable. Include current documentation at its original
relative paths so links work, README-START-HERE, BUILD-INFO with source commit,
THIRD-PARTY-SOURCES and applicable notices. Do not bundle private inputs, game
assets, settings, logs, development virtualenvs or proprietary DDS converters.
Source DDS conversion is built in. Exclude unneeded Qt/browser modules and PyAV.

## Validate and publish

- Run the frozen GUI/CLI/audio checks and bounded synthetic format/writer tests.
  No RPCS3 or real/testing JB. Confirm the version and SDAT/other optional imports
  are collected; startup alone does not test a lazy-loaded module.
- ZIP the complete app directory, test ZIP integrity, inspect entries for private
  data, and calculate SHA256SUMS.txt. Record source head, size and digest privately
  and in durable release evidence where appropriate.
- Tag the exact tested source commit (or an identical merged tree with explicit
  provenance). Create a draft release with honest features, limitations, commands
  and counts. Upload all native desktop ZIPs/checksums; verify uploaded size/digest.
- Publish only after source, CI, package and license gates pass. Link merged PRs
  and release in handoff comments. Both instances maintain this procedure.

Do not regenerate a package from an uncommitted tree or label a parser-only result
as gameplay certification. Preserve published releases unless a specific owner
request calls for removal. Cleanup local intermediates after successful publication;
keep the delivered package/checksum and avoid deleting user builds/research.

## Build macOS (Apple Silicon and Intel)

Build on the matching native macOS runner with Python 3.12, Xcode command-line
build tools and `MACOSX_DEPLOYMENT_TARGET=13.0`. Install the declared development
dependencies, run `bash tools/audio_codec/build_ffmpeg.sh`, then
`python tools/dev/setup.py --audio-encoder`. The encoder uses Apple's clang on Mac.
Run `.venv/bin/python tools/rebuild/package_macos.py`. Each architecture runs full
portable checks, frozen startup/CLI/audio checks and a native Cocoa/OpenGL render.
The app is ad-hoc signed and verified, not Developer ID signed or notarized.
Never describe this as an Apple-notarized release. Exact codec sources and docs
are beside the app so copying documentation cannot invalidate its signature.

Run `tools/rebuild/release_archive.py` with the native packaging interpreter on
Windows or Mac. It records source commit/platform/version, verifies ZIP CRC and
writes a per-ZIP SHA-256 file. Mac archives use ditto to preserve framework links
and executable permissions. CI uploads the complete ZIP and checksum together.
Download all three successful native job artifacts for the same tested commit;
inspect checksums/contents before uploading release assets. Do not publish only a
workflow or a source ZIP as a completed desktop release.
