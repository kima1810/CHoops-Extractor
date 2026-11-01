> Historical record, captured before v1.18. Not a current support contract.
> See ../CURRENT_STATUS.md and ../TEST_REPORT.md. Relative links below retain their original context.

# Unreleased — split-header and override diagnostics regressions

Synthetic tests reproduce a valid header prefix crossing 0A into 0B, then check
append and repack replacement outputs, opaque-byte preservation and unchanged
source banks. A 130-entry TOC crossing the first 2 KiB bank is parsed correctly.
Damaged-bank cases test missing header bytes, named bank/size diagnostics and
specific suggested actions. SDAT tests check preview validation can run while the
JB writer remains explicitly blocked. A Qt test verifies archive/selector details
and suggested fixes persist in Mod Builder without losing the original error.
Portable verification of the combined update: 596 passed, 9 offscreen GL skips,
2 deselected; compile, CLI/Qt smoke, Ruff, mypy, handoff and diff passed.
No real/testing game folder was rebuilt.

# Unreleased — NBA extension validation

Synthetic fixtures cover both NBA roster profiles, payload dispatch, masked edits,
shared-string rejection, text growth/unknown-field rejection, undo/redo, patch
rollback and Qt side-panel routing. SDAT tests cover header/block authentication,
truncation, random reads, cache bounds, mixed encrypted/plain split-bank extraction
and early writer rejection. ZLIB tests cover strict lengths and round trips;
extended IFF tables and newer vertex/draw/instance layouts have synthetic fixtures.

Read-only supplied evidence: both stock NBA roster payloads opened without string
issues; player number/height changes encoded into IFF and reopened correctly.
NBA2K9: 1,064 players / 69 teams / 72 arenas; NBA2K14: 1,665 / 105 / 102.
NBA2K14 floor: two meshes/no warnings; arena: 61 meshes, one unsupported UV mesh.
Combined NBA2K14 jersey preview remains unavailable and is not a passed check.
Animation survey: 319 / 904 / 7,460 SingleMoCap records across CH2K8/NBA2K9/NBA2K14.
Portable verification: 589 passed, 9 offscreen OpenGL skips, 2 deselected; compile,
CLI/Qt smoke, Ruff, mypy, generated handoff and diff passed. Final exact-head
verification is also recorded in the PR handoff.
No RPCS3/gameplay, EBOOT edits, animation port or real/testing JB build.

# Unreleased — key/center alignment guides

Portable verification: 577 passed, 9 offscreen OpenGL skips, 2 deselected;
compile, CLI/Qt smoke, Ruff, mypy, handoff and diff checks passed.

Synthetic geometry test checks that routes 2/10/20 are copied from the authored
reference, raised one unit and thinned on the appropriate UV axis, while filled
key paint and actual floor draws remain unchanged. Qt regression checks default-off,
independent enable/disable behavior alongside the existing guide toggles. Read-only
stock S256 inspection confirms the named batches and radial UV direction. No game
assets were committed, and no RPCS3 or real/testing JB was run/built.

# v1.17 — automatic PS3 2K layouts

Focused automatic-layout/research suite: 22 passed. Covers both TOC schemas,
64-bit stored sizes, ambiguous-layout rejection, split-bank extraction, fixed/
growing/repacked NBA synthetic builds, source preservation, CRC record labels,
CDF pairing/TXTR variants, half4 UV/color fields, automatic Qt source loading and
College Hoops roster boundaries. An end-to-end synthetic test selects a DDS
folder, previews its live replacement and rebuilds with the same detected layout.

Read-only supplied NBA 2K9 evidence: 5,624 TOC entries / 6 banks, no overlaps;
selected raw IFF/CDF outputs rehashed; five standard sample IFFs' logical blocks
decoded; five sample DDS exports plus a menu-logo DDS opened successfully.
Shared preview services: jersey/shorts 2 meshes / 2 images; floor 2 meshes / 2
images / no warnings; arena 78 meshes / 58 images / no warnings. These checks
materialize extracted scratch assets only, never a rebuilt game JB. Broader game
compatibility and runtime shader/roster behavior remain unverified.

Full portable verification: 575 passed, 9 offscreen OpenGL skips, 2 deselected;
compile, CLI/Qt smoke, Ruff, mypy, handoff and diff passed. RPCS3/gameplay NOT RUN; real/testing JB NOT BUILT; EBOOT NOT EDITED.

Windows packaging validation: startup and synthetic audio round trip passed.
Frozen CLI passed read-only NBA IFF extraction, fixed/growing/138-bank repack
fixtures for both layouts and a three-worker NBA override import. Both source
layouts retain unchanged synthetic source bytes. No supplied game was rebuilt.

