# College Hoops 2K8 player faces — read-only findings

## Result

The observed PS3 game has **generated faces and seven dedicated likeness slots**.
The roster chooses the latter with a four-bit selector, not a general NBA-style
cyberface file number. The original seven likenesses use the shared head/morph
system with dedicated color/normal textures and FRFG coefficient presets. This
is a concrete asset-editing route, but not proof that arbitrary NBA head IFFs can
be copied into the game or independently assigned to every player.

Original source archives, roster and EBOOT were read only. No RPCS3 or game build.
No face editor/writer or automatic cross-game converter is added by this research.

## Located assets

| Archive | Record(s) | Observed role and format |
| --- | --- | --- |
| `pcaatface.iff` + `pcaatface.cdf` | `face01`–`face07` | Seven dedicated likeness albedos, 256×256 ARGB8, visibly different authored faces. |
| `pcfacenormal.iff` + `.cdf` | `facenormal91`–`facenormal97` | Dedicated likeness normal textures, 512×512 DXT5. |
| Same normal bank | `facenormal00`, `10`, `20`, `30`, `40`, `50` | Six other normal records, also 512×512 DXT5; the default executable path selects from a seeded lookup. Do not relabel them solely from their numeric suffix. |
| `pcfacehair.iff` + `.cdf` | 75 `beard`, `stache`, `burns` records | Shared facial-hair artwork; names combine color/style indices. Samples: beard 256×128, moustache 64×64 ARGB8. |
| `global.iff` | `face_01`–`face_07`, type `FRFG` | Seven 544-byte floating-point face parameter records. Preset selection and coefficient conversion are traced below. The extra bytes beyond the three traced coefficient groups remain unclassified. |
| `global.iff` | `facegen_head`, `facegen_bench_head` | Shared high-detail/bench SCNEs, each with one `player` mesh part and no embedded textures. Distinct layouts/LODs must stay consistent. |
| `facegen.iff` | `mean_head` SCNE | 52 embedded 256×256 ARGB8 images, zero mesh parts. This is generator data, not 52 interchangeable finished player faces. |

**Normal maps are shared more widely than the dedicated albedos.** The default
normal lookup at virtual 0x10034070 contains suffixes
`0, 10, 20, 30, 40, 50, 91, 92, 94, 95, 96, 97`.
Thus a generated player can use several of the same normals as dedicated
likenesses. Replacing `facenormal91`, for example, can affect generated players
as well as Conley-slot users. Do not promise isolated per-slot normal edits.

`hNNNN.iff` is **not** a head filename convention here: inspected College Hoops
samples contain `Highlight`/`Hilt` records. There are zero currently resolved
`pngNNNN.iff` entries in this College Hoops source. A name-dictionary absence alone
would not prove an unknown hashed file absent; executable routing and asset
contents provide the stronger evidence.

The face albedos and normal/hair examples were decoded and inspected locally.
All seven albedos pass an in-memory DDS → swizzled GTF → DDS byte-identical image
round trip using the built-in converter. This verifies extraction/conversion,
not gameplay or a complete new-likeness import. Local artwork is excluded from Git.

## Per-player routing established on the supplied original roster

The editor's raw player window starts 0x10 bytes before the logical engine player
anchor. Offsets below deliberately distinguish these origins.

| Meaning | Logical engine offset | Raw editor offset | Evidence |
| --- | --- | --- | --- |
| Dedicated likeness selector | word +0x8C, low four bits | word +0x9C, low four bits | EBOOT selectors below plus all nonzero stock players match the seven licensed names. |
| Custom-morph flag used by generation gate | word +0x88, bit 0 | word +0x98, bit 0 | Gate branches around procedural/preset generation when set. Other uses and authoring policy still need validation. |
| Procedural generation seed input | word +0x0C | word +0x1C | Passed to the PRNG initializer by both generated-face and default normal selection routines. Do not replace the player's identity field to change it. |
| Morph byte group A | +0xA6, 50 bytes | +0xB6, 50 bytes | Three-group decode/encode loops. |
| Morph byte group B | +0xD8, 30 bytes | +0xE8, 30 bytes | Same. |
| Morph byte group C | +0xF6, 50 bytes | +0x106, 50 bytes | Same. Final bytes cross the biased raw window, remaining within the logical row. |

The selector maps as follows, corroborated by **every** nonzero row in the stock
roster, including duplicated historical/training-player rows:

| Selector | Original likeness | Matching color / normal / preset |
| --- | --- | --- |
| 0 | Generated face | Procedural route, not `face00` |
| 1 | Mike Conley | `face01` / `facenormal91` / `face_01` |
| 2 | Glen Davis | `face02` / `facenormal92` / `face_02` |
| 3 | Greg Oden | `face03` / `facenormal93` / `face_03` |
| 4 | J.J. Redick | `face04` / `facenormal94` / `face_04` |
| 5 | Al Thornton | `face05` / `facenormal95` / `face_05` |
| 6 | Alando Tucker | `face06` / `facenormal96` / `face_06` |
| 7 | Julian Wright | `face07` / `facenormal97` / `face_07` |

