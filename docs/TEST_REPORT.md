# v1.23 desktop release validation

Local source and isolated exact-head verification: **967 passed,10 skipped,
2 deselected**, plus compile/CLI/Qt/Ruff/mypy/handoff/diff. The synthetic native
OpenGL triangle check also passed on Windows.

Added regression coverage for frozen Mac output paths and preserved source/Windows
paths. Portable and native package results, exact commit and skipped checks are
recorded in the release PR. macOS jobs require frozen audio conversion and a
real Cocoa/OpenGL framebuffer; startup alone is insufficient. No emulator,
gameplay or testing JB is used.

# v1.22 alternate discovery and PR integration

Targeted: `python -m pytest tests/test_team_assets.py tests/test_folder_overrides.py
tests/test_parallel_overrides.py tests/test_output_path_spelling.py -q -o addopts=`:
**59 passed**. New regressions
cover manifest-free roster-enabled SELU additions with raw/DDS input in serial and
spawned workers, exact virtual metadata byte ranges, unchanged new container
retention, build-time partner fallback, synthetic final TOC and source preservation.
Unlinked alternate names are rejected with a corrective message. A bounded stress
reproduction traced the prior intermittent worker failure to Windows returning a
resolved path with a Win32 extended prefix. Normalization now retains source and
output-root guards; drive and UNC spelling regressions pass. No original game
or override writes, RPCS3/gameplay or testing JB. Earlier combined source verification: **963 passed, 10 optional skips, 2 deselected**;
compile, CLI/offscreen Qt, Ruff, mypy, handoff and diff checks pass. Exact-head
isolated, CI and packaged verification results are recorded in the release PR.

# Unreleased donor header / allocation protocol follow-up

Twelve-file targeted animation suite: 160 passed. New synthetic cases cover target
header layout, exact resampled component data, preserved timing bits, fingerprint-
bound authoring assertions, missing/opaque metadata/events/auxiliary dependencies,
budget rejection before expansion, huge-input/float-conversion guards, exact aligned
budget acceptance, relocation
roundtrip, allocation failure, write/readback rollback, concurrent reader retirement,
shutdown, overlap quarantine, uncertain-free no-retry, callback reentry, and heap
generation/rebinding fences during allocation, readback, leasing and release.

The shareable revision-guarded Ghidra instruction harness passes four native-wrapper
cases: inherited/alternate heap policy, null allocation and release. It traps a
synthetic heap callback and checks arguments plus TOC restoration; actual heap
allocation/free, native publication/readers and gameplay are not exercised.

Read-only actual signature-bank audit: 918 resolved nonempty slots including 458
aliases, 911 referenced headers / 456 resolved payloads / zero dependency or alias
metadata-count errors. Known component projection is 12,307,462 bytes excluding
auxiliary/opaque payloads, alignment, registration, heap overhead and existing CH
assets. All 806 bounded selector curves pass, totaling 35,852 bytes; their cross-
game meanings remain unresolved. No real-game metadata contract or donor shot is
certified. Original sources remain unchanged. RPCS3/hardware/gameplay NOT RUN;
automatic/testing JB NOT BUILT. Full portable/exact-head results are in PR45.

# Unreleased target header residency follow-up

Nine-file animation regression suite: 123 passed. New cases cover complete later
track extents/BSS rejection, metadata retention, shared dependency storage, source
immutability, exact relocation/inverse at different bases, wrong declared pointer
state, malformed metadata, missing sentinel, output budget, unknown auxiliary
extents and header overlap. Allocation tests cover image reservation after TLS,
physical padding and a virtual collision despite free file padding. Deep
registration checks reject a header that passes shallow mask checks but lacks
valid counts/tracks. Source portable verification: 832 passed, 9 optional skips, 2 deselected; compile,
CLI/offscreen Qt startup, Ruff, mypy, handoff and diff checks pass. Exact-head
isolated results are recorded in PR45.

Private read-only corpus: 7,055 inspected target headers, zero errors; all 2,522
supported headers pass owned-image preparation/relocation/inverse byte equality.
Largest image: 126,996 bytes. All 224 distinct headers from 112 stock shot rows
pass full dependency extents. Separate stock-backed resident probe: 113 rows,
112 original rows preserved, 4,656-byte image, 9,648-byte total allocation within
14,848 available padding bytes, no borrowed motion pointers, exact diff allowlist
and reparse pass. Original source hashes unchanged. No donor header is derived,
no native heap/demand loader is installed, and no gameplay compatibility is claimed.
No emulator, hardware, automatic/testing JB or release build was run.

# Unreleased runtime adapter follow-up

Targeted command: `python -m pytest tests/test_motion_sampling.py
 tests/test_donor_registry.py tests/test_motion_events.py tests/test_motion_bind.py
 tests/test_shot_registration.py tests/test_motion_frames.py
 tests/test_embedded_motion.py tests/test_motion_envelope.py -q -o addopts=`:
