> Historical record, captured before v1.18. Not a current support contract.
> See ../CURRENT_STATUS.md and ../TEST_REPORT.md. Relative links below retain their original context.

# Unreleased — split-header rebuilding and actionable override failures

Rebuild planners now read the complete logical pre-body header region across split
banks, not just 0A. Append writing also uses bounded split-bank writes so updating
such a header never extends 0A across a bank boundary. The archive reader follows
TOCs across banks too. Synthetic append/repack regressions preserve opaque header
bytes and unchanged inputs. The supplied original CH/NBA sources do not reproduce
the reported error; a split-header fixture reproduces the old failing condition.

Truncated/missing banks report filenames and expected/actual byte counts. GUI build
and override failures keep their full details in Mod Builder, with specific next
steps for source damage, CDF pairs, duplicate/ambiguous selectors, DDS layouts,
geometry overlap and stale prepared inputs. No unsafe automatic renaming or byte
removal is used as a repair. Read-only NBA2K14 overrides can pass preview validation;
authenticated JB rebuilding stays blocked and the completion dialog says preview
only for that source. Combined portable verification: 596 passed, 9 GL skips,
2 deselected; compile/CLI/Qt/Ruff/mypy/handoff/diff passed. See USER_GUIDE and
TEST_REPORT.

# Unreleased — NBA 2K14 reading and separate NBA roster editors

NBA 2K14's SDAT-wrapped seven-bank / 72-byte-descriptor archive is now readable
through the shared Explorer, with authenticated random-access decoding and ZLIB
IFF support. Extraction and texture inspection work; SDAT/extended-descriptor JB
rebuilding is explicitly blocked. Supplied f000 floor decodes two meshes; s000
arena decodes 61 meshes with one unsupported-UV warning. NBA 2K14 combined jersey
artwork/cloth binding is unresolved. College Hoops and NBA 2K9 writers stay enabled.

Roster payloads dispatch dynamically to College Hoops, NBA 2K9 or NBA 2K14 models.
NBA names, height/weight, jersey number, face ID and primary positions are editable;
NBA 2K14 also has a separate secondary-position field. NBA team/arena text,
read-only membership/asset links, side panels, numeric dropdowns, undo/redo and
wrapper-preserving export are implemented. Unknown ratings/body fields and NBA
text heap growth remain blocked. No entire-roster-semantic or gameplay claim.

Filename candidate families and corroborated shared record-type labels expanded.
Animation portability is research only: 319 / 904 / 7,460 SingleMoCap records found
in CH2K8 / NBA2K9 / NBA2K14. NBA2K9 is structurally closer; neither direct swap is
certified. See NBA_ROSTERS_AND_2K14.md and ANIMATION_PORTABILITY.md. Both instances
must keep those documents and this generated handoff current. No source game was
modified; no RPCS3, EBOOT edits, animation port or real/testing JB build.

# Unreleased — key and center-circle alignment toggle

Models/Courts adds an independent, default-off “Alignment guide: key and center
circle” toggle. It copies stock S256 key-line, outer key-circle and center-circle
batches (confirmed palette routes 20, 2, 10), raised one game unit. No filled key
or center paint is added. Curves thin across V; straight key lines across U using
the existing thin flat guide shader. Actual floor draws, palettes and textures
remain unchanged. This is an independent update from the NBA support PR #25.

# v1.17 — automatic shared PS3 2K archive layouts

The existing editor now detects the supported College Hoops/NBA size32 and size64
TOC layouts automatically. Extraction, cached source/override previews, DDS import
and fixed/growing/repacked builds use the detected source schema. Game title/ID
are shown from PARAM.SFO; College Hoops 2K8 roster controls remain specific to their
confirmed schema. Unknown/ambiguous layouts fail explicitly; universal support for
all 2K years/platforms is not claimed.

Read-only NBA 2K9 validation: 5,624 entries / 6 banks; selected IFF/CDF samples
extracted exactly; five standard IFFs' blocks decompressed; textures and 71 menu
logo records parsed. Shared preview services show 2 jersey/shorts meshes, 2 floor
meshes and all 78 arena meshes / 58 images. Half4 UV/color declarations and
case-sensitive internal CRC labels bridge the shared format variants. Source
banks are unchanged. A standalone research inventory/extractor is also available.
See PS3_2K_ARCHIVES.md for evidence, commands and explicit remaining limitations.
Rebuilding is validated with synthetic fixtures only; no real/testing JB or RPCS3.

