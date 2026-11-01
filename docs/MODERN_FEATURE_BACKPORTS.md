# Modern-feature backport feasibility for College Hoops 2K8

Follow-up, 2026-10-19: [executable modernization research](EBOOT_MODERNIZATION_RESEARCH.md)
adds verified menu-handler/TOC routes and ranks small executable candidates.
Scorebug PR #32 has since traced live native name/style providers and developed
authored layout tooling; its normal-game name suppression remains unresolved
under the owner's read-only EBOOT decision. The older matrix below records the
2026-10-17 baseline and must not supersede that newer, separately scoped evidence.
No patch or new runtime feature is implemented by either assessment.

Research assessment, 2026-10-17. No gameplay feature, asset port, executable patch
or new alternate asset is implemented by this document. This targets **PS3 College
Hoops 2K8**, not an assumed interchangeable NBA 2K8 binary. Confidence below is
about the proposed technical route, not a certified in-game result.

## Meaning of direct and indirect

A data/asset route uses a consumer already present in 2K8: replace supported artwork,
change confirmed roster fields or assign existing animations. A converted port
needs donor decoding and destination re-encoding with equivalent bindings. An
indirect feature reproduces part of the experience in the editor or an external
workflow. A new engine feature requires executable/runtime logic, not just an IFF
record with a similar name. EBOOT remains read-only; no emulator is launched.

The [NBA 2K11 donor follow-up](NBA2K11_DONOR_ASSESSMENT.md) adds authenticated v3
archive access, actual resource samples and per-category ratings. It supersedes
the earlier 2K11 access blocker, not the requirement for conversion/consumer evidence.

Our supplied donor evidence now includes PS3 NBA 2K9, 2K11 and 2K14. No modern Gen9 asset
sample was inspected. PS3 2K14 must not be confused with PS4/Gen9 variants or taken
as a bridge that automatically makes present-day resources compatible.

## Candidate matrix

| Feature / desired result | Route | Evidence and missing work | Priority |
| --- | --- | --- | --- |
| Modern courts, uniforms, shoes, logos and arena signage | Re-author DDS for 2K8's existing materials; convert geometry only when layout/binding is understood | Existing overrides/preview/writers support known destinations. Newer SCNEs are not automatically compatible; preserve material semantics, alpha, UVs, numbers and budgets. Supported data path, runtime acceptance still unverified. | High |
| Contemporary broadcast scorebug and menus | Redesign artwork first; investigate authored SCNE transforms/layout bindings second | gamedata.iff has named scorebug scenes and textures. Node-to-score/clock/team-color bindings are unresolved. Re-skin is much closer than moving all live fields into a new layout. | High |
| Modern shot selection / perimeter-oriented roster identity | Batch confirmed ratings and four tendencies: close, mid-range, 3PT, drive | Current CSV/copy/compare tools can apply reproducible profiles. This can influence existing decision inputs; it cannot create a new spacing/rotation AI. Profile effectiveness needs user gameplay feedback. | High |
| Modern signature-style assignments | Assign existing jump-shot/free-throw IDs and supported appearance/body fields | 112 jump-shot IDs and free-throw IDs 0–21 have destination evidence. A familiar label does not add a missing move. Current capabilities can support curated profiles. | High |
| Newer shot, celebration or presentation clips | Decode/retarget/encode selected donor clips | 2K9 shares the older SingleMoCap envelope and is the better first donor. Bone order, tracks, timing, aliases, root motion/events and lookup consumers remain unresolved. Conversion research, no certified direct swap. | Medium research |
| More modern arena atmosphere | Replace supported signage/crowd artwork, existing music/fight-song slots; investigate presentation/crowd clips | WAV and artwork paths exist. Crowd placement, trigger timing and synchronization are separate dependencies. Arbitrary commentary or PA event insertion is not established. | High for artwork/audio; medium for animation |
| More modern lighting/material appearance | Re-author textures/lightmaps within established 2K8 shaders | Embedded Cg/prelit/lightmap evidence exists. PBR materials, new reflection/AO systems and modern shader graphs need translation plus runtime support and performance validation. More pixels alone do not produce modern lighting. | Medium |
| Modern playbooks, spacing and coaching tendencies | Locate destination play/tuning structures and their consumers before building an editor | No validated playbook/tactical writer is currently exposed. Old-engine tactics may be editable data, but adaptive modern AI is a different runtime system. Candidate research, not a confirmed port route. | Medium research |
| Contemporary rules, shot-clock behavior and 3PT distance | Trace rules/settings and scoring consumers read-only; distinguish artwork from logic | Court texture and alignment guides do not change collision/scoring/rule constants. No validated modern-rules data writer exists. Do not advertise painted lines as a rules update. | Research only |
| Transfer portal / NIL / richer dynasty management | Possible external roster-management workflow using supported exports | Current roster edits/guarded assignment are established, but dynasty/recruiting/save-state semantics and NIL finances are not. An off-season companion could approximate decisions only after save identity/progression is understood. Not native portal/NIL logic. | Medium concept |
| Badge/archetype experience | Editor-side named presets mapped only to existing confirmed ratings/tendencies | Feasible as an authoring convenience. Actual conditional badges, takeover meters and progression require destination systems; writing invented bits creates no behavior. | Medium indirect |
| Modern replay cameras / broadcast presentation | Inspect existing camera banks, markers, scene transforms and dispatch | Named gameintro_cameras/SingleMoCap records are discoverable. A camera path is not yet a decoded writable track and broadcast-event selection remains unresolved. | Medium research |
| ProPLAY / motion matching / modern contact physics | New runtime animation selection, pose matching, collision and interaction systems | No equivalent destination implementation established. Old compatible clips could improve variety, but cannot import the engine that selects/blends/coordinates them. | Outside current asset-only path |
| Rhythm shooting, new control mechanics, advanced shot timing | Runtime input and shooting logic changes | Animation replacement does not change input interpretation, timing windows or success logic. External remapping is not an implementation of the mechanic. | Outside current constraints |
| Modern online services / crossplay / live marketplace | Separate networking/service architecture | No compatible destination/service contract established; not an archive replacement task. | Out of scope |