108 passed. Full source portable verification: 817 passed, 9 optional skips,
2 deselected; exact-head isolated verification is recorded in the PR handoff.

New tests compare every integer tick of a nontrivial pose/root fixture against
full expansion, exercise cache eviction and stale/closed input rejection, and
reject later-key BSS overlap, inconsistent duration and unsupported unpacked mode.
Registry fixtures cover category bounds, typed cross-bank identity, ambiguity,
nonzero runtime pointers, unknown selection kinds and output-input protection.
Event regression compares the four native cache timing fields and rejects a
convenient but incorrect global ID decrement.

Private read-only audit: 28,722 samples / 9,574 unique streams / zero errors;
peak retained payload 65,536 bytes under the 65,536-byte budget. Seven explicit
event rules accept 3,616 tables (including empty), with 2,337 actual converted
rows; 5,958 tables remain blocked. Registry: 988 entries / 31 categories /
2,478 uniquely resolved nonempty references / 320 empty slots, with no missing
or ambiguous identities. This does not establish full group payload semantics.
Source analysis ELF hashes remain unchanged. No emulator, hardware, native hook,
full runtime memory test or automatic/testing JB was run. No playable port claimed.

# Unreleased canonical bind / registration phase

Targeted animation regression suite:66 passed. Source portable verification:
781 passed,9 optional skips,2 deselected before the final unpacked-mode guard; compile,CLI/Qt smoke,Ruff,mypy,
handoff and diff checks passed. Exact committed-head verification is recorded
in the PR handoff. Tests cover bind mismatch rejection, mask/count agreement, all five observed
translation counts, decoded-pose equivalence, padding/reverse-byte preservation,
changed native consumers/ranges, TLS-safe zero-padding planning, mirror-selector
parity and opaque-payload refusal after consumer inspection.

Private read-only corpus:7,055 CH and18,831 NBA11 headers pass canonical-channel
validation.9,574 NBA11 pose streams/341,823 keys/49,278,288 bytes pass conversion
and exact reverse checks; no component-preparation errors. Of9,574 event tables,
2,674 use only the verified subset (including empty tables),6,900 remain blocked.
Traced payload reads pass for151 event90,1117 event92,71 event93,47 event94,
1260 event173,23 event178 and187 event186 rows; no extent errors.

The authorized separate registration-only decoded ELF reparses at113 entries,
preserves112 original records, TLS and adjacent label pointers, and passes an
exact diff allowlist. This is structural evidence only, not runtime registration.
Source hashes are unchanged. No game assets/binaries/reports are tracked or
published; no RPCS3, hardware or automatic/testing JB was used.
# Native-only continuity and Legacy diagnostics — 2026-10-21

Targeted: `python -m pytest tests/test_legacy_recruiting_gui.py
tests/test_recruit_pool.py tests/test_transfer_portal.py tests/test_cli.py
tests/test_legacy_save_adapter.py -q -o addopts=`: **94 passed**. Six new Qt cases
cover immutable data/history, metadata/preferences, filtering, unknown profile and
malformed-table handling, changed/closed-source callbacks, editor entry and view
invalidation. No transfer/sign/save actions exist in the diagnostic view. An initial
sandboxed run hit three temporary-directory setup permission errors (91 passed);
the rerun with normal temporary-directory access passed all 94. Focused Ruff and
module mypy pass.

Private read-only Ghidra continuation establishes annual regeneration, native
commitment, player-to-recruit copying/class mismatch and reusable-player-pool
operations. Eight callsites, five tail branches and the 2,500-entry pool bound
independently match raw PowerPC. Original ELF digest and byte equality pass.
No executable patch, native portal, historical-stat/team-link writer or in-game
continuity validation is claimed. RPCS3/gameplay NOT RUN; testing JB NOT BUILT.
Full source portable verification: **847 passed, 10 optional skips, 2 deselected**;
compile, CLI/offscreen Qt startup, Ruff, mypy, handoff and diff checks pass.
Exact-head isolated portable results are recorded in PR46.

# Native recruiting pool and persistence continuation — 2026-10-21

Targeted: `python -m pytest tests/test_recruit_pool.py tests/test_transfer_portal.py
tests/test_cli.py tests/test_legacy_save_adapter.py -q -o addopts=`: **88 passed**.
New module/tests pass focused Ruff/import formatting and module mypy. Source
read-only CLI audit verifies all 2,000 reserved stock recruit records (432,000 bytes)
are blank and explicitly does not certify slot reuse. Private source/digest checks
pass; native constant getters independently match section size 0x415A4 and aggregate
relative offset 0x11418. Ghidra/raw instruction traces establish list ownership,
serializers and destructive-to-new-object recruit conversion. No original writes.
Exact-head isolated portable results are recorded in the PR handoff. No offseason
save supplied, save roundtrip/gameplay/emulator NOT RUN, testing JB NOT BUILT.

# Transfer recruiting policy follow-up — 2026-10-21