# v1.16 rebuild performance verification

Targeted synthetic rebuild tests: 26 passed, 1 GUI case deselected. Twelve new
regressions cover persistent split-bank reads/writes, bank crossings, overlapping
preservation exclusions, corruption in preserved padding/non-bank files, cleanup,
single-read source fingerprints, cancellation handle release and CLI manual-output
parity without relaxing unrelated exports. Existing append,
relocation, CDF insertion, opaque-header-gap and manual-output regressions pass.

Synthetic verification benchmark (Windows Python 3.12, 8,192 shuffled entries /
32 MiB): 1.5131 s per-entry checks; 0.0477 s sequential checks, 31.69x for this
phase only. 16,384 opens become two. No real game files were used by the benchmark.
Command: `python tools/dev/benchmark_rebuild.py`.

Full portable verification: 553 passed, 9 offscreen OpenGL skips, 2 deselected;
compile, CLI/Qt smoke, Ruff, mypy, handoff and diff checks passed.
Frozen Windows checks run in the release packaging workflow.
RPCS3/gameplay NOT RUN; testing JB NOT BUILT; EBOOT NOT EDITED.

## Queued audio / build destinations / roster and scorebug audit — 2026-10-15

`python tools/dev/verify.py` passed: **541 portable tests**, nine offscreen
OpenGL skips, two deselected real/manual/native-reference checks. Compileall,
CLI help, hidden Qt startup, Ruff, mypy, handoff consistency and diff checks passed.
The PR records the exact tested head. No RPCS3 or real/testing JB folder was built.

New synthetic checks cover two changes in one cribmusic bank plus global.iff,
untouched third stream/prefix/tail/metadata, queue replacement/source binding and
reopen, preservation of newer choices during a save, GUI queue/save callbacks,
external output paths including existing empty folders, source/ancestor rejection,
opaque header-gap preservation in append/repack, occupied TOC rejection, correct
roster +1 anchors/uniform masks/logical windows, and bounded scorebug discovery.

Read-only stock checks: scorebug discovery parsed all twelve identified records
in gamedata/gamedataextra and their SCNE textures/parts. Roster audit found 347
resolved and reciprocal arena-team references, 32 nulls, no unresolved nonnull
arena links and no logical-table overlaps. EBOOT arena indexing and four-pointer
serialization/deserialization corroborate the structure. Remaining unknown bytes
are still reported explicitly; this is not a full semantic or gameplay certification.

# Roster / game-line / animation continuation verification

Portable final runner: **473 passed, 7 skipped, 2 deselected**. Native Windows
targeted checks: **17 passed**, including seven rendered shader paths, keyboard
warnings, exact conference-logo selection and authored line supplementation.
Read-only hidden S256 floor rendering restored two verified line draws with the
original coordinates/UVs and no OpenGL error; source SHA was unchanged. Appearance
and unknown-bit coverage checks passed. No RPCS3, EBOOT changes or testing JB.

Regressions cover UTF-16 supplementary characters, advisory warning reset,
invalid conference index rollback, protected tournament links, exact logo900+
index identity, compressed raw motion span extraction, unchanged arena/apron
geometry and no duplicate supplemental draws. Source/Qt/CLI startup, compile,
Ruff/mypy and generated documentation checks are part of the final runner.

# Combined roster/arena continuation verification

Portable runner: **461 passed, 7 skipped, 2 deselected**. Seven rendered-pixel
checks are skipped only by Qt offscreen; native Windows targeted verification:
**144 passed**, including all seven rendered shader paths. Source/Qt/CLI startup,
compilation, Ruff, mypy and handoff checks passed. Synthetic appearance tests
check shared packed-word neighbours, bounds, readback and undo for all 12 fields.
Read-only S256 hidden rendering: 119 parts, 180 lightmapped batches, no shader
errors. No RPCS3, testing JB or EBOOT edits. Proprietary fixtures stay private.

# Uniform lettering continuation verification

`python tools/dev/verify.py`: **448 passed, 4 skipped, 2 deselected**. Skips
are rendered-pixel GL checks on Qt offscreen. Compilation, CLI/Qt startup,
Ruff, mypy (11 files), handoff and diff checks passed.
Native Windows targeted check: indexed_font, scene_number_gl, scene_preview and
roster_side_panels: **128 passed**. GL tests read actual front/back/name/palette
pixels. All 101 number codes are exercised. Private read-only source inspection
and hidden rendering confirmed authored Reborn above the back number, and front
and back 23. No assets/screenshots enter Git. Inputs remained immutable.
No RPCS3/gameplay, EBOOT editing or full testing JB was performed.

