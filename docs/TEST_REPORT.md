# Development verification

## LGPL audio packaging branch — verified PR head

Follow-up native reproduction: stereo IEEE-float WAV audio with peaks at ±1.5
encodes after raising the ATRAC frontend's finite-sample ceiling to ±4.0, aligned
with AtracDEnc's internal 1/4 scaling. Direct helper checks accepted ±4.0 and
rejected ±4.01 and NaN. `pytest tests/test_audio.py tests/test_cli.py -q`: 18 passed;
native round trips verify replacement trim to 24,000 samples and silence padding
to 60,000 at 48 kHz. `python -m compileall -q choops_py/audio_tools tests/test_audio.py`,
handoff generation, and `git diff --check` passed. The rebuilt frozen app passed
the Qt startup smoke and over-range float WAV encode/decode round trip.

Exact-head CI run 54 passed on `e149790005fdaeb14d0a1b79689d0a3de3b8f2da` on
both Ubuntu and Windows. The Windows job built the pinned LGPL FFmpeg helper and
ATRAC3 encoder, built/smoke-tested the standalone package, and printed
`Bundled LGPL audio helpers passed a synthetic WAV round trip` from the frozen
executable. Thus the packaged helper lookup, WAV resampling/encoding and ATRAC3
decode validation ran in the actual frozen app.

Local `python tools/dev/verify.py` on the previous PR head: 250 passed, 1 skipped,
2 deselected. The one skip was the native helper round trip; the two deselections
were private game/runtime checks and the optional legacy native comparison. CLI
help, Qt startup smoke, scoped Ruff, studio/service mypy, handoff snapshot,
compileall and `git diff --check` passed. The suite includes a regression that
rejects a non-RIFF/RF64 replacement before codec lookup.

Earlier Windows runs exposed and fixed an annotated-tag SHA mismatch, FFmpeg
component names/make target, a missing MSYS2 `cmp`, and the absence of conversion
filters. The final verified helper pins the peeled `n9.0.2` source commit, enables
only LGPL `aresample`/`aformat` conversion filters, and checks required codecs,
formats and filters. No emulator or testing JB was run/built. PR #6 was merged;
this follow-up is tracked in its own PR and does not create a release.

## Independent PR #5 review and continuation — 2026-10-12

Reviewed submitted head 6603d24f4d32f70abfd25e3f6770939b86f4594b in an isolated
checkout: 239 passed, 1 skipped (encoder absent), 1 failed (legacy converter
presence), 2 deselected. Reproduction tests separately showed both scene and shoe
previews opened Audio instead of Models/Courts. Navigation now uses page names;
discovery tests use synthetic files instead of excluded proprietary executables.

Continuation makes batch WAV export transactional. Regressions cover successful
publication, decode failure, cancellation, destination preservation, final sidecar
paths, shared fight-song artwork and cancelled GUI output selection. The unchanged
pinned-source encoder was enabled for an actual native WAV round trip. No emulator,
EBOOT writes or full testing JB. Final exact-head results are recorded in the PR.

The final portable continuation run passed 250 tests, 2 deselected; actual native
WAV encoding ran rather than skipping. Source GUI/CLI smoke, scoped Ruff and mypy
passed. The handoff snapshot check passed. No private game fixture was required.

## Audio workspace update — 2026-10-11

Python 3.12 x64 setup check and pinned LGPL ATRAC3 helper build completed.
Audio/CLI tests: `pytest tests/test_audio.py tests/test_cli.py -q` — 17 passed.
Qt navigation and audio-category tests: 2 passed. Full portable suite excluding
the two documented private/optional checks and the legacy converter-presence
assertion: 240 passed, 3 deselected. CLI help, Qt startup smoke, scoped Ruff and
studio/service mypy checks passed. A read-only scan of the available Vanilla JB
catalog returned 23 licensed tracks and 64 fight songs; no audio or artwork was
exported and no source was modified.

The exact `tools/dev/verify.py` run on this audio GUI head reported 240 passed,
1 failed and 2 deselected before stopping at the pre-existing
`test_bundled_paths_have_precedence` assertion. It expects the historical
`tools/gtf2dds.exe`, which is absent from the public clone and excluded from
releases. That single check is outside the audio GUI change; no proprietary
converter was fetched or substituted. The full suite with that assertion
excluded passed. No emulator, gameplay test or JB build was performed.

## Audio/handoff update — 2026-10-11

