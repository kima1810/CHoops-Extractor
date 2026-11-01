Current NBA extension: see [NBA roster/container support](NBA_ROSTERS_AND_2K14.md) and
[animation portability research](ANIMATION_PORTABILITY.md). Those pages define the
newer per-game boundaries; historical College Hoops-only statements below remain
specific to that earlier scope. NBA 2K14 SDAT rebuilding and complete NBA ratings
semantics are not implemented.

# Shared PS3 2K archive support

The editor automatically detects supported archive layouts when opening a JB or
USRDIR folder. There is no game-mode selector. Game title/ID are read from optional
PARAM.SFO for display; they never determine the binary TOC layout. College Hoops
2K8 roster editing and its confirmed rendering features remain available. A known
other title is not automatically decoded with the College Hoops roster schema.

## Confirmed outer layouts

Both supplied games use magic AA00B3BF, a 24-byte big-endian header, 16-byte bank
descriptors, 2,048-byte alignment and 16-byte asset entries. Banks are concatenated
logically; an entry may cross bank boundaries. The entry order differs:

| Byte | College Hoops 2K8 layout | NBA 2K9 layout |
|---|---|---|
| 0..3 | filename CRC32 | stored byte length, high 32 bits |
| 4..7 | sector offset | stored byte length, low 32 bits |
| 8..11 | preserved flags | filename CRC32 |
| 12..15 | stored byte length | sector offset |

The detector validates both candidates against the full TOC, unique hashes,
header/neighbor/bank boundaries and stored lengths. Exactly one candidate must be
valid; ambiguous/unknown layouts are rejected. College Hoops' existing derived
extent fallback and rounded extraction behavior are retained. The size64 layout
uses exact stored lengths. Writers serialize TOC rows using the detected source
layout for in-place builds, growth/append and bank repacking. Header/flags/opaque
padding, unknown resources and untouched files keep their preservation checks.
The raw 64-bit size is not truncated to a 32-bit field.

Other PS3 2K games may work automatically if they use a supported layout and inner
formats. This is not a claim that every game/year/platform is compatible. New or
ambiguous layouts require evidence and fixtures; do not add filename/title guesses
or silently reinterpret an unknown format.

## NBA 2K11 research access

The observed NPD v3 SDAT variant (flags 0x0100003C) now selects its version-specific
wrapping key and retains header/block authentication. The supplied 2K11 copy has
6,974 entries, 72-byte descriptors, size64 TOC rows and mixed raw/SDAT banks.
Extraction and bounded known inner readers are available; SDAT rebuilding remains
blocked and no NBA 2K11 roster schema is enabled. See [donor assessment](NBA2K11_DONOR_ASSESSMENT.md)
for verified sample reads, animation inventory, preview gaps and conversion ratings.

## NBA 2K9 supplied-copy observations

Read-only inventory: 6 banks, 6,158,907,392 bytes, 5,624 entries, no overlaps.
945 outer filenames match the existing hash dictionary; those remain candidates,
not new globally verified name assignments. Source game ID is BLUS30197.

| Stored resource signature | Count | Handling |
|---|---:|---|
| FF3BEF94 | 3,171 | Standard IFF, existing readers |
| F0985030 | 46 | CDF-backed IFF metadata; preserve linked CDF |
| 01 + 0E4837C3 | 2,322 | Flagged H7A resource; exact raw extraction |
| 0E4837C3 | 15 | Compressed header/prefix and possible following data; raw preservation |
| Other | 70 | Exact raw extraction; unsupported inner decoding stays explicit |

A sampled flagged H7A resource decoded to non-IFF data. Do not strip the flag and
assume all 2,322 entries are complete compressed IFFs. Their wider purpose and
possible references are not fully established. No archive resource is automatically
unwrapped/rebuilt based on this signature alone.

Selected exact extractions: ua000.iff, uh000.iff, s000.iff, gamedata.iff, global.iff,
teamselectlogo.iff and its linked teamselectlogo.cdf. All blocks in the five standard
IFF samples decoded to their declared lengths. Uniform TXTRs, stadium TXTRs and
shared gamedata/global artwork converted to valid DDS images with existing code.
The menu-logo pair parsed 71 texture records and exported a 512x512 DXT5 DDS.

The shared preview services decoded:

- Jersey + shorts: 2 meshes and 2 authored images, using existing cloth packages.
- Floor: 2 meshes and 2 images, no parser warnings.
- Arena: 78 meshes and 58 images, no parser warnings.

These are static authored previews, not runtime/gameplay certification. NBA number
placement, roster semantics, animation/skinning, dynamic shaders and all unknown
resources have not been generalized. College Hoops' fixed S256 alignment guides
are not injected into another game's floor preview.

## Shared inner readers

IFFs without a tool-generated name trailer can recover a small set of shared
internal names from case-sensitive CRC32 IDs: arena, floor, uniform artwork,
jersey/shorts cloth shapes and numbered logos. Unknown IDs remain numeric and
unknown types remain unknown. Authored name tables still take precedence.
CDF metadata recognizes the standard TXTR hash as well as the older CDF variant.
SCNE previews accept declared half4/float4 UV fields (first two UV components) and
half4 vertex colors; complete declared attribute extents stay bounds checked.
The NBA arena's half4 declarations are the read-only evidence for this extension.

Asset caches include the detected TOC schema. Frozen importer fingerprints include
the shared layout and record-label modules, so changed readers invalidate prepared
results. Source and override toggles keep the same detected schema and game identity.

## Editor and research usage

Open the NBA JB folder through the existing source-folder action. Use Explorer,
Texture Editor, Models / Courts, Select overrides folder and Mod Builder normally.
There is no new game mode. Unresolved extracted IFFs keep a hash-based .iff filename;
non-IFF resources remain .bin. Load source rosters only for a confirmed schema.

For a separate read-only inventory/extraction command, from the repository root:

```powershell
python -m choops_py.research.nba2k9 "NBA_JB_ROOT" output/research/nba-inventory
python -m choops_py.research.nba2k9 "NBA_JB_ROOT" output/research/nba-samples --extract ua000.iff uh000.iff s000.iff gamedata.iff global.iff teamselectlogo.iff
```

Selectors also accept `index:1045` or `hash:0x30f9aaf9`. Indices are input-specific;
use names/hashes for repeatable selection. This command auto-includes a CDF
metadata file's linked payload, checks its filename/CRC and publishes a new output
folder only after source metadata and written SHA256 checks. Existing output is
never overwritten. `--all-iff` explicitly exports all direct IFFs and linked CDFs;
this can use several GiB. It does not pretend unknown GPU/resource streams are IFFs.

Read-only planning also accepted a larger uniform-IFF replacement against the
supplied NBA TOC, preserving its size64 schema and source inventory. It created
no output banks. Raw extraction is byte preserving; rebuilding tests use synthetic
archives only.
No supplied JB was rebuilt, no EBOOT was edited and RPCS3 was not opened.