# Development verification

## Roster / preview continuation checks

Final integrated `python tools/dev/verify.py`: 341 passed, 2 intentional
deselections; compile, CLI/Qt startup, lint/type and handoff checks passed.
Final targeted preview/bulk/GUI run: 27 passed. Regressions include reordered
conference references, entire long-string warning preservation, exact menu logo
ownership, game entry capacities and isolated jump-shot writes/undo. No
RPCS3, EBOOT writes or testing JB. Evidence is in ROSTER_SCALE_AND_PREVIEWS.md.
## PR #11 independent integration review — 2026-10-14

Inspected exact original head 81cd1665c26ce8798c025f5bfbd2d20f98cf213f in
an isolated checkout: 15 texture-layout tests passed. Merged v1.12 master into
the branch, resolved the changelog conflict and regenerated the shared handoff.
Added an actual DDS replacement/export check preserving the depth-one descriptor,
header and payload extent, and rejection checks for depth zero, depth two and
volume-plus-cubemap combinations. Integrated portable suite: 329 passed,
1 native-audio skip (helpers absent in this isolated checkout), 2 intentional
deselections. Compile, CLI/Qt startup, lint/type and handoff checks passed.
No RPCS3, gameplay, EBOOT edits or testing JB. Sampler runtime behavior remains
unverified; this change does not generalize to deeper volumes or DDS arrays.

## Roster scale / preview development checkpoint — 2026-10-13

`python tools/dev/verify.py`: 326 passed, 2 intentional deselections. Compile,
CLI help, offscreen Qt startup, scoped Ruff, mypy (11 files), generated handoff
and diff checks passed. The earlier targeted bulk/preview/cache/GUI run passed
13 tests; three subsequent CSV scalar-type regressions passed in the full suite.
Comparison selection survives filtering/sorting; bulk edits preserve one-step
undo, source preconditions and coupled-field rollback. The comparison uses a
table model rather than allocating a widget item for every changed cell.
CSV rejects JSON objects, arrays and booleans in scalar text/numeric fields.
No RPCS3, gameplay, EBOOT writes or testing JB build. Unfinished text-limit and
shader research remains explicitly documented in ROSTER_SCALE_AND_PREVIEWS.md.

## v1.11 side-panel and membership verification

The local source checkpoint passed 310 tests with 2 intentional deselections;
native audio coverage runs using the unchanged verified LGPL helpers. GUI/source
startup, scoped lint/type and generated handoff checks passed. New regressions
cover every category side editor, palette/coach/uniform edits, transfer/count/
row-zero handling, shared/inconsistent refusal, scoped shoe brand propagation,
18-member/full-destination behavior, undo and top/shorts texture-role/coordinate
preservation. No untested alternate-asset actions are restored.

Read-only stock checks validate all 443 school arrays/counts (maximum 18), identify
row-zero ownership, transfer/undo without player-data changes and school-only brand
propagation/undo. Actual combined jersey/shorts decode returns both roles with
separate mapped artwork. Inputs remain unchanged; no emulator, EBOOT write or
testing JB. Exact release SHA and packaged Windows checks are recorded in the PR.

## v1.10 roster usability checks

Portable suite: 296 passed, 1 native-codec skip, 2 deselected at the local
checkpoint. Source startup, scoped lint/type and handoff checks passed. Added
height/position display and numeric-sort checks, scholarship exact-mask/undo
checks, visible Player/Ratings/Scholarship tabs, equipment labels, removed-action
checks and combined Schools view. Updated existing position edit/save/reopen and
realignment interactions. Synthetic Qt visual QA checked the main roster layout;
a toolbar text-encoding issue found during rendering was corrected before release.
Duplicate equipment captions receive distinct variant labels so accepting the
current choice cannot accidentally write a different code; a regression checks this.

Read-only stock/EBOOT tracing confirms single byte positions and scholarship
polarity; the full stock roster contains 5,166 scholarship flags and 519 walk-ons.
No game input modified. Exact source SHA and Windows packaging/codec smoke results
are recorded in the PR/release metadata. No emulator or testing JB.

## Independent conference review — 2026-10-12

