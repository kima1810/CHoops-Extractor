## Unreleased — RPCS3 game patches

- Add `rpcs3_patches/`: the BLUS30078 RPCS3 patch file (60 FPS, poll rank on the
  scorebug / Team Select / pregame matchup card, recruit generation, Legacy
  transfers) with its code-cave generators, offline interpreter checks and TTY
  probes. Emulator patches only; the editor still does not patch executables.
- Add Quick Game team cycling in conference member order (alphabetical after
  realignment) and a 30-second shot clock to the patch file.

# v1.23

- Native macOS Apple Silicon/Intel app packages and Windows x64 release archives.
- Mac writable data outside the app bundle; native audio and OpenGL package checks.
- Per-package source identity and checksums; existing v1.22 behavior retained.

## v1.22 — alternate discovery and combined research updates

Windows extended drive/UNC path spellings are normalized consistently, fixing the
intermittent parallel-worker output-root rejection without relaxing source guards.

- Recognize newly enabled X/Y/Z uniform and SELU folders from the effective roster even without a team-assets manifest; compile their nested DDS/raw records using the matching Home template.
- Respect byte ranges when reading added archive metadata and retain new archives whose artwork matches the template. Keep DDS priority and reject inactive/unlinked alternate folders with a corrective message.
- Combine PR45's contract-gated animation tooling and PR46's transfer research/read-only Legacy diagnostics. Native donor gameplay and the in-game transfer portal remain unfinished; no executable patches or game assets are included.

## Unreleased — donor header and allocator protocol follow-up

- Assemble owned CH motion components from the observed NBA11 ELF family using explicit fingerprint-bound authoring metadata and event contracts; reject unresolved dependencies.
- Add a bounded offline resident ownership model with leases, delayed release, rollback, readback and allocation quarantine; no native hook is installed.
- Add a revision-guarded Ghidra allocator-wrapper instruction harness and read-only 300-Hz auxiliary selector-curve inspection.
- Document actual signature-bank dependency/footprint findings and the remaining source-adapter, metadata, auxiliary and native lifecycle work.

## Unreleased — native target residency preparation

- Audit full registered CH motion track extents with `inspect-shot-registration --motion-extents`.
- Prepare bounded CH-backed resident images retaining authored metadata and validating native pointer relocation and inverse relocation.
- Reserve resident-image space in registration allocation plans; reject virtual load-memory collisions in addition to occupied file padding.
- Document the separate stock-backed resident registration probe and remaining donor metadata/loader/runtime work. No donor installation or executable patching feature is added.

## Unreleased — authored-key sampling and donor registry

- Sample NBA11 authored motion keys on demand with canonical-bind checks, full extent validation, input invalidation and a byte-budgeted payload cache.
- Inspect signature collections and cross-bank typed dependencies, preserving unknown metadata and reporting native group-member selectors.
- Add four explicit trajectory-cache event correspondences; unsupported events remain blocked.
- Document observed corpus results and remaining native registration, header, event and memory dependencies. No playable animation port is claimed.

## Unreleased — canonical animation bind and registration audits

- Verify the observed CH/NBA11 21-bone bind and preserve declared channel masks during packed pose conversion.
- Add read-only bind and shot-registration CLI audits; validate stock rows, known consumers and native label initialization.
- Inspect additional native payload reads without enabling unproven event conversion; provide an explicit three-marker mirror-selector contract.
- Document the separate registration-only probe and full observed-family component preparation. No playable donor port or executable patching is added to the editor.
## Unreleased — native-only transfer continuity and Legacy diagnostics

- Add read-only Legacy recruiting diagnostics for confirmed recruit metadata, native preference weights and unresolved fields, using immutable background snapshots.
- Trace annual recruit regeneration, native commitment, player-to-recruit copying and reusable-player-pool lifetime hazards.
- Require in-game transfers to retain player statistics and historical team associations; no editor/save-applied transfer workflow or playable portal is added.