Synthetic targeted suite: `python -m pytest tests/test_transfer_portal.py -q -o
addopts=`: **42 passed**. Covers all college class/RS labels, rejection of HS/unknown
classes and transfer-status-as-RS, stable/order-independent priorities, framed
identities, rejection sampling, three distinct preference winners, capacity/source/
eligibility filters, duplicate identities and malformed/nonfinite metrics.
All 96 reconstructed profiles match an independent native-loop-order audit and
source float32 weights; source digest and byte equality remain unchanged. Invalid
uninitialized profile indices are rejected. Focused Ruff format/check and module
mypy passed. Native read-only follow-up confirms HS/JC label
codes, separate recruit class/preference fields, localization captions, geography,
position-depth and recruit-rank consumers. No game execution or native record writes.
Exact-head isolated portable results are recorded in the PR handoff.

# Legacy transfer feasibility research — 2026-10-21

Documentation-only update. Read-only Ghidra generated 17 focused function reports;
PowerPC instructions and constants independently checked. Private audit passes
source digest/byte equality, the chance subtraction instruction, 3.0/0.66 constants,
eight state-gate cases and 0x12CC = 401 x 12 arithmetic. Static evidence only:
no game execution, measured transfer distribution, save roundtrip, modified EBOOT
or JB. No editor runtime behavior changes, so runtime suites are not rerun.
Documentation/handoff/diff validation is recorded in the PR handoff.

# v1.21 animation event bridge

Targeted animation suite:
`python -m pytest tests/test_motion_events.py tests/test_motion_envelope.py tests/test_embedded_motion.py tests/test_motion_frames.py -q`:
49 passed. Full development portable verification:758 passed,9 optional skips,
2 deselected; compile,CLI/Qt smoke,Ruff,mypy,handoff and diff checks passed.
The release is also checked from its exact committed head in an isolated checkout.

New regressions cover signed relative versus native absolute payloads, file-backed
extent/BSS rejection, missing sentinel/truncation, nonfinite times, required event90
payload, opaque payload refusal, missing/duplicate contract rules, exact float-bit
and duplicate-order preservation, zero-valued payload categories, bounded auxiliary
pairs, all-validation-before-write and input/contract overwrite protection.

Read-only supplied-copy audit using the new parser:3,727 CH tables/17,897 events;
9,574 NBA11 tables/49,639 events; no malformed tables. All identified tables have
nondecreasing finite times.101 NBA11 auxiliary tables/101 pairs pass;151 event90
payload-word reads and2,850 other opaque payload rows are distinguished. Original
analysis-copy hashes remain unchanged. No game/executable bytes are distributed,
no emulator ran and no real/testing JB was built. Semantic mappings are explicitly
caller-supplied research assertions, not automatically validated gameplay behavior.

# Team asset checkbox defaults

Targeted Qt/backend suite: `python -m pytest tests/test_team_assets.py -q`:
22 passed. Regression coverage includes per-asset peer names for different
arena rows/uniform owners sharing the same files, original target ID defaults,
available stadium/Home/Away/menu defaults,
missing SELU pairs, inactive alternates, no changes for an untouched matrix,
new-category-only plans, independent copies by button or manual ID, unselected
team preservation and resetting pending intent on reload. Source inputs remain
unchanged; no emulator or full JB build was run.
Full portable verification:735 passed,9 optional skips,2 deselected. Compile,
CLI/Qt smoke, Ruff, mypy, generated handoff and diff checks passed.
The sandbox-limited first full run was interrupted; the complete run with
required temporary-file/Qt settings access passed.

# Applied-roster synchronization regression

Applying asset expansion also updates an open community roster as one undoable
edit, preserving pending player changes. A regression checks that later saves
retain the new arena/uniform routing and Undo restores the pre-expansion roster.

# Community roster assignment integration

Four additional synthetic tests cover selected-team activation/stadium copying,
shared-owner isolation, mismatched Team ID refusal, destination player/conference
preservation, editor undo/redo after table movement, and saving community player
edits to the selected overrides roster. Targeted combined suite:21 passed. Final isolated portable verification after this
integration:728 passed,10 skipped,2 deselected; CLI/Qt,Ruff,mypy,handoff and
diff checks passed.
No original/community roster is overwritten; no gameplay or real JB build.

# Team asset manager verification

Targeted synthetic suite:17 passed on Windows/Python3.12.14, including shared-owner
isolation, all-five ordering, batch arena rebasing, classic shared-stadium forks,
invalid plans/source preservation, serial/two-worker preparation, preview/build
insertion, CDF logo cloning/live preview, build-time Home fallback and Qt checks.
Read-only supplied JB inspection:443 teams /553 entirely unused IDs. One full
seven-category plan passes override and build preflight:11 new IFFs,3 replacement
containers,6 Home fallback notices. No actual JB built and no emulator run.
Final combined portable and isolated exact-head verification:724 passed,10
skipped,2 deselected each. Compile,CLI/Qt smoke,Ruff,mypy,handoff and diff checks
passed. Read-only bulk plan:435 teams /2,434 new assets /2,205 active uniform rows
in15.95 seconds. Windows bundle validation is recorded in the release notes.