Stock: 5,685 rows; 5,670 selector-zero, 15 rows spread across selectors 1–7.
The custom flag is zero and all three stored morph groups are zero in every
stock row. Thus interpreting those zero groups as active face shapes would be
wrong: the executable generates/loads parameters when the flag is clear.
Existing skin, hair, facial-hair, eyes and other packed appearance fields remain
separate from this selector.

## Read-only executable chain

Addresses describe the inspected PS3 executable only, not other builds/platforms.
The ELF has two relevant TOCs: 0xA54AC8 and 0xA64A94. Map load-segment virtual
addresses to file offsets and use each function's descriptor TOC. Using one
global TOC or treating a file offset as a virtual address yields false xrefs.

- **0x74EB38:** tests player logical +0x88 bit 0. If clear, reads low nibble
  +0x8C. Zero tail-calls procedural generation **0x74E5D0**; nonzero calls
  **0x745604**, falling back to procedural generation if preset loading fails.
- **0x745604:** formats `face_{0:D2}` using that nibble, requests type hash
  **0xBE981E93** (FRFG), then calls **0x4A2164**. This is an inter-module thunk
  to **0x68D9C**, which converts three groups of float coefficients into player
  morph bytes. It is not a `png<player ID>.iff` loader.
- **0x74570C:** formats `face%02d` with the same nibble for dedicated artwork.
- **0x74ECB0:** formats `facenormal%02d`; nonzero selector adds **90**, giving
  91–97. For zero, **0x74EE24** seeds the PRNG from logical +0x0C and uses a
  lookup to choose the normal suffix.
- **0x74E5D0**, including **0x74E664–0x74E670:** procedural generation uses the
  same +0x0C seed with initializer **0x7C52BC** (LCG setup is visible). Appearance
  words constrain later generation. Changing only one DDS is not a complete
  replacement for this generated shape/texture process.
- **0x66ECC:** byte groups at logical +0xA6/+0xD8/+0xF6 decode into 50/30/50
  floats. The observed constants implement approximately `byte * 24/255 - 12`.
  **0x68D9C** encodes/clamps floats to bytes and applies group magnitude limits.
  Raw coefficient names and each component's facial meaning are not established;
  the ranges alone do not justify arbitrary GUI sliders.
- **0x4E5C5C** requests the `facegen_head` SCNE. **0x731348** includes the
  `facegen.iff` resource request at **0x73161C**. The executable also contains
  `FaceGen_ApplyHeadMorphsToTexture`; a string alone does not expose a usable API.

## What can be changed, and what is still required

1. **Seven existing likenesses:** the strongest first target. Replace the paired
   color/normal artwork and compatible FRFG preset while retaining the College
   Hoops mesh/UV/skin/LOD contract. The roster selector provides a demonstrated
   data route to select those slots; runtime testing has not been performed.
   Any players sharing a slot would share its replacement. Several normals also
   serve generated players through the default lookup above, so replacing a
   slot's normal map needs a broader compatibility check.
2. **More varied generated players:** the game already stores per-player custom
   morph bytes and uses a seed for default generation. A correct authoring path
   can vary individual geometry without a dedicated IFF per player. Reproducing
   the FaceGen bases, magnitude constraints, texture synthesis and the custom
   flag's full lifecycle is needed for accurate preview/editing. Do not write
   zero arrays as a supposedly neutral custom face.
3. **More dedicated slots:** four bits represent 0–15, but only 1–7 are backed by
   the observed assets. This is a storage bound, not proof that slots 8–15 work.
   Matching color/normal/FRFG resources, resource-pack registration/capacity,
   save/load behavior and both LODs must be established. Thousands of independently
   textured players are not available through this selector as currently traced.
4. **Borrowed NBA faces:** plausible as donor artwork or geometry for a conversion
   project, not a demonstrated direct import. NBA 2K9 has 774 named PNG archives;
   inspected `png877.iff` has two SCNEs and four TXTRs. Its scene headers differ
   from the CH shared head (sample +0x4C values 14/7 versus CH 12/7); equal bench
   counts would not establish equal bone identity/order or skin weights. Refit or
   retopologize/bake to CH UVs, validate bind pose/skinning/facial animation,
   normals/materials and bench LOD, then derive compatible CH morph parameters
   or establish an actual per-player mesh loader before promising whole meshes.
5. **Later donors:** NBA 2K14 has 1,289 resolved PNG names, but the inspected
   sample's ZLIB variant was rejected by the current decoder. Supplied NBA 2K11
   SDAT flags/version are also unsupported. Those are recorded extraction
   blockers; no bypass or pretend decoded donor is included. 2K9 is the nearest
   currently inspectable comparison, not certified interchangeable.

## Reproduce without modifying inputs

```powershell
python -m choops_py.research.player_faces "PATH_TO_ORIGINAL_CH2K8_JB"
python -m choops_py.research.player_faces "PATH_TO_ORIGINAL_CH2K8_JB" --players
python -m pytest -q tests/test_player_face_research.py
```

The command reads paired textures, shared head/preset records and the source
roster, prints JSON, and has no write/import operation. `--players` includes
private roster names; keep derived reports/artwork local. It does not claim a
cross-game schema detector, a full FaceGen renderer or a cyberface editor.