Official v1.17 integrates PRs #22–24 and includes the Windows application.
Portable verification: 575 passed; frozen startup/audio and both synthetic writer
layouts passed. Both instances must maintain these docs and the generated handoff
on every subsequent update.

# v1.16 — sequential rebuild verification and queued soundtrack edits

Rebuilding growing archives now verifies preserved bytes sequentially in 4 MiB
chunks and keeps bank handles open, replacing thousands of per-entry opens and
random reads. Relocation writes also reuse bank handles. Existing DDS conversion
and prepared-override caches remain enabled; selecting unchanged overrides still
reuses validated archives. Fresh build outputs are always checked rather than
trusting a prior build's verification result.

Source preconditions share the replacement's original-asset read; unrelated
preconditions are streamed. CDF pairs avoid eagerly rereading partners already
supplied as replacements. DDS preflight temporary folders are removed after
success or failure. The CLI build command now uses the same manual-output policy
as the GUI/backend; other export commands retain their output restrictions.
Fixed-size builds check free space before copying. Source
inventory is captured before planning/preflight, so changes during that phase
also prevent publication.

Growing-build verification now checks preserved bank padding and all copied
non-bank files, in addition to TOC identities, exact generated headers and
replacement payloads. Cancellation/failure retains atomic cleanup. No hard links
or writes to source files are used.

Synthetic benchmark: 8,192 shuffled entries / 32 MiB, Windows Python 3.12:
1.5131 s previous per-entry verification versus 0.0477 s sequential (31.69x for
this verification phase); bank opens reduced from 16,384 to 2. This is not a
whole-build speed estimate; disk copying, texture conversion and asset checks
still take time. Reproduce with `python tools/dev/benchmark_rebuild.py`.

This release also includes PR #22: queued multi-song WAV imports before one bank
save, manual JB output folders, preserved opaque header gaps, and read-only
roster/scorebug research. Complete roster semantics and dynamic scorebug behavior
remain unresolved. No alternate assets, RPCS3, EBOOT edits or real/testing JB build.

# Unreleased — queued audio, manual JB output and research continuation

Audio now queues individual WAV replacements before one save. Selecting another
WAV for the same bank/index replaces its queued choice; removing/clearing is
explicit. Save writes one combined bank and matching global.iff AUSB metadata.
Cancelled output selection or failed conversion retains the queue. Pending songs
are tied to the source JB path and bank size/mtime/inode snapshot. Reopening the
same unchanged source is supported; a different/changed JB is rejected.

JB output can be selected in Mod Builder on any drive. Builds still reject source
or overrides overlap, filesystem roots, links/junctions, existing files and
unowned nonempty destinations. Atomic publication, manifest validation, rollback
and owned temporary-folder cleanup work beside the selected destination. Other
export workflows retain their documented output/ restrictions.

Fixed the archive-growth error `Unclassified nonzero header padding`: replacements
use existing TOC slots and preserve the opaque post-TOC gap. Added entries may
consume only zero slots. Repacking preserves opaque bytes in place when the body
start stays fixed; it refuses to relocate opaque bytes or overwrite them with a
larger TOC. Unknown header bytes are never zeroed to bypass validation.

Roster research corrects reported relative anchors (stored displacement includes
+1), accounts for the 33 confirmed bits in each uniform row, lists unresolved
bit-mask runs and reports both legacy biased windows and engine logical record windows.
Logical windows have no table overlap on the stock input. A newly audited
arena +0x24 relative reference resolves to the team-name anchor for every nonnull
stock row: 347 resolved and reciprocal team arena links, 32 nulls. Its wider runtime
ownership/write behavior is not established; no new backlink writer is exposed.
The full roster is still not semantically reversed. See ROSTER_SEMANTICS.md.

Scorebug discovery identifies authored records/parts/textures in gamedata.iff and
gamedataextra.iff. A read-only inventory command and SCOREBUG_RESEARCH.md record
exact routes. Runtime score/clock/text bindings and geometry editing remain
unresolved. No RPCS3, EBOOT writes or real/testing JB builds.

# v1.15.4 — faster override-folder preparation

Override selection prepares independent archive groups in separate CPU worker
processes (up to six, capped by cores and available RAM). A memory-weighted queue
keeps heavy archives from overloading the system. Each archive has one writer;
DDS priority, SCNE replacement, cube handling and validation remain unchanged.
Progress shows completed archives and active workers. Cancellation or failure
stops workers before removing partial output; the previous workspace is retained.

