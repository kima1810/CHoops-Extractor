# Current support matrix — v1.23

Supported means structurally verified by parsers and automated fixtures. No row
certifies game/runtime compatibility. Unknown variants fail explicitly.

| Operation | College Hoops 2K8 PS3 | NBA 2K9 PS3 | NBA 2K14 PS3 |
| --- | --- | --- | --- |
| Archive detection, listing, extraction | Supported observed layout | Supported observed layout | Supported observed SDAT/72-byte descriptor variant |
| IFF/CDF, texture inspection | Supported known layouts | Supported known layouts | Supported known layouts, including observed ZLIB blocks |
| DDS overrides / static preview | Supported known layouts | Supported known layouts | Preview/preflight supported; some newer mesh/UV bindings unavailable |
| Manual fixed/growing/repacked JB output | Supported layout, synthetic verification | Supported layout, synthetic verification | Blocked: authenticated SDAT/extended writer not established |
| Roster identity | College Hoops schema | Separate NBA 2K9 schema | Separate NBA 2K14 schema |
| Roster editing | Confirmed names, ratings, appearance, history, palettes, footwear, assignment | Confirmed numeric/text fields only | Confirmed numeric/text fields only, including observed secondary position |
| CSV / selective comparison import | Supported confirmed College Hoops fields | Not a general NBA bulk editor | Not a general NBA bulk editor |
| Full unknown-byte semantics / engine ceilings | Incomplete; unknown bits retained | Incomplete | Incomplete |
| Animation banks | Inventory/research | Inventory/portability research | Inventory/portability research |
| Uniform geometry editing | Experimental source-bound OBJ/rest-position workflow; known cloth only | Unsupported | Unsupported |

| Team asset expansion | Checked stadium/uniform/SELU/menu plans, overrides and build integration; runtime unverified | Unsupported | Unsupported |

## Shared features

NBA 2K11 has additional **research-only read/extraction evidence** for the observed
NPD v3 SDAT/72-byte descriptor copy. No 2K11 roster editor or SDAT build writer is
enabled. [Donor evidence and limits](NBA2K11_DONOR_ASSESSMENT.md).

- Explorer reads nested records and researched asset references; labels never make
  an unknown hash an established semantic identity.
- Team Assets checks existing available assets by default, marks shared asset
  routes with peer team names, and starts the target box with the original ID.
  Existing checks alone never clone the roster; independent copies are explicit.
- Offline NBA11/CH event inspection and contract-gated event-table conversion
  complement packed-pose/timing/root conversion. No default semantic event map
  or playable donor bank is supplied; opaque payload schemas block conversion.
- Source and overrides are cached concurrently. Global preview selection resolves
  geometry and artwork; DDS takes priority only within overrides, with TXTR fallback.
- Static preview camera supports orbit, look-around, pan, WASD movement and fit.
  Combined jersey/shorts and cut/neck controls use supported authored meshes.
- Court guides are separate raised thin references. Border, 3-point, key/center
  toggles do not modify floor textures or depend on roster palettes.
- Supported College Hoops jersey previews draw authored numbers 0–99 and the
  supported Reborn surname preview. Runtime cloth/skinning is not simulated.
- Audio WAV replacement can queue multiple songs before saving cribmusic.bin.
  Song names/artists are read-only. Licensed music/fight songs are separated.
- GUI repair diagnostics identify the target and compatible next action. Larger
  payloads still require known relocation/pointer semantics; arbitrary growth is
  not automatically safe.

## Excluded or unresolved

No automatic D1 conversion, editor EBOOT patching, complete gameplay animation
port, encrypted-save decryption, universal NBA roster fields or full arena shader
emulation. Unknown reflection/fake-bump/AO/runtime palettes and universal text
ceilings remain unestablished. See [limitations](KNOWN_LIMITATIONS.md),
[NBA details](NBA_ROSTERS_AND_2K14.md) and [shader evidence](ARENA_SHADER_MASKS.md).

## Desktop platforms

Windows x64, macOS arm64 and macOS x86_64 have native packaging/check jobs.
Mac packages require macOS 13+, are ad-hoc signed, and are not notarized.
Linux remains a source/test target. Native checks do not certify gameplay.