# Scorebug popup inspection

Synthetic ELF tests cover table bounds, OPD alignment, executable mappings, TOC
validation, priority independent of provider count and CLI source protection.
Targeted suite: 11 passed. Supplied decoded executable: 83 types /119 providers.
No RPCS3, executable writes or JB builds. Full release verification follows.
# Uniform runtime distance correction

Targeted synthetic verification: 22 cases pass across uniform OBJ/IFF reimport
and packed cloth distances, including an end-to-end solver-distance regression,
authored bend prestrain, self-edge padding, no-op byte identity, out-of-bounds
indices, overlapping/truncated tables and unrepresentable edited distances.
Private supplied-source checks cover all 21 replacement archives /33 paired
SCNE-Clth records. Native record-name CRCs match the model selector tables.
GUI override preparation and build preflight pass all21 archives, including ten
larger compressed replacements using the existing bank relocation path. No JB
was built. In-game fit and the remote developer's installed files are unverified.
Full source portable verification passes: **696 passed,10 skipped,2 deselected**,
plus compile/CLI/Qt/Ruff/mypy/handoff/diff checks. Focused E/F/I lint passes.
Private package checks validate79,005 changed distance words across33 record
pairs;45 selective packages retain unrelated records. All21 build-preflight
payload fingerprints match their replacements. The installed-bank verifier also
correctly identifies all21 unchanged source archives as ORIGINAL, tolerating
allocation padding without confusing it with a changed garment payload.
Exact-head isolated verification is posted in the PR.

# Native packed-pose translation

Fifteen targeted synthetic cases pass, including adaptive timing/SLERP, quaternion
encoding,6/8-byte roots, endpoint preservation and multi-output source guards: all four native permutation selectors,
channel equivalence and reverse byte identity, signed translation scale, partial
group padding, invalid profiles/counts/extents/quaternions and CLI source guards.
Full E/F/I lint passes the new codec/tests. Full source portable verification: **689 passed,10 skipped,2 deselected**, plus
compile/CLI/Qt/Ruff/mypy/handoff/diff checks. Exact-head isolated verification is
posted in the active PR.

Private checks:32 CH streams (1,106 frames,18,802 quaternion channels,159,264 bytes)
and32 NBA11 streams (644 frames,10,948 quaternion channels,92,736 bytes) preserve
decoded channels and round-trip every byte. Source analysis copies remain unchanged.
The broad observed-family audit passes3,727 CH streams /247,373 frames and9,574
NBA11 streams /341,823 frames with exact reverse bytes; all9,574 distinct donor
timelines match rate/time-scale/duration. Resampling32 pose streams preserves644
keys across4,642 fixed frames;33 root streams preserve keys across4,757 samples.
Ghidra/native instructions establish frame layout, quaternion selector difference
and the112-entry CH jump-shot table. No complete bank conversion, bone retargeting,
new shot registration, control remap, native runtime or gameplay check is implied.
RPCS3 NOT RUN; automatic/testing JB NOT BUILT. No EBOOT writes.

# Executable-held motion inspection follow-up

Targeted synthetic motion/envelope checks: **11 passed**. New parser fixtures
cover absolute mapping for both profiles, source preservation, unbacked-memory
reporting, invalid targets, machine/profile rejection and overlapping load ranges.
Full E/F/I lint passes the new parser/tests. Source portable verification passes
**674 passed, 10 skipped, 2 deselected**, plus compile/CLI/Qt/Ruff/mypy/handoff.
A sandbox temporary-directory/process limitation required normal local test
permissions and workspace-local temporary output. Exact-head isolated evidence
is posted in the follow-up PR.

Read-only supplied ELF inspection finds CH7,055/NBA11 18,831 mask-family candidates,
zero rejected hits and zero unbacked dependency starts. Ghidra confirms CH's native
pointer/group selector and fallback behavior. This does not validate payload
extents, poses, complete registration, controls or gameplay portability.
No EBOOT edits, RPCS3 or automatic/testing JB. Donor gameplay/control changes
remain unimplemented.

# Pending PR integration and native animation audit

Combined source portable verification: **670 passed, 10 skipped, 2 deselected**.
Compile, CLI/Qt, Ruff, mypy, generated handoff and diff checks pass. New motion
modules/tests also pass full E/F/I lint. Source checkout omits optional native
helpers; exact-head isolated evidence is maintained in the integration PR.

Synthetic regressions cover banks above 10,000 records, malformed table/pointer
bounds, reference IDs, distinct collection strides, sentinel event arrays, local
alias cycles, motion names/categories, Legacy fixed-size encode/outer bytes and
invalid Legacy layouts. A stale roster-button label expectation was corrected.