Repeat selection reuses validated completed archives from the current prepared
workspace when inputs, source checksums and importer code match. Changed inputs
recompile only their archive; tampered cached output is rejected and regenerated.
Conversion-cache identity is computed once per process and directory pruning is
batched under a cross-process lock, with a final size-maintenance pass.

Measured on 14 supplied scene groups / 612 DDS inputs with warm conversion cache:
Final run: 24.838 s serial, 10.008 s with six workers (2.48x),
6.676 s unchanged repeat. An earlier run measured 3.08x; timings vary with cache
and machine load.
All resulting archive hashes matched. These are preparation-only measurements;
whole-folder timings also include discovery and compatibility checks and vary
with CPU, RAM, storage and cache state. No RPCS3 or automatic/testing JB build.

# v1.15.3 — frontend override import geometry fix

Fixed folder selection aborting with `frontend_sync.iff: Geometry overlaps a
texture image`. Menu SCNEs can store inline geometry in their header block and
textures in a separate block. Image packing now distinguishes inline vertex
stream flag 0x40000002 from GPU stream flag 0x40000003, and header-relative index
flag 0x10 from data-relative 0x20000010. Inline geometry/pointers remain unchanged;
GPU buffers retain relocation and byte-preservation checks. Real overlaps and
out-of-bounds or modified inline geometry still fail closed.

Read-only validation passed all 14 supplied non-stadium SCNE import groups.
The complete portable suite passed 524 tests.

A failed folder import is atomic: it preserves the previous prepared workspace.
That explains the old LSU preview after the failed reselection. Once import
finishes successfully, the live source index and current S258 overrides activate.
No source files, prepared snapshots, EBOOT or JB builds are modified by this fix.


Legacy flat DDS artwork targeting a base cubemap is handled only in recognized
legacy folder imports: it updates the first (+X) face, resampled to the original
format, dimensions and mip chain; the other five faces are retained from source.
The result remains a full cubemap and its descriptor is preserved. The GUI
compatibility summary identifies this operation. Modern manifest-based imports
and direct DDS imports still require matching complete cubemap inputs.

# v1.15.2 — current override files in previews

Folder-based previews now use current loose DDS, SCNE and archive inputs instead
of treating an earlier prepared build snapshot as the selected folder. Only the
requested archive is compiled for preview; unchanged inputs reuse a bounded
64 MiB compiled cache. File changes invalidate materialized and decoded previews.
Missing or incompatible live inputs raise an error rather than showing JB art.
The same source applies to Explorer, texture, jersey, shoe and stadium previews.

Select overrides folder once after upgrading to register live input locations.
Older workspaces and imported patches remain usable prepared snapshots and are
labelled accordingly. New or renamed files require selecting the folder again.
After editing inputs, preview again (or switch sources) to reload. Select the
folder again before building to prepare an updated build snapshot; previews do
not change prepared builds or any original input. JB fallback applies only where
no replacement exists. No emulator, testing JB or EBOOT changes.

# v1.15.1 — resizable full-width 3D preview


## Resizable 3D preview

Models / Courts reserves more height for the full-width preview. Drag the wide
divider above it up or down to enlarge or shrink it. Controls scroll independently
when space is reduced; the main application window can also be resized normally.
Fit camera frames the model after changing the available viewing area.
# v1.15 — Explorer overrides, references and cache fixes

Roster controls explicitly open external roster IFF or decrypted USERDATA/USRDATA
(and supported save ZIPs), load the source JB roster, or load a real override
roster replacement independently of the preview dropdown. Export offers roster
IFF and decrypted USERDATA. An external IFF supplies its own export template;
other inputs use the loaded JB or a chosen IFF template. Save copy preserves the
original wrapper, including other members of a loaded save ZIP. USERDATA export
does not create encryption, PARAM files, or a complete console save package.
All writers validate and reparse the result and protect the original input.

Release: https://github.com/ZMO34/CHoops-Extractor-Reborn/releases/tag/v1.15

Select overrides folder… is in Explorer. The stale-fallback bug is fixed, source
counts and source-aware asset rows are shown, and the visible workspace is used
consistently. Dry run is removed from the GUI; JB builds still validate first.
Confirmed roster ownership includes uniform selection menus, gameplay uniforms,
cloth meshes, player/team footwear, stadiums and paired logo banks. Wider
reference columns have full-text panels/tooltips. CSVs exclude UI/research
fields and retain source/identity/stale-edit safety columns.