## Unreleased — native recruiting pool audits

- Add read-only `inspect-recruit-pool` with native table bounds, metadata diagnostics, interest-list ownership checks and optional serialized recruiting-component inspection.
- Establish native dual-list persistence layout and identify the rollover conversion that transfers must bypass to preserve player identity/history.
- Preserve all original data. Playable pool insertion, binding persistence and native signing integration remain unfinished.

## Unreleased — transfer recruiting policy foundation

- Add offline transfer class/redshirt labels and reproducible three-priority school ordering for playing opportunity, hometown proximity or team ranking.
- Trace existing HS/JUCO class and recruiting-preference formatters, distinguishing recruit fields from college-player class/eligibility and team ranking from recruit ranking.
- Preserve originals; native pool insertion, persistence and executable integration remain unfinished.

## Unreleased — Legacy transfer feasibility research

- Document confirmed transfer candidate gates, ranked destinations, 400-entry active queue, existing transfer menus and serialized pointer relocation.
- Assess scoped frequency tuning and a recruitable portal while identifying unresolved calendar, scholarship, recruiting and save contracts. No executable or editor behavior changes.

## v1.21 — animation event bridge and team asset selection

- Add bounded CH/NBA11 event-table inspection, known category-payload-word reads and NBA11 membership-pair inspection.
- Add a separate CH event-table writer requiring an explicit research mapping contract; retain exact time bits, duplicate markers and order, and block unknown payload schemas.
- Document native marker consumers, complete identified-family event audit and remaining semantic/runtime dependencies. No playable donor animation or new controls are claimed.

### Team asset selection correction

- Check existing available team assets by default; leave missing or inactive categories unchecked.
- Show the original team Asset ID in the target box; keep default checks out of change plans and support explicit selected-team cloning.
- Mark shared stadiums, uniforms and menu logos with an asterisk and peer team names, including mixed classic/modern asset routes.
- Preserve existing assignments when clearing checks and reset pending clone intent on refresh.

## v1.20

- Save edited community rosters to overrides; copy selected-team activation/asset assignments between roster sources with review and editor undo.
- Place Team Assets above Research/Diagnostics; audit public paths/credentials and remove unreferenced legacy artwork.

- Add searchable team assignment matrix, visible IDs and per-category expansion checks.
- Apply independent stadiums, five uniform banks/SELU pairs and menu logos to overrides and normal JB builds.
- Clone missing enabled alternates from Home during build preflight and log each fallback.
- Correct numeric stadium routing; preserve classic classification and shared original arenas.
- Preserve existing selected overrides, support new assets in previews and reject stale/checksum-mismatched plans.
- Remove obsolete hidden alternate writers/CLI branches; maintain native evidence and workflow docs.

## Scorebug research follow-up

- Add bounded read-only native popup descriptor inspection and malformed-input tests.
- Document queue priority, update heartbeat and formatter limitations.
## Unreleased — uniform solver shape correction

- Adapt native stretch/bend distances when importing edited garment positions,
  preserving authored prestrain, response bytes and particle bindings.
- Modern-fit-2 corrects the previous rest-only preset and retains all necklines,
  builds and aggregate/individual routes. Document confirmed native model routing.
- In-game appearance still needs testing; no source JB or EBOOT is modified.

## Unreleased — adaptive animation timing/root conversion

- Decode the observed NBA11 byte-delta timeline and resample pose channels to
  fixed CH ticks with native key preservation, SLERP and bounded quantization.
- Translate optional6/8-byte root tracks; protect all inputs and distinct outputs.
- Audit the broad observed motion pools and all112 original jump-shot mappings.
  Complete banks, events/auxiliary tracks, bind retargeting and additive native
  shot registration are not implemented or claimed gameplay compatible.

## Unreleased — native packed-pose translation

- Translate the observed NBA11/CH2K8 packed quaternion selector convention with
  exact preservation of remaining stream bits, translations and padding.