Private read-only inventories: CH319 / NBA11 4,705 / NBA14 22,139 SingleMoCap;
no standard-header traversal errors or bounded-header/sample skips. Actual CH
crowd: 125 packed +125 alias candidates; NBA11 signature bank:333 +333. No envelope
errors/local cycles in these two banks. Ghidra and original disassembly establish
native animation fixups, reference handlers, collection stride and pad imports.
These are structural findings, not bone/pose/event semantics or gameplay tests.

No animation converter, donor gameplay bank, right-stick default or preset-A
change is enabled. Runtime smoothness, engine compatibility and PS3 behavior are
unverified. RPCS3 NOT RUN; automatic/testing JB NOT BUILT. All game inputs remain
unchanged. See ANIMATION_GAMEPLAY_PORT.md for native evidence and remaining work.

# PR #30 merged compatibility audit

Reviewed merge `fd9eae5d43f0dec436411661dcf99c52f326e562` in an isolated
checkout with `tools/dev/verify.py --python <prepared Python 3.12 interpreter>`:
**602 passed, 10 skipped, 2 deselected**. Compile, CLI/Qt smoke, Ruff, mypy,
handoff and diff checks passed. Offscreen OpenGL and the absent optional native
converter are skipped. Each of v1.16, v1.17, v1.18 and v1.19 is an ancestor.

Nine added synthetic regressions pass. Full follow-up source verification with
`python tools/dev/verify.py`: **612 passed, 9 skipped, 2 deselected**, all other
portable checks passed. Final exact-head isolated results are posted on the
follow-up PR. No production parser behavior changed in this audit.
See [scope and retained feature coverage](PR30_COMPATIBILITY_REVIEW.md).
No Windows package was rebuilt because dependencies, packaging and application
code are unchanged. No RPCS3, gameplay, EBOOT editing or real/testing JB copy;
small generated archive fixture outputs only. Unknown formats remain guarded.

# v1.19 Reborn Overrides V5.5 import support (original submission evidence)
# Player-face research verification

Windows / Python 3.12.14 source `tools/dev/verify.py`: **607 passed, 9 skipped,
2 deselected**; compile, CLI/Qt smoke, Ruff, mypy, generated handoff and diff
checks passed. Four added synthetic cases cover selector masking and unchanged
source, independent custom flags, biased-row morph tail bounds, rejection of NBA
or other strides, and missing-bank reporting. Final exact-head isolated results
are recorded on the research PR; optional native DLL absence adds an isolated skip.

`python -m choops_py.research.player_faces <original CH2K8 source>` reads all five
face banks and source roster with no unresolved banks: seven dedicated albedos,
13 normal records, 75 facial-hair textures, shared heads/presets; 5,685 players,
15 nonzero likeness selectors matching seven names, 5,670 generated selectors,
zero custom flags/stored morph arrays. All seven albedos pass byte-identical
DDS/GTF/DDS conversion in memory; extracted local face artwork visually inspected.
EBOOT function-specific TOCs, selector branches, seeded generation and morph
encode/decode loops were inspected read-only. No executable bytes are committed.

NBA 2K9 donor container/scene structure inspected. The selected NBA 2K14 sample
ZLIB variant and supplied 2K11 SDAT version/flags remain unsupported; these are
not successful extraction/port tests. No face writer, EBOOT change, RPCS3,
gameplay validation or real/testing JB; no Windows package/release requested.
See [the findings and reproduction command](PLAYER_FACE_RESEARCH.md).
# NBA 2K11 authenticated-reader and donor research

Windows / Python 3.12.14 source `python tools/dev/verify.py`: **609 passed,
9 skipped, 2 deselected**; compile, CLI/Qt smoke, Ruff, mypy, generated handoff
and diff passed. `python -m pytest -q tests/test_sdat_2k14.py`: **8 passed**.
Existing random reads/header/ciphertext/truncation tests now cover v3 and v4;
metadata corruption, mixed encrypted/raw banks, write blocking and rejection of
unknown versions/compressed/debug flags are covered. Six added parameter cases
retain the original v4 checks. Final isolated exact-head results follow on the PR.

Read-only supplied NBA 2K11: 6,974 archive entries, 72-byte descriptor/size64 TOC;
both encrypted banks authenticate sparse beginning/interior/end/cross-block reads.
Full standard-IFF header inventory has zero traversal errors. Generic animation
inspection reports 4,705 SingleMoCap records and unchanged source metadata.
Selected texture/SCNE/audio/roster/animation blocks decompress; floor f030 yields
two preview meshes without warnings. Stadium s734 yields 21 supported arena parts
and one unsupported UV part. Sample PNG high-detail vertices remain unsupported;
bench geometry decodes. A 48-kHz stereo ATRAC3 effect exports 43,008 PCM16 WAV frames.
ROST marker 0x225 is observed but no 2K11 roster editor enabled.