Both JB and override indexes are retained. Separate validated scratch copies and
a bounded 64 MiB decoded image cache support switching sources. DDS takes
priority; raw TXTR is used only without a matching DDS. SCNE geometry remains
supported. No user filenames or artwork were changed: the supplied names already
resolved to 1,824 targets. Existing prepared data showed 354 stadium and 727
uniform overrides; no shoe packages were supplied. No RPCS3 or testing JB build.

# v1.14.1 preview source/list hotfix

Release: https://github.com/ZMO34/CHoops-Extractor-Reborn/releases/tag/v1.14.1

Top-toolbar Source JB / Selected overrides dropdown controls all previews.
Models / Courts offers Jerseys, Shoes and Stadiums / Floors subtabs with pick-only
lists, explicit Override / JB fallback labels and retained selections. Missing
archive/scene names are handled safely. Switching sources keeps the active page.
Read-only S258 preview succeeded with unchanged input. 494 portable tests and 22
native GUI/GL checks passed; Windows frozen startup/audio checks passed.
Broader roster/shader research remains incomplete as described below.

# v1.14 release preparation

Direct Models / Courts selectors now preview jerseys, shoes and stadium/floor
packages without first opening an IFF. Captured source/override selection applies
to SCNE and texture data. Jersey shape controls remain available; stadium modes
choose arena+floor, floor only or arena only. Integrates tested PR #14 updates
and the override-folder fix in PR #15; broad reverse-engineering remains ongoing.

# Override-folder selection fix