## Most promising investigation sequence

1. **Modern gameplay profiles using known fields.** Establish a baseline export,
   define versioned per-player profiles, preserve identity and unknown bits, and
   produce a reversible diff. Use ratings plus the four confirmed tendencies;
   do not claim new tactical AI. User testing would measure pace/shot mix/turnovers
   and expose the old engine's behavioral ceiling.
2. **Broadcast artwork and live-node map.** Inventory gamedata.iff scorebug_bottombar,
   scorebug_topbar/blackbar/logo_bloom and relevant TXTRs, then trace score, period,
   clock, foul, team-name/logo and palette bindings without editing EBOOT. Separate
   cosmetic changes from geometry/visibility/animation changes. Prove one static
   replacement and preserving round trip before a complete new layout writer.
3. **Single-clip animation decoder, starting with 2K9.** Prefer a low-interaction
   presentation clip for structural study; do not start with contact dunks or a
   full motion-bank swap. Locate its skeleton and aliases, decode all tracks,
   reconstruct time/poses and compare encoded output. Even a celebration may
   depend on events, so classify missing dependencies explicitly.
4. **Old-engine tactical/rules discovery.** Survey named settings/play/tuning records,
   compare consumer accesses against known roster fields and document storage.
   No unverified playbook, hot-zone, shot-clock or physics editor should be exposed.
5. **Off-season companion feasibility.** First identify the actual dynasty save
   format and links to roster/recruiting/progression. Existing roster USERDATA
   support is not proof of dynasty compatibility. Keep any later external simulation
   explicit and reversible; do not add removed D1/alternate actions.

This ordering is a recommendation based on existing tooling and dependencies,
not a claim that research items have been decoded or performance-tested.

## Why animation counts do not establish compatibility

The existing read-only inventory found 319 / 904 / 7,460 identifiable SingleMoCap
records in CH2K8 / NBA2K9 / NBA2K14 respectively. They include references/aliases
and are not totals of all playable animations. CH2K8/2K9 samples share an older
envelope; 2K14 sample organization differs. Shared hashes and matrix bytes do not
prove bind pose, bone indices, frame units, events or gameplay lookup compatibility.

A converter needs: bone hierarchy/identity and scale; bind transforms; packed
rotation/translation decoding; timing/interpolation; mirrored/reference records;
root motion; ball/hand/foot contacts; event IDs; destination clip lookup and memory
requirements. Record extraction and decompression are the first steps only.
A move can decode correctly and still break gameplay synchronization.

## Modern feature reference and inference boundary

2K's official [NBA 2K26 gameplay announcement](https://newsroom.2k.com/news/nbar-2k26-debuts-new-gen-9-gameplay-improvements-including-an-all-new-dynamic-motion-engine-powered-by-proplay)
(31 July 2025) describes dynamic lower-body pose matching, changed shooting/control
systems, collision changes and an AI intelligence module. These descriptions
establish examples of modern runtime features, not their proprietary formats.
The conclusion that raw textures/clips cannot supply those systems is an
engineering inference from the runtime dependencies and current destination evidence.
It is not proof that executable reimplementation could never be attempted.
No broader claim about the newest unresearchable title is needed for this assessment.

## Local evidence and next acceptance gates

- [Animation portability](ANIMATION_PORTABILITY.md): donor envelopes/counts,
  skeleton cautions and repeatable inventory command.
- [Animation extraction](ANIMATION_RESEARCH.md): lossless record export only,
  no skeletal track decoder or BVH/FBX writer.
- [Roster semantics](ROSTER_SEMANTICS.md) and roster/schema.py: actual writable
  fields, bounds and packed-bit ownership. No independent CH2K8 secondary position.
- [Scorebug research](SCOREBUG_RESEARCH.md): named destination nodes/artwork and
  unresolved live routing. No geometry redesign writer is claimed.
- [Arena shaders](ARENA_SHADER_MASKS.md): embedded shader evidence and static
  renderer limits; preview guides are not game-rule edits.
- [NBA containers/rosters](NBA_ROSTERS_AND_2K14.md): per-game schemas and blocked
  SDAT rebuilding. Donor extraction is independent of donor rebuilding support.

For each future implementation require a bounded reproduction, confirmed consumers,
source-immutable decoding, destination reparse, untouched-range comparison,
ambiguity rejection and rollback. Engine/memory behavior remains uncertified
without user testing. This research launches no game, edits no executable,
builds no real/testing JB and distributes no donor assets.

## Transfer follow-up

[Legacy transfer feasibility](LEGACY_TRANSFER_PORTAL.md) now traces native candidate
frequency gates, ranked destinations, transfer menus and serialized queue relocation.
These improve the evidence behind a possible portal; recruiting integration and
higher rates remain unimplemented and gameplay-unverified.