Ratings are conversion judgments, not port/runtime tests. No track poses decoded,
no direct cyberface/full-arena/HUD port, no Windows release/package requested,
no EBOOT edits, RPCS3/gameplay or real/testing JB. Reports/artwork/audio stay local
and excluded from Git. [Assessment and reproduction](NBA2K11_DONOR_ASSESSMENT.md).
# Combined scorebug follow-up verification

Private candidate: five SCNE reparses; 257 untouched gamedata records compare;
two replacement IFFs prepare and pass preflight; matched English literals resolve;
SELF payload round-trip and bounded executable diff pass. Nine synthetic wrapper
paths cover visible/empty/transparent/opening/closing/missing-scene/wrong-layout
conditions and preserve original callback inputs and stack/nonvolatile registers.
No runtime appearance, game execution, physical PS3 or JB result is claimed.
Public editor contract fixes and their portable tests are tracked in PR #32.
This follow-up changes documentation only in PR #36.

# Local executable experiment 01 — 2026-10-19

Private-only prototypes generated and audited on Windows / Python 3.12.14,
Capstone PPC64 big-endian and locally installed Keystone 0.9.2. Keystone is not
an editor dependency. Original decoded ELF and retail SELF digests match after
all work. Five variants pass allowlisted diff/header/branch and debug SELF payload
round trips; the control ELF is identical. No game code is executed by these
checks. 60,000 geometry samples cover both directions plus modern apex/corners/
joins and old-circle equivalence; 30,000 transfer-mask cases preserve neighboring
bits. Added instructions' register/TOC/stack/LR usage was reviewed.

The companion reparses with 10 old text styles retained and two native labels
added. Original decoded bytes and vertex data remain unchanged. Its relocated
SCNE extends an unrelated inferred span over 44,720 abandoned original bytes;
runtime acceptance is unverified and explicitly documented. Two-archive override
preparation/preflight passes with zero unapplied overrides; ZIP integrity is
checked locally. No automatic/testing JB, emulator, gameplay or physical-PS3 test.

Public changes are documentation/handoff configuration only. Scoped exact-head
handoff, Ruff, local-link and diff checks are recorded in the PR. Full runtime
suites and packaging are not rerun and historical passes do not certify EBOOT.
The cleanup preserves active tracked regression tests and user builds/inputs;
broader historical package deletion remains approval-blocked.

# Executable modernization research — 2026-10-19

Documentation-only update on Windows / Python 3.12.14. Read-only ELF mapping,
function-descriptor/TOC inspection and PPC64 big-endian Capstone disassembly
followed named menu registrations. The bounded scan recorded 580 candidate
strings / 75 TOC references; these are not an exhaustive executable analysis.
Input digest matched before/after scanning. No game data or executable writes.
Additional read-only assertions passed for both prior name-suppression branch
sites, CameraMenu table/handler descriptors, Game Rules table/callback and
non-file-backed camera state pointers; a second before/after digest matched.

Scoped verification: generated handoff/check, Ruff for the changed handoff
generator, local Markdown-link resolution and `git diff --check`. Exact committed
head results are recorded in the PR. Runtime suites and Windows packaging were
not rerun: no runtime/package code changed. Historical suite counts below do not
validate the newly proposed executable candidates. No Ghidra, RPCS3/gameplay,
executable patch, real/testing JB or release.
# Experimental uniform mesh editing — verification

Windows / Python 3.12.14. Targeted command:
`python -m pytest tests/test_uniform_mesh.py tests/test_scene_preview.py tests/test_direct_asset_previews.py tests/test_cli.py -q`
passed **42 tests**. The 15 new mesh/GUI cases cover byte-identical no-op import,
position-only writes in matching SCNE/Clth, unchanged unknown records, stale
manifests, UV/topology/count changes, nonfinite/excessive displacement, flipped
triangles, missing/ambiguous rest matches, split seams, unsupported layouts,
preset attachment regions and selected-source GUI dispatch.

Read-only actual asset inventory and private output audit: **21 IFFs, 33 record
pairs, 25,956 original rendered vertices**. All 21 no-op exports/reimports are
byte-identical. Edited logical blocks differ only in intended XYZ bytes;
unreferenced bytes, UVs, other attributes, constraints and record addresses stay
unchanged. All **21 replacements prepare and pass build preflight**. Before/after
rest-pose contact sheet inspected for all 18 distinct garment/build combinations.
Source inputs unchanged. Local editable/override assets stay out of Git.

Full portable verification uses `python tools/dev/verify.py --python PYTHON` and
a temporary directory outside project output. Its first run exposed missing
UUID imports in the new GUI methods; corrected and covered by direct selected-
source dispatch. A run with fixtures inside output invalidated an existing
output-safety test's premise; no production court behavior was changed for that
test environment. Windows worker verification requires normal worker access.
Final source portable verification passed **617 tests, 10 skips, 2 deselections**;
compile, CLI/Qt startup, Ruff, mypy and generated handoff checks passed. New
backend/test files also pass the full E/F/I Ruff selection. Exact-commit isolated
verification is recorded in the PR handoff.