The GUI action is now Select overrides folder… . Existing mod directories no
longer cause Choose a new mod directory: selection prepares a fresh numbered
workspace, preserving old folders, and updates both build and preview paths
only after successful compatibility checks. Verification: 464 portable tests passed; 26 targeted override checks passed.
Separate PR from the ongoing roster
and shader research (#14); no emulator or automatic JB build.

# Current project status

## Active roster, floor-layer and animation continuation

v1.13 is published from master 9e18f32aed8d0e3f81c2cfb05e0346d8854320b9:
https://github.com/ZMO34/CHoops-Extractor-Reborn/releases/tag/v1.13.
Its Windows package passed Windows/Linux CI and local frozen startup/audio checks.

The next feature branch adds orange advisory keyboard-limit warnings, independent raised
alignment guides from fixed stock S256 court coordinates, safer conference index validation, exact conference-logo editor routing and
read-only motion-record discovery/export. Byte coverage now reports unresolved
bits within packed words. Conference +0x1A is a tournament index, not a logo ID;
its unsafe generic writer is protected. See CONFERENCE_ASSETS.md and
ANIMATION_RESEARCH.md. No secondary-position search: the owner closed that task.

Complete remaining byte semantics, universal engine text ceilings, reflection,
fake-bump/AO and all dynamic palette modes remain unestablished. This continuation
does not claim completion of those research goals or gameplay certification.
No RPCS3, EBOOT edits, added alternates or testing JB folders.

Continuation verification: 482 portable tests passed (9 offscreen GL skips,
2 deselected), 28 native Qt/OpenGL checks passed, plus hidden read-only S256 line
rendering. Compile, CLI/Qt startup, Ruff, mypy and handoff checks passed.


PR #13 combined roster/arena continuation: twelve additional appearance/tattoo/
signature fields with verified inclusive option bounds, all 112 jump-shot labels,
and authored arena vertex-colour/alpha, second-UV lightmaps, glow/flare masks.
461 portable tests passed (9 offscreen GL skips, 2 deselected); 144 native
checks passed. See ROSTER_SEMANTICS.md and ARENA_SHADER_MASKS.md. Complete
remaining roster bytes, per-field engine ceilings
and every runtime shader/palette mode remain unproved; no guessed edits are added.


Authored jersey lettering continuation (PR #13): front/back numbers 0–99/00,
roster-linked or preview-only number choices, and curved Reborn surname rendering
use actual indexed fonts/metrics and placement. Declared material DiffuseColor
and integer shader switches are fixed. Palette 16/17 runtime-copy roles are
confirmed. Full roster semantics and remaining arena mask routes
remain under research. No guessed writers, EBOOT edits, RPCS3 or testing JB.
Verification: 448 passed, 4 offscreen-OpenGL skips, 2 deselected; native hidden
OpenGL checks separately passed. Source startup, CLI, lint/type checks passed.
The PR #13 continuation was published in v1.13; the active next branch above is unreleased.


## Roster / preview continuation

v1.12 is published from merged PR #12. Continuation source fixes worker source
snapshots and named SCNE identity, comparison reference matching, school-filter
reset and menu-logo subrecord references. Confirmed Edit Schools text capacities
are mapped to roster fields, and the jump-shot animation ID is editable with
confirmed bounds. See ROSTER_SCALE_AND_PREVIEWS.md for evidence and unfinished
semantics. This continuation is not a published release.
Combined with merged PR #11: 341 tests passed, 2 deselected; source/Qt startup,
lint/type and documentation checks passed. No RPCS3, EBOOT edits or testing JB.
## Latest release and single-slice integration

v1.12 publishes merged PR #12 at master 4f0eec7f95f9d624ff0fe09b4aac489ba4cf058e.
Windows ZIP and SHA256SUMS: https://github.com/ZMO34/CHoops-Extractor-Reborn/releases/tag/v1.12.
Exact-head Windows/Linux CI and local packaged startup/audio checks passed.
PR #11 is integrated with that source and independently tested: 329 passed,
1 isolated native-audio skip, 2 deselected. Depth-one, non-cubemap 3D TXTRs
support 2D DDS replacement while retaining their original descriptor; deeper
volumes remain unsupported. See TEST_REPORT.md for exact review evidence.

## Active roster scale / preview project

The feature branch adds source-bound CSV editing, selective comparison, atomic
ratings paste, inline rating boxes, school filtering, Class/Redshirt controls,
growing UTF-16 text, shared source/override SCNE and texture previews, archive
categories/references and bounded conversion/normalization caching. This remains
a continuing research project; its implemented checkpoint is published in v1.12,
while full reverse engineering remains unfinished.
See ROSTER_SCALE_AND_PREVIEWS.md for exact behavior, evidence and remaining work.
Development verification on 2026-10-13: 326 tests passed, 2 deselected; source/Qt
startup, lint/type and generated handoff checks passed. No testing JB or gameplay.
Merged checkpoint: https://github.com/ZMO34/CHoops-Extractor-Reborn/pull/12.
Jersey colour constants now trace to slots 0/1 and a separate mode using 14/15;
fragment routing and mode selection remain unfinished.
Recent functional PRs were merged before work; baseline is v1.11/master
7796fcbd72c127730f484c67a5b0de26440ed066.

## v1.11 side-panel update

Every roster category has a right-side editor. School palettes, shoes and jersey
previews are in appropriate side tabs; Edit selected/Team palette/shoe toolbar
actions are removed. Player School supports guarded move/unassign; all 18 slots
and counts are handled, with active player row zero correctly represented.
School brand application updates that school’s players only in one undo step.
Jersey preview combines top/shorts and offers neck/build/cut dropdowns. No alternate
assets created. See ROSTER_SIDE_PANELS.md; it supersedes historical 16-slot claims.

## v1.10 roster usability update

Current public GUI combines Teams/Edit Schools as Schools, displays player height
in feet/inches and positions as PG–C, and keeps Player/Ratings/Scholarship details
beside the player table. Scholarship/Walk-on is writable through a verified flag,
preserving weight and unknown bits. Separate properties/attributes dialogs and
D1/alternate/independent-asset actions are removed from the release surface;
conference realignment remains. No alternate work is authorized in this update.
See PLAYER_QOL_RESEARCH.md; older feature descriptions below record historical
backend capabilities rather than removed public actions.

Updated 2026-10-13. Upstream: ZMO34/CHoops-Extractor-Reborn; base: master.
Baseline before this handoff: `e556e360d0091df0bb645da9eb1d279e9d8f9e3a`.
Last published Windows feature release at that baseline: **v1.07**, commit
`bf43d81b10ea2f16bab7df3e798edb64435ab6f4`.
Check GitHub and git history for newer commits/releases; these are provenance,
not a permanently current HEAD assertion.

## Implemented foundation

- Native Python/PySide6 desktop GUI; CLI and GUI share parsers and services.
- Split JB archive browsing, extraction and identity recovery; bounded IFF/CDF,
  H7A compression, tool wrappers, TXTR and SCNE handling.
- Built-in DDS/GTF conversion, recursive override discovery, DDS priority over
  raw TXTRs, replacement SCNE priority, dynamic supported stadium asset sizes.
- Base-layout normalization outside sNNN stadiums; preserve source dimensions,
  format, mip count, remapping and layout. Use vanilla source for vanilla sizes.
- DDS replacement accepts depth-one 3D TXTR descriptors as single-slice images,
  preserving their descriptor; deeper volumes remain read-only.
- Texture and geometry previews including arena, cloth and shoe selection;
  material texture routing, packed geometry, camera movement and RSX remapping.
  Basic previews do not reproduce every game shader. Artificial floor lift is
  not the solution and must not be reintroduced.
- Roster adapters, editable confirmed fields and conference history records,
  ratings, undo/redo, RGB color dialog,
  packed Yes/No and L/R choices, player/team shoe editing and roster IFF export.
- Community ZIP/save wrappers are preserved. Existing unchanged malformed name
  characters are warnings; new corruption or invalid pointers still block writes.
- Explicit alternate-linking/asset-building operations, availability checkboxes,
  optional D1 conversion. No automatic conversion or profile unlock bypass.
- Manual JB staging/building, source hash preconditions and transactional writes.
  Having this feature does not authorize agents to create testing game builds.
- Reusable single-surface court preparation; actual bump semantic and DXT5nm
  routing; only extra **floor** draws disabled. Arena remains normally textured.

## Current audio project

`audio_tools/{codec,banks,workflow}.py`, `formats/audio.py`, and the thin native
ATRAC3 helper source provide an **experimental** backend. Mapping recovered 23
licensed tracks and 64 fight songs in cribmusic. Title/artist/artwork mappings are
data in soundtrack_names.json. WAV decode/re-encode passed a synthetic round trip.
Bank replacement updates AUSB offsets/durations and checks untouched streams.
Workflow and game archive replacement still need broader regression validation.

Experimental catalog/WAV/song/batch/AUDO/jukebox-art CLI commands are exposed;
unchanged manifest WAVs are skipped and sample bounds/export overwrite are checked.
The Audio workspace now uses the shared backend in the Qt studio, with distinct
Licensed Music and Fight Songs tabs, selected/section WAV export, WAV replacement
preparation and shared cover-art actions. Independent review fixes scene/shoe
navigation to Models/Courts by name, removes a clean-clone test dependency on
proprietary converters, and makes batch WAV export transactional. See PR #5 for
integration/review status. The `codex/audio-codec-packaging` branch adds a
restricted LGPL FFmpeg CLI and the ATRAC3 encoder to the standalone Windows GUI,
with matching source archives and notices. Exact-head Windows CI built both
helpers, packaged the GUI, and passed the frozen synthetic WAV round trip on
`e149790005fdaeb14d0a1b79689d0a3de3b8f2da` (run 54). This is CI-verified branch
work, not yet a published release. Follow-up fixes the ATRAC helper's PCM input
ceiling to ±4.0, aligned with its internal 1/4 scaling, for over-range float WAVs.
Licensed Music and Fight Songs replacements are also trimmed or silence-padded
to the selected track's catalog sample length before archive rebuilding.

Song-title/artist editing stays read-only because archive-only routing is not
established, and EBOOT writing is prohibited. Unknown AUDO loops and general CDF
audio growth remain unsupported. Users stage outputs and build JB copies manually.
See AUDIO_RESEARCH.md and AUDIO_WORKFLOW.md.

## Priorities for the next instance

1. Review and publish the CI-verified LGPL-only Windows audio-helper package,
   including corresponding sources, notices and packaged WAV round trips.
2. Continue independent validation of audio metadata identity, conversion
   limits, cancellation and no-overwrite handling. Keep uncertain name fields
   read-only. Reject non-WAV replacement sources before codec conversion.
3. Validate standalone/paired/inline AUDO handling and explicitly block unknown
   loop formats or unsupported CDF writes. Do not claim all formats writable.
4. Continue remaining roster semantics, palettes, shaders and asset-linking
   investigation as separate documented PRs; do not distract from audio validation.

## Remaining uncertainty

- Six team palette words (16, 17, 27–30) have no verified role. 22 exact Edit Schools
  captions plus three additional runtime roles are known; older nine-caption
  requests must not be mistaken for the latest remaining count.
- Complete arena shader-mask routing and authored number/name atlas behavior.
- Alternate/profile unlock behavior and newly inserted asset consumption in game.
- Independent asset IDs/menu-logo handling for decloned classic/all-time teams.
- Commercial shoe style names and exact special-family UI caption.
- Crash-free court texture budget. 4096 is a dimension ceiling, not a tested safe
  allocation. Defaults: court 2048x1024 DXT5; normal 512x512 DXT5, full mips.
- Soundtrack title localization override route, AUDO loop semantics, CDF growth.

## Verification boundary

No emulator tests and no automatic testing JB builds are permitted. v1.07 had
135 targeted Python/Qt checks plus private roster save/reopen and archive checks.
The initial audio commit had syntax checks and 10 existing archive regressions.
The handoff/audio CLI update passed 240 portable tests, source smoke, scoped lint
and mypy. Native WAV re-encode/resample, AUSB preservation and AUDO/header checks
are covered. Read-only stock catalog returned 23 licensed/64 fight/159 total music
bank streams. No game replacement consumption validation. See TEST_REPORT.md for
exact commands; new commits require their own results rather than reused counts.
The LGPL-helper packaging branch passed the Windows build and packaged audio
round trip on `e149790005fdaeb14d0a1b79689d0a3de3b8f2da`; see TEST_REPORT.md.

All game inputs, rosters, templates, private reverse-engineering helpers and raw
audio are local and absent from Git. A fresh PC must supply its own authorized
fixtures. Do not assume a generated court template or any old local build exists.

Additional appearance/tattoo/post/free-throw fields and all 112 jump-shot captions are now supported; see ROSTER_SEMANTICS.md. Arena vertex-colour/alpha, lightmap, glow and flare routing is implemented; see ARENA_SHADER_MASKS.md for evidence and remaining runtime effects.

Text edits now grow beyond old allocations and keyboard entry capacities. The UI separates advisory game-keyboard sizes from unproved engine ceilings; structural pointer/UTF-16/adapter guards still apply.

ROST string fixup 77FB1C computes field + signed delta - 1; 7C5818
consumes big-endian wide characters. The previous shifted LE view only happened
to work for ASCII. Copy-on-write now preserves non-Latin text and aligned targets.
The shared formatter count is limited to 65,535 UTF-16 units; smaller display
ceilings remain unresolved. Qt's unrelated 32,767-character cap is removed.

Preview source/list hotfix: the top toolbar dropdown selects Source JB or Selected
overrides for every preview category. Models / Courts has Jerseys, Shoes and
Stadiums / Floors subtabs with pick-only asset lists, preventing typed unmatched
filenames. Override mode labels replaced assets and JB fallbacks explicitly.
Unnamed archive entries no longer break stock court-reference lookup.
v1.14 is published from 2158df982f43ba3dbb1e2df1cfcd2030fb0a25ea;
this follow-up targets the reported missing-name error and source-list UX.

Override-source refresh fix: selecting another overrides folder while Selected
overrides is already active now refreshes asset lists immediately and reloads
the active preview after preparation. Preview loading uses the visible Mod
workspace field, not an older cached path. The toolbar shows the loaded override
count; an unavailable workspace is not mislabelled as JB fallback. Existing
legacy DDS/SCNE folder names remain supported; no bulk rename is required.

Explorer/workspace update: Select overrides folder… now lives in Explorer,
with source-aware asset sizes and Override/JB labels. Dry run is removed from the
GUI; Build JB copy still performs automatic validation. Roster references cover
home/away/alternate selection menus (SELUA/H/X/Y/Z), gameplay uniform banks,
confirmed cloth geometry, player/team shoes, stadiums, paired CDF payloads and
conference/school logo banks. These links use the loaded roster. The wider
reference column, full-text panel and tooltips preserve long references.
Unsupported display metadata is reported without escaping the Qt result callback.

JB and override indexes remain available together. Source-specific scratch files
are reused while file fingerprints are unchanged; RGBA previews share a bounded
64 MiB content cache. Changed manifests invalidate override snapshots; changed
payloads still undergo source/checksum validation. DDS artwork skips the matching
raw TXTR replacement; TXTR remains the fallback only when no DDS is present.
SCNE replacements remain supported. CSVs use explicit binary-backed field
whitelists: asset references, preview labels, research fields and row offsets are
excluded, while source/stale-edit safety columns are retained.
