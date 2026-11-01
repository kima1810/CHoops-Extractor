# NBA 2K11 PS3 as a College Hoops 2K8 donor

Read-only assessment, 2026-10-18. Scores are engineering judgments about useful
results achievable through asset conversion, not measured gameplay improvements.
No assets have been ported, no EBOOT changed and no RPCS3/gameplay test performed.

**Overall: 8/10 for visual/audio donor material; 6/10 for animation conversion
research; 1/10 for copying newer gameplay systems.** 2K11 offers more identified
animation resources than the inspected 2K9 source, but is not established as a
closer structural match. 2K9 remains the simpler first animation compatibility
baseline; 2K11 is a valuable next comparison rather than a full-library swap.

## Ratings by update

| Desired update | Candidate rating | Conversion difficulty | Evidence and practical route |
| --- | --- | --- | --- |
| Court artwork, logos, signage | **9/10** | Low–medium | Resolved 85 floor names and 216 logo names. Floor `f030.iff` decodes two preview meshes without warnings. Eleven floor entries are 32-byte empty stubs, so names alone are not proof of useful artwork. Re-author/bake for CH UVs/materials and respect its base texture budgets. |
| Uniform and shoe artwork | **8/10** | Medium | Resolved 138 UA + 138 UH names and nine shoe names (not a complete shoe inventory). Sample uniform DXT5 1024×512, L8 number atlas 1024×128; shoe DXT5 128×128 and DXT1 256×256. Extracted formats are readable. Keep CH cloth/neck/shorts bindings and adapt artwork/number masks; sampled uniform SCNEs are not decoded CH-style mesh replacements. No new alternate assets added. |
| Arena detail/atmosphere | **7/10** | Medium–high | Fifty named stadium entries. Sample `s734.iff` has an arena with 22 parts / 52 textures; 21 parts decode for static preview with one unsupported UV declaration. Reuse signage and selected adapted props before attempting a whole arena. Lighting, palette/material bindings, collisions, scales and memory remain destination constraints. |
| Faces and hair | **6/10** | High | 1,040 resolved PNG player-asset names. Sample `png0349.iff` contains two head SCNEs and five TXTRs plus unresolved records. Bench mesh decodes; high-detail mesh declaration is not supported. Sample head header +0x4C values 18/7 differ from CH 12/7. Match UVs, bones, skinning, facial motion and both LODs. CH's seven dedicated likeness slots/shared FaceGen routing still limit independent assignments. No drop-in cyberface port established. |
| UI/scorebug artwork and presentation styling | **6/10** | High for live layouts | `gamedata.iff`, `frontend.iff`, `global.iff` and `jukebox.iff` parse; familiar SCNE/TXTR/LAYT families exist. Some UI vertex declarations are unsupported. Artwork can guide a CH redesign; score/clock/team-logo/message bindings must remain CH-specific. Do not transplant an entire HUD bank expecting its live logic to work. |
| Sound effects and arena audio | **8/10** | Low–medium | 1,060 identifiable AUDO records; sampled global effects use the known 36-byte ATRAC3 headers at 48 kHz. One stereo sample decoded to PCM16 WAV (43,008 frames). Convert through WAV into existing CH slots; loop flags, triggers and commentary timing require their own checks. No complete 2K11 jukebox/song catalogue or PA event mapping claimed. |
| Celebrations, intros and crowd clips | **6/10** | High | Identified SingleMoCap records include global/crowd and other banks. Prefer one low-interaction clip for a converter study. References, track masks and timing differ; events and triggers must be mapped. No new clip currently plays in CH. |
| On-court dribbling, movement, shooting, contact animations | **6/10 research value; 2/10 direct-swap readiness** | Very high | 4,705 identifiable SingleMoCap records, versus existing inventories of CH 319 / 2K9 904 / 2K14 7,460. Samples include 56/64-byte reference-like and longer packed records. Bone mapping, rotations, root motion, ball/hand contacts, events, clip lookup and selection/blending must be decoded. More clips alone cannot supply smoother gameplay. |
| Roster data / tendencies / playbooks | **4/10 research value** | High | `roster.iff` decodes a 2,692,320-byte ROST with marker 0x225, distinct from current 2K9 0xD1 and 2K14 0x235 profiles. No 2K11 roster writer enabled. Use already confirmed CH ratings/tendencies for curated authoring; do not reuse NBA offsets or assume NBA tactical logic fits a college roster. |
| AI, physics, controls, animation blending engine | **1/10 as an asset donor** | New runtime implementation | Assets do not transfer the code that chooses/blends moves, coordinates contacts, interprets controls or runs AI. Under the current read-only EBOOT boundary, these are not file-copy updates. |