Packed solver/collision and normal/tangent retargeting are NOT established.
No external DCC roundtrip certification. RPCS3/gameplay: **NOT RUN**.
Automatic/testing JB: **NOT BUILT**. No EBOOT change or release publication.

# v1.19 Reborn Overrides V5.5 import support

Read-only discovery against the supplied V5.5 folder and vanilla College Hoops
2K8 archive recognized 1,946 archive groups and scanned 25,428 files, including
17,596 DDS files and 7,794 record files. Numeric folders 1004 and 1055 resolved
to `shoe_100_04.iff` and `shoe_100_11.iff`; folder 1376 resolved to `uy011.iff`.
The V5.5 `icon_tatoo` path resolved to `icon_tattoo`. No game or override source
files were written. No JB copy was built. This is supplied-input discovery
evidence, not a game/runtime compatibility claim.

`git diff --check` passed on the submitted source changes. No full test suite or
package rebuild was run on the v1.19 branch in this update.
# Unreleased Legacy save editor foundation

Read-only inspection of the supplied 5,523,948-byte Legacy-mode save found a
validated roster payload at offset `0x438`, length `0x003DF800`, followed by
1,461,684 bytes of additional mode data. The embedded payload passed the current
roster model's structural validation with 5,685 players, 379 arenas, 443 teams,
1,373 coaches, 39 conferences and 988 uniform rows, with zero validation issues.
The adapter's unchanged encode returned bytes identical to the input. No source
save was edited; no saved output or JB was produced. The additional mode data's
semantics remain unknown.

`git diff --check` passed. No full test suite or package rebuild was run.
# Native scorebug contract verification

Targeted style/layout/localization suite: **23 passed**. New regressions reproduce
parseable misaligned literal vectors and verify native width-fit edits preserve
literal IDs, alignment flags and vertex payloads. Source portable verification: **628 passed, 9 skipped, 2 deselected**; compile,
CLI/Qt, Ruff, mypy, handoff and diff checks passed. Exact-head isolated results
are recorded in the current PR handoff.

Ghidra is read-only format evidence, not a Python bug detector or an in-game test.
No emulator, gameplay or automatic/testing JB is used. Private combined output
has independent native ABI/branch/scene checks; it remains a runtime candidate.

# Scorebug test05 verification

Targeted style/layout/localization/native-font suite: **23 passed**. New regressions
cover alpha restoration with unrelated properties/bones/events/payload unchanged,
invalid alpha/RGB rejection, count-only native-label suppression and propagation
through ordered mesh operations. Actual five-scene package prepares/preflights
both required archives without unapplied DDS. Source portable verification: **626 passed, 9 skipped, 2 deselected**; compile,
CLI/Qt, Ruff, mypy, handoff and diff passed. Exact-head isolated results are
recorded in the PR handoff.

Read-only built-archive analysis confirms test04 inputs were current; native code
shows normal-game city-name suppression. Owner declined an executable patch and
left names unresolved. Current scene/property checks do not certify gameplay or
claim names have been fixed. No emulator launch, EBOOT write or new JB build.

# Native test04 startup-crash correction candidate

Read-only user log: asynchronous resource-loader PC 0x00845E14, access violation
reading 0x4D4C0002, before HUD rendering. The failing thread contains added branding
tokens. Built English content matches the supplied native test04 IFF. Its decoded
block contains the old table plus an appended full replacement. Other build mods
are present; neither universal mod compatibility nor a fully isolated gameplay
root cause is claimed.

Targeted layout/style/font/localization suite: **21 passed**. Regression checks
require offset zero, one table, exact stored/logical-size equality and no H7A
wrapper, plus rejection of prefix/alias/multiple-resource layouts. All old actual
English translations remain byte-identical; new decoded size is old size +50 bytes.
The corrected ZIP preserves gamedata bytes from native test04. Source portable verification: **624 passed, 9 skipped, 2 deselected**; compile,
CLI/Qt, Ruff, mypy, handoff and diff passed. Corrected two-archive preparation and
build preflight passed with zero unapplied DDS. Exact-head isolated results are
recorded in the PR handoff.
No emulator run, executable write or new game build; user runtime retest remains.

# Test04 native branding follow-up

Targeted layout/style/font/localization regressions: **20 passed**. Covers explicit
ID low/high-float packing, preserved flags/vector tails, sorted localization insertion,
opaque sentinel/old-pool preservation, malformed/duplicate/encoding rejection, safe
IFF growth and rejection of changes to existing translations. Actual native-label
style matches clock font alias, RGB, alpha and shadow values. All 21,637 existing
localization rows and old token bytes are preserved; only one tagged literal is added.
Two-archive override preparation/preflight passes with zero unapplied DDS.
Source portable verification: **623 passed, 9 skipped, 2 deselected**; compile,
CLI/Qt, Ruff, mypy, handoff and diff passed. Final exact-head isolated results
are recorded on PR #32. No emulator, executable
writes or native test04 JB built; runtime placement/visibility awaits user testing.

