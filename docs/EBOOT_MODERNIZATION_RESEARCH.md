# College Hoops 2K8 executable modernization candidates

Follow-up: the owner subsequently authorized separate local experimental copies
for three specific changes. [Experiment 01](EBOOT_EXPERIMENT_01.md) records the
new scoring/transfer findings, private prototypes and unverified runtime limits.
The original executable remains unchanged and the editor has no patching feature.
The read-only investigation below is the earlier research record.

Read-only investigation, 2026-10-19. Target: the supplied **PS3 College Hoops
2K8** executable. Addresses below are virtual addresses in this particular
decoded ELF, not portable file offsets or a patch for other game revisions.
No executable, source game, overrides or savedata was changed. No emulator was
launched. This document identifies candidates; it adds no editor feature.

## What is closest to a small update

The best executable candidate is restoring native scorebug team-name output.
Camera customization and broadcast transition controls are useful next targets,
but their complete setting-to-renderer contracts still need tracing. Modern
rules, animation blending and AI are not established as small constant patches.
Many visual improvements can already use asset/data consumers without changing
the executable at all.

| Update | Evidence / route | Effort and confidence |
| --- | --- | --- |
| Native school names beside scorebug logos | Registered home/away city providers have a normal-game suppression path and an existing team-name fallback. Two branch sites are identified below. | Smallest identified executable candidate; high static confidence in the route, no runtime validation. Owner explicitly declined applying it; names remain unresolved. |
| More readable broadcast text, title-case branding, larger scores/clocks, less intrusive framing | Existing native style/localization and authored scene paths are described in scorebug PR #32. These consumers already exist in EBOOT. | High practicality through assets; executable patch usually unnecessary. PR #32 is separate, unmerged work with remaining user-test issues. |
| Modern broadcast branding, replay wipes and watermark artwork | Named replay scene resources reach native selection code. Replace compatible artwork first; preserve replay/event logic. | Asset changes are closer than logic changes. New timing controls require tracing the fields consumed by the update/draw routines. |
| Additional camera presets or more useful camera adjustments | Named CameraMenu registration reaches handlers using 44-byte records, bounded selection and multiple option paths. | Promising bounded research. Not yet a verified FOV/zoom/height patch or proof that hidden camera modes are safe. |
| Optional HUD indicator simplification | An indicator resource is referenced from native code; scorebug/meter routes are already mapped. | Candidate only. Identify individual draw/visibility consumers before disabling anything. Do not disable a whole update routine to hide artwork. |
| Contemporary shot selection and signature assignments | Confirmed roster ratings/tendencies and existing animation selectors already have data consumers. | Practical data presets; no executable change required. They influence the old engine and do not install modern tactical AI. |
| Shorter presentation interruptions / replay pacing | Replay selection initializes named resources and several float fields. Popup and replay paths are identified. | Medium research. A float near a replay name is not yet a proven duration in seconds; event completion and state transitions must be preserved. |
| Contemporary rule presets | Named Game Rules menu has mode-dependent initialization paths. | Medium/high investigation, not yet a safe shot-clock, reset-clock, foul or scoring-distance patch. Trace actual simulation and saved settings consumers. |
| Autosave convenience | Separate AutoSaveMenu and AutoSaveMenu_EndOfGame registrations plus autosave scene names exist. | Not currently an easy patch. These establish UI routes, not save scheduling or atomicity. Avoid changing save behavior from UI evidence alone. |
| Framerate, bloom, modern lighting | Bloom/profiling/shader labels occur, but no complete adjustable render contract was established. | No proven quick patch. A frame-cap edit may affect timing; a shader name does not prove a safe global toggle. |
| Smoother modern gameplay, motion matching, new collision/AI, entire newer animation libraries | No compatible replacement runtime is established by this executable scan. | Major engineering; not a small EBOOT modernization. Donor clips still require track, skeleton, event and consumer compatibility. |