Original PR #8 head f38448cadd71eae38e0374517193312fd3367bbd failed the generated
handoff synchronization gate. Regenerated the snapshot and added parameterized
coverage for all 14 conference scalars: exact byte preservation, reopen, validation,
undo and negative/overflow rejection without mutation. The source offset/width
table matches the primary public `conferences.py` definition; labels remain source
labels, not independently verified gameplay semantics. No private inputs required,
emulator/gameplay checks or test JB copies. Final head/results are recorded in PR #8.
Portable checks passed 292 tests, 1 native codec skip, 2 deselected; source startup,
scoped lint/type checks and handoff synchronization passed. The native FFmpeg
helper is unavailable locally, so that skip is explicit rather than a pass.

## Conference historical fields — current branch

The supplied read-only USERDATA file was used to confirm 39 conference rows.
An in-memory model edit changed only the selected `final_fours` field byte;
model validation passed and undo restored the exact original payload. The file
was not modified or added to Git. Windows packaging completed with
`tools/rebuild/package_windows.ps1`; the packaged Qt startup and bundled LGPL
audio round-trip smoke checks passed. Conference gameplay effects are not
independently verified.

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
The DDS importer now treats dimension-3 TXTRs with stored depth one as
single-slice storage and continues to reject deeper volumes. The existing
volume fixture now covers acceptance at depth one and rejection at depth two.
Automated checks were not run for this change; no RPCS3 or gameplay validation
was performed.

## Override-folder selection regression

Python 3.12.14 on Windows: tools/dev/verify.py passed with 464 tests, 7
offscreen GL skips and 2 deselected checks. Compile, CLI/Qt smoke, Ruff, mypy,
handoff and diff checks passed. Targeted override tests: 26 passed. Repeated
selection preserves previous snapshots, skips occupied numbered workspaces,
compiles current artwork, cleans only its failed temporary workspace and updates
GUI build/preview destinations together. No RPCS3 or automatic/testing JB build.
Current continuation: 482 portable tests passed, 9 offscreen GL skips, 2 deselected; 28 native targeted checks passed after them. Guide tests verify flat colour with transparent textures, zero palette tint, glow mode and both automatic/manual texture selection. Runtime BE text tests independently check field+delta-1 and save/reopen/undo. No RPCS3 or JB build.

Combined v1.14 preview release checks: 491 portable tests passed, 9 offscreen OpenGL skips, 2 deselected; 37 native Qt/OpenGL targeted checks passed. Direct jersey launch, captured source/override stadium selection, scene-mode identity and reload behavior are covered. No RPCS3 or JB build.

v1.14.1 preview source/list hotfix: 493 portable tests passed (9 offscreen GL skips, 2 deselected); 17 native direct-preview/GL checks passed. Read-only stock S258 floor preview returned five parts and twelve textures; source hash unchanged. Shared source dropdown and pick-only category lists have regression coverage. No RPCS3 or JB build.

Additional hotfix regression: global source switching preserves the active texture category rather than navigating to a prior 3D view. Final full suite: 494 passed, 9 offscreen GL skips, 2 deselected; nine direct-preview checks passed.

Final v1.14.1 native preview/GL/roster-scale GUI suite: 22 passed. Packaged Windows startup and synthetic audio round-trip passed. Verified v1.13 audio helpers and matching source/licence archives reused.

## v1.15 override-source refresh

Final Windows Python checks: 497 passed, 9 offscreen GL skips, 2 deselected.
Native override/direct-preview/GL checks: 24 passed. Compile, CLI/Qt smoke, Ruff,
mypy, handoff and diff checks passed. Regression covers already-selected override
mode during the worker result callback, queued preview reload, preservation of
JB fallbacks, visible workspace versus stale cached path, and unavailable badges.
Read-only supplied-folder discovery resolved 1,824 archives, including S258;
existing workspace had 1,825 replacements. Native GUI list verification showed
354 stadium and 727 uniform overrides. No shoe packages were supplied. Names and
contents of user inputs were unchanged. No RPCS3 or automatic/testing JB build.

## Final v1.15 Explorer/cache/CSV verification

515 portable tests passed (9 offscreen GL skips, 2 deselected), with compile,
CLI/Qt smoke, Ruff, mypy and handoff checks. Native targeted suite: 41 passed.
Hidden Explorer loaded the supplied SELUH258 override, showed five records and
full roster references, and rendered its texture without errors. Read-only
S258/SELUH258/UH258 override inspection and DDS preview decoding also passed.
Cache tests retain both source variants, invalidate modified inputs, reject
altered replacement payloads and enforce the image-memory bound. DDS tests skip
a broken raw TXTR when DDS exists and correctly use TXTR when DDS is absent.
CSV tests exclude injected UI metadata and reject unsupported import fields
without changing roster bytes. No RPCS3, game launch or automatic/testing JB.