- Add a bounded packed-frame CLI, source protection and conformance regressions.
- Trace additive jump-shot requirements: native112-record playback table and
  UI cap. No stock replacements, new registered shot or gameplay port claimed.

## Unreleased — executable-held motion investigation

- Add bounded read-only native ELF motion-header inspection for the observed
  CH2K8/NBA 2K11 full-body family, with explicit incomplete-library/import status.
- Document Ghidra-confirmed CH pointer/group selection and the gap between archive
  inventories and executable-held motion. No gameplay port/control change.

## Unreleased — pending updates and native animation inspection

- Consolidate pending Legacy-save, override, face, NBA reader, scorebug and
  uniform-editing updates, preserving their limitations and branch ancestry.
- Resolve 21 native animation bank names and classify them in Explorer.
- Fix inventory skipping banks above 10,000 records; include 2K14's main bank.
- Add bounded native motion-envelope/collection and local alias-link inspection.
- Document Ghidra input/animation routes. No donor gameplay port or new controls
  are represented as implemented or runtime tested.

# Unreleased — merged override compatibility audit

- Verify PR #30 retains the v1.16-v1.19 feature history and existing regression suite.
- Add regression coverage for numeric/named override folders, DDS priority, legacy record aliases and opaque BIN relocation without changing existing import policies.
# Unreleased — player-face research

- Document the seven dedicated College Hoops likeness slots, generated-face routing, paired texture/preset banks and cross-game conversion limits.
- Add a read-only face inventory command with synthetic bounds/family/preservation checks; no face editor or EBOOT changes.
# Unreleased — NBA 2K11 donor research

- Read the observed v3 SDAT variant with version-specific key selection and retained authentication; keep SDAT output blocked.
- Document actual NBA 2K11 asset/animation samples and donor suitability ratings; no gameplay, face or animation port implemented.
## Unreleased — native scorebug text contracts

- Reject misaligned SCNE text/property tables that native vector loads cannot read
  as intended, even when Python parsing succeeds.
- Add bounded native text `max_width` edits, preserving literal/alignment flags
  and the authored property type. Keep private executable experiments separate.

## Unreleased — scorebug test05

- Remove HUD dividers and relocate obsolete depth masks away from the new layout.
- Restore authored palette vertex values; retain enlarged logos and clock/score
  sizes. Center popup text, restore its alpha and align its black backing.
- Use one native sixth-man label; move native title-case branding to the bottom
  bar's default-text route. Enlarge all 19 live meter segments within the header.
- Add bounded native text alpha/RGB editing and count-only label-loop suppression.
- Correct earlier live-team-name claims: native normal-game callbacks suppress
  names. Owner chose to retain read-only EBOOT and leave names unresolved.

## Unreleased — native test04 startup correction

- Replace the experimental duplicated compressed English heap with a single
  uncompressed localization resource at offset zero. Preserve old translations,
  resource metadata, NAME trailer and native title-case branding ID.
- Reject localization compaction when unknown prefix bytes or other resources
  could be moved. Add regressions for the native direct-read descriptor contract.
- Record user-provided startup crash evidence and the remaining runtime uncertainty.

## Unreleased — test04 native branding follow-up

- Route title-case College Hoops / Reborn through the existing native label renderer
  using an isolated tagged English literal ID and matching clock font/style values.
- Guarded English loc-system extension preserves every existing token/ID/sentinel;
  recognize the researched TXT loc-system type and validate independent IFF growth.
- Preserve the native sixth-man visibility contract; the small left label now uses
  native-glyph artwork. No executable/font-bank hook or gameplay certification.

## Unreleased — scorebug test04

- Bounded native SCNE font-style inspection and edits, with independent live text
  callback names and preserved scene/bone references.
- Local test layout connects live school names, selects larger native font styles,
  uses narrow gray separators and opaque popup/header backing, and changes branding
  to title case with native glyph/color/shadow artwork. Exact live-font rendering
  remains unresolved; no new runtime/executable hook is implemented.