“Small” describes the size of a possible code change, not a guarantee of PS3
compatibility or lack of side effects. No candidate in this table is gameplay
certified. Do not quote a precise implementation time before the missing consumers
are understood.

## Confirmed executable routes

### Native school-name restoration

The prior scorebug investigation in [PR #32](https://github.com/ZMO34/CHoops-Extractor-Reborn/pull/32)
identified the `home_city` and `away_city` providers at `0x4EF9A4` and `0x4EFABC`.
Normal-game helper paths at `0x4EED80` / `0x4EEB3C` report success without filling
the text buffer; conditional branches at `0x4EF9F0` / `0x4EFB08` then bypass the
fallback. The existing fallback through `0x4EF92C` reads the current team's name
at team-object offset +4. Registered score/period/clock bindings are associated
with `0x4EF400`; the bottom-HUD dispatcher is `0x4F442C`.

This provides a concrete alternative to painting names onto team logos: allow
the existing fallback to supply live text. It is still a proposal, **not a patch
included here**. Long names, localization, special modes, layout clipping and
buffer contracts need review. The owner chose to keep EBOOT read-only and leave
names unresolved. This research does not change that decision.

Native style loading at `0x6A8A8` already handles font/color/alpha/shadow/literal
properties. Scorebug PR #32 demonstrates why readability and branding should first
reuse those authored properties. Its sixth-man meter route at `0x76A714` includes
19 material draws; the popup/backdrop route at `0x4F1620` is a future entry point
for conditional backing/placement research, not permission to suppress events.

### Camera menu: bounded records, not a discovered FOV constant

The `CameraMenu` registration points to an event table at `0x8AF198`.
Event keys 6 and 7 resolve through function descriptors to code at `0x4C0C58`
and `0x4C04A0`. The latter is a short forwarding handler; the former performs
selection and option updates. Adjacent helpers use record stride `0x2C` (44
bytes), selection checks involving `0x1D` / `0x1E`, and option indices through 6.
These observations describe storage/control bounds; they do not establish 30
distinct gameplay cameras or seven independently usable camera settings.

The record/state pointers `0x12C75498` / `0x12C759EC` refer outside the initialized
file-backed ranges used in this scan. Runtime initialization must be found before
claiming their defaults are present as a writable static table. The handler at
`0x4C11C4` loads 35.0 and subtracts it from a derived value before storing a float.
It is in camera-menu logic: **it is not evidence for a shot-clock constant**.
Zoom, height, FOV, UI position and camera identifiers must not be guessed from
those numbers. Trace the initialization and `0x4A25A4` consumer before a preset
writer or relaxed bounds is designed.

### Game Rules: several mode-specific paths

The `OptionsMenu_GameRulesMenu` registration is at `0x9EEEA0`, with event-table
pointer `0x94439C`; associated callback `0x6C0B2C` dispatches across several
conditions. It calls `0x4A0A34` and `0x4A3924`, then selects paths including
`0x6BF5B0`, `0x6BF72C`, `0x6BFA5C` and `0x6BFE60`, or returns/delegates elsewhere.
Mode numbers have not been assigned dynasty/exhibition names in this research.

This is useful for following rule controls, but changing a menu maximum does not
prove that the live game, reset events, simulation, overtime and saved settings
all agree. Next trace one named rule from localization/menu control to storage,
then from storage to live clock/scoring logic and save loading. A changed court
texture or preview guide cannot change the scoring boundary.

### Replay, indicators, saves and rendering labels

| Evidence | Confirmed meaning | Remaining consumer work |
| --- | --- | --- |
| `0x2149E8` selects `replay_wipe_2k` / `cameraShape1`; references at `0x214A9C` / `0x214AB0` | Native replay resource selection/field initialization | Follow field reads before assigning duration/transition semantics. Preserve completion and return-to-game behavior. |
| `0x214C6C`, reference at `0x214D7C`, names `replaywatermark_pontiac` | Watermark resource route | Locate exact destination artwork/layout and retain unrelated replay state. |
| `0x7DB50`, reference at `0x7DD14`, names `replayoverlay` | Replay overlay resource route | Separate visual replacement from replay scheduling. |
| `0x584EAC`, reference at `0x584F7C`, names `gameintro_cameras.iff` | Intro camera archive consumer | Does not establish gameplay-camera compatibility or a decoded camera track. |
| `0x72532C`, reference at `0x7262C0`, names `indicator` | Indicator resource reference | Individual HUD elements and visibility conditions unresolved. |
| AutoSaveMenu / AutoSaveMenu_EndOfGame registrations use tables `0x8A32C4` / `0x8A325C`; `0x11D5D0` references `autosave_%02d` | Save UI/scene evidence | Save serialization, completion, error handling and trigger schedule unresolved. |
| `Ambient:Shot-Clock` referenced at `0x539438` | Named audio event | Not the shot-clock simulation setting. |
| FrameBufferEffect_DrawBloom / bloom shader labels | Render-related names | No validated global bloom toggle, frame cap or timing patch. |

## Method and reproducibility

The local scan used Python 3.12.14 and Capstone PPC64 big-endian disassembly on
the owner's decoded ELF, opened for reading only. A digest before/after the scan
matched. No executable bytes, proprietary disassembly listing, input fingerprint
or asset are distributed in this PR.

1. Parse ELF64 program headers to translate virtual addresses through file-backed
   PT_LOAD ranges. Reject unmapped/BSS reads; do not assume every VA is file offset
   plus a fixed constant.
2. Collect relevant ASCII / UTF-16BE labels, then find aligned address references
   and descriptor registrations. The bounded vocabulary scan collected 580
   candidate strings and 75 TOC references. These are search results, not a full
   executable map, feature count or exhaustive reference inventory.
3. Decode the actual OPD section from the ELF section headers: virtual range
   `0xA082B0..0xA4CAC8`, file range `0x9F82B0..0xA3CAC8`. The earlier broad scan
   window extended into adjacent data; the experiment follow-up tightens this
   bound and validates TOCs instead of accepting nearby pointer-like words.
   Select each function's actual TOC. Main game routines commonly use `0xA64A94`,
   while another group uses `0xA54AC8`; using one TOC universally gives false
   string/constant annotations.
4. Follow named registrations to callback descriptors, then inspect code paths,
   bounds, callers and consumers. PC-relative/direct references, dynamically
   computed pointers and runtime initialization may require additional tracing.
5. Distinguish resource labels, profiling labels, menu controls and simulation
   state. Record hypotheses separately. A string match or nearby numeric literal
   is not proof of gameplay semantics.

This procedure can be repeated in Ghidra with the matching ELF mappings and PS3
function descriptors/TOCs. Ghidra was not installed or run for this scan. Donor
recompilation output is not a replacement PS3 executable and is not evidence that
an executable modification will run on physical hardware.

## Proposed next work and compatibility gates

First finish asset-based broadcast fixes independently of executable research.
If the owner later authorizes an executable prototype, the native-name fallback
is the most narrowly identified first experiment. Camera record initialization
and replay field consumers are the next useful read-only investigations. Rules
research should follow one real setting end to end rather than globally replacing
every matching integer.

Any eventual patch system needs revision/digest matching, exact expected-original
instruction checks, instruction-aligned edits, rejected mismatches, explicit
feature scope and rollback to an immutable original. Branches must respect PPC64
register, LR, stack and TOC contracts; hooks additionally need valid branch range,
allocation, relocation and instruction-cache handling. A byte diff can prove the
written scope, but not the complete runtime effect of a changed branch.

Keep executable patches separate from archive/roster overrides. A PS3 ELF must
also be packaged into a loader-compatible SELF under the user's target firmware;
emulator acceptance alone cannot certify that. Actual PS3 behavior, saved-game
compatibility, gameplay transitions and longer sessions remain user-run acceptance
work. Do not claim backend isolation without tracing dependencies and testing.
No patch framework, hook, altered EBOOT, release or testing JB is delivered here.