# Scorebug test04 follow-up

Targeted native style/layout/font checks: **15 passed**. New regressions distinguish
value-before-type/key properties, preserve ABL bone references when callback names
change, preserve all other original header bytes/payload, reject malformed font
properties reject shared font-property writes and duplicate bindings, and restore an explicitly hidden draw's alpha. Actual scene-only overrides
prepare/preflight successfully; five scenes, one archive, zero unapplied DDS.
Source portable verification: **618 passed, 9 skipped, 2 deselected**; compile,
CLI/Qt smoke, Ruff, mypy, handoff and diff passed. Exact-head isolated results
are recorded on PR #32. Runtime names,
font sizes, popup states and exact branding appearance remain for user testing.
No RPCS3, EBOOT writes or test04 JB built.

# Scorebug test03 follow-up

Targeted layout/native font regressions: **11 passed**. Covers partial-draw
preservation, gradient flattening, unchanged UVs on shear removal, text basis and
translated-marker offsets, ordered edits, native glyph coverage/spacing and
malformed glyph rejection. Local scene-only overrides prepare/preflight with
one gamedata archive, five SCNEs and no unapplied DDS. All 257 other stock records
and all scene block sizes remain identical. Source portable verification: **614 passed, 9 offscreen GL skips, 2 deselected**;
compile/CLI/Qt/Ruff/mypy/handoff checks passed. Exact-head isolated verification
is recorded on PR #32. An initial sandbox run could not create pytest temporary
fixtures; rerunning with normal filesystem permissions passed. Runtime text/meter/popup behavior is not
certified; no emulator, executable writes or new JB build.

# Scorebug test02 follow-up

Portable Windows/Python 3.12.14 verification: **608 passed, 9 offscreen GL skips,
2 deselected**; compile, CLI/Qt, Ruff, mypy, handoff and diff passed.
Scene-only overrides prepared/preflighted successfully with zero unapplied DDS.
Final exact-head isolated review is recorded on the PR.

Synthetic layout regressions cover vertex/UV/color/alpha/depth changes, preserved
unknown interleaved data, paired text matrices/markers, invalid-target rejection,
restart-strip topology and inventory of sixth-man text anchors. Actual static
asset checks preserve all 258 unedited gamedata records and scene block sizes.
No runtime placement, popup visibility or font behavior is certified. See the
scorebug research and PR for exact final-head checks and local artifact evidence.

# v1.19 compatibility verification

Windows / Python 3.12.14 portable checks: **603 passed, 9 offscreen GL skips,
2 deselected**; compile, CLI/Qt, Ruff, mypy, handoff and diff checks passed.

Five new synthetic cases cover flat DDS cubemap imports through authoritative
Python manifests for TXTR and SCNE, retained five faces/header bytes and report
semantics, a paired-CDF face preservation case, named invalid-IFF roles/magic and retained structural error codes.
No invalid-container acceptance is added. Read-only actual checks prepare and
preflight the supplied frontend/legal ZIP; full halftime HDR cube artwork matches
the imported DDS, scene headers/capacity remain unchanged. No source bank writes.
The same ZIP also passes in an isolated v1.16 checkout; its generic screenshot
failure is not reproduced. Final portable/isolated/frozen results are recorded
on the release PR.

# Verification — v1.18

Full portable verification on Windows / Python 3.12.14: **598 passed,
9 offscreen OpenGL skips, 2 deselected**; compile, CLI/Qt smoke, Ruff, mypy,
generated handoff and diff passed. New navigation links resolve locally.

Current source combines the reviewed NBA support, split-header regression fixes,
key/center-circle guide and documentation cleanup. Exact final-head commands and
results are recorded in the release PR and release notes after verification.
The portable runner is `python tools/dev/verify.py`; the isolated run uses the
same runner with `--python` pointing to the prepared development interpreter.

Regression additions from PR #25 cover NBA schema detection/wrapper preservation,
SDAT authentication/tamper/truncation, ZLIB boundaries, extended scene layouts,
cross-bank headers, both append/repack writers and named corrective diagnostics.
PR #26 covers authored key/center routes, radial UV direction, elevation,
source preservation and independent Qt toggle behavior. Wrapper unit assertions
are consolidated into test_binary.py without removing coverage.

Previous exact-head evidence: PR #25 had 596 portable passes (9 GL skips,
2 deselected); PR #26 had 577 (9 skips, 2 deselected). These are separate branch
counts, not the combined release result. Isolated runs additionally skip an
optional native DLL when it is absent. Historical per-release detail is in
[verification history](history/VERIFICATION_THROUGH_V117.md).

The Windows package requires startup, CLI, audio round trip, lazy SDAT dependency
checks, ZIP integrity and checksum verification. No RPCS3/gameplay, real/testing
JB, EBOOT writes or copyrighted assets in Git. See [testing policy](TESTING.md).