## Unreleased — scorebug test03

- Bounded HUD part ranges, ordered edits, shear removal, uniform vertex RGB and
  authored text basis scaling with translated-marker preservation.
- Native FONT glyph artwork composition using recorded bearings/advances and
  coverage, without installing substitute fonts or modifying the font bank.
- Documented local test03 layout: continuous backing/panel joins, adjusted logos,
  palettes, sixth-man enclosure, message backing and native static lettering.
  Runtime placement remains for user testing; no new application release.

# Unreleased

- Add bounded experimental authored HUD geometry/UV/color/text-anchor editing and sixth-man/text inventory.
- Document scorebug test02 corrections and runtime boundaries; derived user-test assets remain local, not distributed through Git.
## Unreleased — combined executable experiment correction evidence

- Document native property alignment and marker-identity defects in the broken
  prototype; keep the prior multi-variant result explicitly historical.
- Record one private combined candidate with native stats parsing, conditional
  backing and retained arc/transfer experiments. No patching is added to the tool.
- Record static checks and runtime acceptance limits without claiming visual QA.

# Unreleased — executable modernization research

- Record owner-authorized private experimental copies for modern NCAA arc/corner
  scoring, native HUD names and new-transfer sit-out assignment; maintain immutable
  originals and document unverified runtime/packaging limits. No editor patching.
- Document verified generated-fixture/cache/review-checkout cleanup and the blocked
  historical-package deletion; retain current regression source coverage.
- Document read-only CameraMenu, Game Rules, replay, indicator and autosave routes;
  rank practical modernization candidates and reject unsupported constant guesses.
- Carry forward the native scorebug name-fallback evidence from separate PR #32
  while preserving the owner's decision against executable changes.
- No runtime/editor feature, executable patch or release added.
## Unreleased — experimental uniform mesh editing

- Add source-aware editable OBJ uniform collections, guarded reimport and a modern-fit rest-shape preset in Models / Courts and CLI.
- Cover five necklines, three body builds and three shorts shapes across all 21 supplied cloth archives / 33 records.
- Preserve topology, UVs, unknown streams and native constraints; update matching SCNE/Clth rest positions only. Runtime fit remains experimental.

# v1.19

- Apply folder single-face cubemap compatibility consistently to Python manifests and paired CDF imports; preserve five base faces and report +X updates.
- Identify archive/role/magic for invalid IFF errors and provide targeted corrective advice without bypassing validation.
- Verify supplied frontend/legal overrides and complete halftime HDR cubemap using Python-only preparation/preflight; no real testing JB.
- Integrate modern-feature feasibility research PR #28. No gameplay/animation backport implemented.

# v1.18