## Actual inspection and extraction access

The supplied copy has four banks, **6,974 TOC entries**, 72-byte descriptors and
the existing size64/hash32/sector32 TOC. Banks 0A/2A use NPD **version 3**, flags
0x0100003C; 1A/1B are ordinary banks. The existing reader previously accepted
only v4. It now chooses the v3 wrapping key for this observed variant while
retaining header and per-block authentication. No flag, integrity check or writer
guard is relaxed. SDAT/extended archives remain read-only.

The version-specific wrapping-key selection follows the primary format
implementation in [RPCS3's unedat.cpp](https://github.com/RPCS3/rpcs3/blob/master/rpcs3/Crypto/unedat.cpp)
and [key_vault.h](https://github.com/RPCS3/rpcs3/blob/master/rpcs3/Crypto/key_vault.h).
Only source code was consulted; the emulator was not launched. The v3 branch uses
the older wrapping key while v4 retains its previous key. Versions other than
3/4, compression/debug flags and other unknown combinations stay rejected.

Authenticated sparse reads passed at beginning/interior/end and across block
boundaries in **both encrypted banks**. Complete header inventory found 3,511
standard IFF signatures and 99 CDF-backed metadata signatures; no standard-IFF
header traversal errors. Of the outer names, 1,936 currently resolve; the rest
remain hashed rather than receiving speculative labels. The 3,120 flagged H7A
resources were not all interpreted as IFFs or assigned gameplay semantics.

Identified IFF records include **12,608 TXTR, 8,077 SCNE, 4,705 SingleMoCap,
1,060 AUDO, 44 AUSB, 476 LAYT and one ROST**. These are structural inventories,
not numbers of independent fully usable assets/clips. No old SKEL type was found;
that does not mean 2K11 lacks skeletons. Unresolved record types may contain
relevant dependencies and remain unclassified.

Selected PNG/uniform/shoe/floor/stadium/global/gamedata/frontend/jukebox/roster/
crowd and animation-bank blocks decompressed to declared lengths. The read-only
animation inventory returns 4,705 records, five sample prefixes and unchanged
source metadata. No track-to-pose decoder or round-trip animation writer exists.
Native preview gaps are explicit skips/warnings, not successful full rendering.

## Recommended order

1. Convert a floor/signage texture and a shoe/uniform artwork sample onto existing
   CH geometry, with a reversible asset diff. This is the best immediate payoff.
2. Evaluate one face donor against CH's dedicated-slot/FaceGen contracts; separate
   artwork from head mesh/skinning and account for shared CH normal maps.
3. Convert one audio effect through WAV and an existing CH event slot.
4. Decode one simple 2K9 clip, then the corresponding 2K11 family. Establish
   skeleton/track/timing correspondence before allocating effort to gameplay moves.
5. Study live HUD layouts and tactical data independently, using CH consumers.

These are next-step recommendations, not implemented ports or runtime-certified
features. Supplied inputs stayed immutable; extracted samples/reports remain local
and excluded from Git. No game/testing JB was created.

## Reproduce

After preparing the existing Python environment:

```powershell
python -m choops_py.research.animation_compat "PATH_TO_NBA2K11_JB" --output output/reports/nba11-animations.json
python -m pytest -q tests/test_sdat_2k14.py
```

The generic archive/extraction reader now accepts the observed v3 banks. This is
not general NBA 2K11 GUI/roster/build certification. Existing 2K8/2K9/2K14 reader
contracts and writer restrictions remain in force. Earlier face research's v3
access blocker is superseded by this authenticated-reader evidence; its face
conversion/assignment limits remain valid.