## v1.15 explicit roster I/O and release verification

`python tools/dev/verify.py`: 519 passed, 9 offscreen OpenGL skips,
2 deselected; compile, CLI/Qt smoke, Ruff, mypy and generated handoff passed.
New regressions cover edited external IFF to USERDATA/IFF round trips, immutable
source payloads, invalid-roster rejection, explicit JB/override source selection,
missing override roster rejection and IFF export without a loaded JB.
Native Windows targeted preview, cache, CSV and roster I/O suite: 45 passed.
Windows packaging additionally runs frozen startup and synthetic audio round trip.
No emulator/gameplay tests or automatic/testing JB builds are performed.

## v1.15.1 preview resizing

18 native direct-preview/OpenGL regressions passed. Hidden Windows Qt resize
check confirmed a 1,364-pixel-wide viewport and dragging the divider changed its
height from 255 to 120 pixels without hiding controls. Qt startup, Ruff and
diff checks passed. No RPCS3 or testing JB.

Full `python tools/dev/verify.py`: 519 passed, 9 offscreen GL skips,
2 deselected; compile, CLI/Qt startup, Ruff, mypy, handoff and diff checks passed.

## v1.15.2 live preview reproduction

Read-only S258 reproduction found a prepared snapshot's old floor image while
current loose inputs compiled the Dayton court. The actual live PreviewArchive
and stadium path now decoded that current 1024 x 512 preview with two floor mesh
parts; unchanged materialization reused its cache. Source inputs were untouched.
Synthetic regression verifies stale snapshot replacement, loose file edits,
cache invalidation, source immutability and missing-file rejection. No JB build.

Final portable suite: 520 passed, 9 offscreen GL skips, 2 deselected.
Native source/preview/OpenGL suite: 36 passed. Compile, CLI/Qt smoke, Ruff,
mypy, generated handoff and diff checks passed. Windows package startup/audio
smoke runs before publication.

## v1.15.3 frontend import reproduction

Read-only frontend_sync import reproduced the false texture/geometry overlap.
Header-relative streams had flag 0x40000002, pointer 5, valid header vertex floats
and header-relative 16-bit indices (flag 0x10). GPU menu streams use 0x40000003
and index flag 0x20000010. The fix imported frontend_sync successfully in memory.
Synthetic tests preserve both inline vertex streams and indices through image
packing, preserve GPU menu relocation, and reject real overlaps, invalid ranges
and changed inline geometry. No RPCS3 or automatic/testing JB build.

`python tools/dev/verify.py`: 523 passed, 9 offscreen GL skips, 2 deselected.
Compile, CLI/Qt smoke, Ruff, mypy, handoff and diff checks passed.

The broader check passed 13 of 14 non-stadium scene groups and exposed a second
studio cubemap mismatch. Added a guarded legacy first-face import: regression
checks retain the original descriptor and five other DDS faces exactly, with
strict rejection retained for direct imports without this legacy policy.

Final complete suite: 524 passed, 9 offscreen GL skips, 2 deselected;
51 targeted import/packing/live-preview checks passed. Actual studio import
completed with +X updated and five source faces preserved.

Final read-only supplied-input run: all 14 non-stadium SCNE groups compiled
successfully together, zero failures. Legacy cube handling is isolated in its
own module so unchanged ordinary conversions retain their cache identities.
The final portable verification command passed all 524 tests again.

## Parallel override preparation

Windows spawn tests compare deterministic manifests and archive bytes between
serial and two-worker preparation. Tests cover CPU/RAM limits, unchanged reuse,
changed-input invalidation, tampered cached output, worker failure/cancellation
and child cleanup, plus source/frozen module fingerprinting.

Read-only benchmark: 14 actual scene groups / 612 DDS inputs, warm conversion
cache, final run: serial 24.838 s, six workers 10.008 s, unchanged repeat
6.676 s (2.48x parallel speedup). An earlier run measured 3.08x.
All output archive checksums matched. Benchmark scratch was removed.
No RPCS3 or real JB build.

Frozen Windows EXE: three synthetic DDS overrides prepared with three spawned
workers, then all three completed archives reused on repeat. Distinct texture
outputs and source-bound manifests verified; owned smoke fixtures removed.
Packaged Qt startup and synthetic audio round-trip also passed.

Final `python tools/dev/verify.py`: 530 passed, 9 offscreen GL skips,
2 deselected. Compile, CLI/Qt smoke, Ruff, mypy, handoff and diff checks passed.
Final frozen EXE test repeated successfully with three workers and three reused
archives; startup/audio smoke passed.