- Integrate NBA 2K14 reading, detected NBA roster editors and split-header repair (PR #25).
- Add independent key/center-circle court reference guides (PR #26).
- Replace stale landing pages/matrix with current per-game documentation; add workflow, troubleshooting, testing and release guides. Preserve dated research in clearly labelled history.
- Remove obsolete pinned Windows dependency snapshot/unpublished beta draft; consolidate wrapper assertions into binary tests without reducing coverage.
- Include the complete documentation tree in Windows packages and maintain the generated cross-PC handoff.

## Unreleased — split archive headers and override error fixes

- Read and write header regions across source banks; support a TOC crossing 0A.
- Name damaged banks and expected/actual sizes instead of a generic incomplete-header error.
- Keep actionable override/build failure details and targeted repair advice in the GUI.
- Allow NBA2K14 override preview validation without enabling its unvalidated JB writer.

## Unreleased — NBA PS3 roster schemas and NBA 2K14 archive reading

- Read authenticated NPD v4 SDAT blocks and extended split-bank descriptors; keep SDAT JB writing blocked.
- Decode/re-encode strict ZLIB IFF blocks; read extended IFF pointer tables without unsafe rewriting.
- Detect College Hoops/NBA 2K9/NBA 2K14 roster payloads and expose verified per-game fields in side panels.
- Add NBA face, court, logo and language filename candidates and explicit roster asset references.
- Decode observed newer scene buffer/draw/instance variants and resolve separate court packages.
- Add read-only cross-game animation inventory and portability evidence; no animation port.

## Unreleased — additional court alignment guides

- Add a separate key/free-throw-circle and center-circle guide toggle using stock authored geometry, independent of 3-point/border guides.
- Keep guides raised, thin, flat-colored and separate from actual floor rendering.

## v1.17

- Auto-detect shared PS3 2K size32/size64 TOCs and preserve their layouts when rebuilding.
- Read optional game identity, retain College Hoops roster boundaries and shared source/override caching.
- Recover common internal CRC labels; support standard CDF TXTR hashes and half4 scene attributes.
- Add read-only NBA 2K9 inventory/extraction tooling and supplied-copy extraction/preview evidence.

## v1.16

- Faster sequential rebuild verification and persistent relocation bank handles.
- Single-read source preconditions; avoid redundant CDF partner reads.
- Fix CLI rejection of manually chosen JB output folders.
- Verify copied non-bank files, preserved bank padding and generated headers.
- Remove DDS preflight temporary folders on success/failure; check free disk space.
- Include queued song imports, manual output folders and opaque archive-gap fixes from PR #22.

# Unreleased

- Queue multiple song WAV imports, review/remove pending edits, then save combined
  music banks and global.iff once; retain pending edits on cancellation/failure.
- Choose the JB destination on any drive, with source/overwrite/link guards and
  transactional cleanup preserved.
- Preserve opaque archive header gaps during replacement growth; reject only
  newly consumed/relocated unknown bytes rather than all nonzero gap bytes.
- Correct roster research anchors/uniform bit coverage; audit arena-team backlinks.
- Add read-only scorebug record/part/texture discovery and evidence documentation.

# v1.15.4

- Parallel CPU/RAM-bounded override preparation, completed-archive reuse, cheaper
  conversion-cache maintenance, deterministic outputs and cancellable workers.

# v1.15.3

- Fix frontend menu override imports misclassifying header-relative geometry as
  texture data; preserve inline/GPU buffers and retain real overlap validation.

# Unreleased roster / game-line / motion continuation

- Traced the shared 65,535-unit text descriptor bound; block count overflow and
  remove Qt's unintended 32,767-character truncation.

- Live orange warnings beyond verified UTF-16 keyboard entry capacity.
- Authored 3-point/outer-border layers, source court supplementation, retained camera.
- Guarded conference indices and exact conference-logo texture editor shortcut.
- Corrected tournament-link semantics; unvalidated bracket editing protected.
- Bit-accurate unresolved-byte coverage and lossless SingleMoCap inspection/export.

- Dynamic UTF-16 edits no longer confuse keyboard entry capacities with engine storage ceilings.

# Roster and arena continuation

- Twelve additional confirmed appearance/tattoo/signature fields and all jump-shot captions.
- Authored arena vertex colour/alpha, secondary UV lightmaps, glow and flare masks.
- No guessed secondary positions or unproved palette assignments.

# Uniform lettering continuation (PR #13)

- Authored indexed font decoding, front/back numbers 0–99/00 and curved Reborn surnames.
- Roster-linked or preview-only number selection; source/override glyph consistency.
- Correct sampler/bool uploads and declared material DiffuseColor.
- Confirmed palette 16/17 school-colour runtime-copy labels.

# Change log

## Unreleased — roster / preview continuation

Named SCNE source switching, worker source snapshots, comparison reference guards,
confirmed school text capacities and jump-shot animation ID editing. Nested menu
logo records show school ownership; stadium labels use arena references.

## Unreleased — single-slice DDS replacements

Allow a 2D DDS replacement for dimension-3 TXTR descriptors whose stored depth
is exactly one, preserving the original descriptor. Deeper volume textures stay
blocked.
## v1.12 — roster scale and preview source checkpoint

Inline ratings, atomic multi-player ratings paste, source-bound CSV and selective
roster comparison; school filtering, Class/Redshirt controls and growing text
storage. Shared source/override previews, archive categories/references, bounded
conversion cache and concise GUI build summaries. This is in-progress work;
remaining engine limits and shader/number routing are documented, not claimed
complete. Comparison review uses a table model for large change sets.

## v1.11 — record side panels and previews

Side editors for every category; integrated palettes, footwear and jersey preview.
Safe player school assignment and 18-slot/count-aware roster handling, including
real player row zero. School shoe brands propagate to that school’s roster as one
undo step. Combined top/shorts preview with neck/build/cut dropdowns. Removed Edit
selected, Team palette and shoe toolbar actions; no alternate assets added.

## v1.10 — roster editing cleanup

Readable height/positions, visible Player/Ratings/Scholarship editor tabs, verified
scholarship flag editing and named equipment. Schools combines duplicate views.
Removed separate properties/attributes and D1/alternate/independent-asset actions;
conference realignment remains. No alternate assets added. Full Windows package
includes the established LGPL audio codecs and corresponding source notices.

## Unreleased — reviewed audio GUI continuation

Fix scene/shoe navigation after Audio insertion; clean-clone converter tests use
synthetic fixtures. Batch WAV exports publish atomically and remove incomplete
batches on cancellation/failure.

## Unreleased — LGPL audio package

Build a restricted FFmpeg CLI from pinned upstream source with GPL/nonfree
components disabled, ship corresponding FFmpeg/AtracDEnc sources and notices,
and include both audio helpers in the standalone Windows GUI. Windows CI run 54
built the package and passed the frozen synthetic WAV round trip on the current
PR head. ATRAC PCM input now accepts finite samples through Â±4.0, matching the
encoder's 1/4 input scaling and avoiding rejection of over-range floating WAVs.
Song replacements are trimmed or silence-padded to the selected track's original
sample length.

## v1.08 audio development bundle

Experimental WAV/audio-bank/AUDO/jukebox-art CLI, unchanged-WAV checksum skipping,
sample-extent checks, portable setup and shared Codex PR/documentation workflow.
Experimental Audio workspace adds separate Licensed Music/Fight Songs tabs, WAV
export/replacement preparation and mapped cover-art actions. Song-name editing
remains unavailable. No emulator or testing JB.

## v1.07

Community roster ZIP/rating fixes, packed player/team shoe editing, game roster
IFF export and declared 2D stored-depth compatibility. Source inputs preserved.

## v1.06

Reusable single-surface court preparation and automatic non-stadium base texture
normalization. Dynamic supported stadium sizes retained; runtime budget unknown.

## 1.0b0 development (Git tag v1.0beta reserved, not created)

Native Qt studio; streaming cancelable raw extraction; precomputed IFF spans; replacement-folder staging and source preconditions; verified unpatched build bytes; roster redo; source/packaged smoke tooling. CI branch deletion/release side effects removed. Historical higher-looking version tags remain untouched. This is a new rebuild train, not a replacement of preserved releases.

Override selection fix: automatically choose a fresh numbered workspace when the configured folder exists; update build and preview paths together. Rename the GUI action to Select overrides folder… and remove staging wording from GUI messages. Preserve previous workspaces on failure.
Continuation: optional stock-court alignment guides default off and leave floor shader/palette rendering intact. Correct ROST runtime UTF-16BE string fixup, protect the 65,535-unit descriptor count, and remove Qt’s unrelated input ceiling.

v1.14: direct jersey, shoe and stadium/floor selectors use Source JB or selected overrides without manual IFF opening. Jersey selection initializes the mesh; stadium modes choose combined, floor or arena. Source switching reloads the active direct preview.

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