`python tools/dev/verify.py`: 240 passed, 2 deselected (private game test and
optional historical executable comparison). Source CLI help and Qt smoke passed;
scoped fatal-error Ruff, new setup script lint and GUI/service mypy passed.
`python tools/dev/setup.py --check`: installed desktop/dev dependencies imported.
`python tools/dev/setup.py --audio-encoder`: dependency install and pinned-source
native helper rebuild completed. Windows packaging and startup smoke completed;
packaged CLI help includes audio registrations. Decode/encode uses Python workspace.
`pytest tests/test_audio.py tests/test_cli.py -q`: 17 passed at this checkpoint.
Audio tests cover AUSB neighbor/prefix/tail/unknown preservation, invalid offsets/
encoded sample bounds, flat/split/inline/wrapped AUDO, blocked loop fields, catalog
artwork/category counts and native 24k mono WAV -> 48k stereo ATRAC3 round trip.
Private read-only stock catalog: 23 licensed, 64 fight, 159 total music streams.
No native decoder DLL redistribution, full bank game validation, EBOOT writes,
RPCS3 or testing JB. Exact commit SHAs are recorded in the PR/release metadata.

The full portable run exposed pre-existing invalid four-byte fixtures tagged as
TXTR and an output-safety test expecting a later error. Fixtures now use generic
CDAN where appropriate; normalization rejects truncated texture headers cleanly.
Type annotations were corrected without changing preview/staging behavior.

Historical results below remain separate observations, not current test totals.

The community roster and shoe-editing update passed 135 targeted Python/Qt
checks. Both supplied community ZIPs were loaded, edited for ratings and
player/school shoes, saved and reopened with exact payload round trips. ZIP
members other than USERDATA remained byte-exact, and original input hashes
were unchanged. Both payloads also exported to game roster IFFs and reopened
successfully. Three malformed source name strings in one input remain
unchanged warnings; changing their malformed bytes or introducing a new
invalid pointer remains fatal, including pre-existing out-of-bounds pointers.
All 90 DDS overrides for the frontend bank
compiled in memory. Zero/non-one stored depth in declared 2D textures is
covered separately from rejected volume dimensions. No JB build or emulator
test was performed.

For 2D/cubemap texture storage, the dimension selects the resource type and
effective depth is one; an unused stored depth is not a volume declaration.
The primary reference is [RPCS3's texture layout implementation](https://github.com/RPCS3/rpcs3/blob/master/rpcs3/Emu/RSX/Common/TextureUtils.cpp),
whose image-section layout uses depth only for the 3D case. The importer now
follows that distinction and includes dimension/cube/depth values in remaining
unsupported-layout errors.

The court-template and non-stadium texture policy update passed 125 targeted
Python checks, including raw and whole-IFF normalization, paired CDF imports,
HDR preservation, multistream geometry relocation, previews, compression and
CLI registration. Real gameplay/uniform replacements were compiled in memory
and retained exact base headers after resizing. The supplied court template
retained its floor triangles and primary UVs, resolved albedo to slot 0 and
bump to slot 2, disabled the other floor draws, and ignored inactive artwork.
The source GUI passed its startup smoke check. No emulator was opened and no
JB build was produced for this update. The optional historical executable
comparison was excluded after Windows rejected its DLL relocation; built-in
conversion checks passed independently. The game's crash-free court texture
budget remains unverified.

Built-in DDS/GTF conversion is tested in both directions against generated
native-reference fixtures for L8, ARGB8, DXT1/3/5 and RGBA16F. Coverage includes
rectangular Morton order, non-power-of-two linear storage, mip chains and all six
cubemap faces. Default import/export and preview tests run without external tools.
The independent accelerated H7A codec and portable decoder agree on random,
overlapping and malformed streams. Override regression tests cover misplaced
scene folders, numeric record aliases, Windows copy suffixes and explicit reports
for DDS files requiring a missing replacement scene.

Local checks exercised the synthetic parser/writer, Qt navigation/edit/save, actual Windows converter, interruption cleanup, source preconditions, malicious ZIP rejection and cross-part copy/patch workflows. Private read-only game integration and separate generated-output verification also ran; environment-specific results are excluded from public documentation.

Commands: pytest, compileall, CLI --help, studio --smoke, studio --verify-game --game PRIVATE_PATH, Ruff and mypy on the new studio/patch-package modules. Test groups distinguish unit, integration, gui, windows and real_game. Public CI must skip the private fixture when absent. Converter tests use generated inputs.

Initial Ubuntu CI exposed missing libEGL.so.1; the workflow installs the required Qt runtime libraries and allows both platforms to complete independently. The corrected prior CI commit passed Windows/Linux and standalone packaging. Subsequent code requires its own observed checks.

Original files were read only; output patch and untouched ranges were verified separately. Runtime PS3/RPCS3 verification: NOT RUN. Unsupported layouts, geometry import/export and unknown roster semantics remain documented limitations. This is not completion or publication of v1.0beta.
