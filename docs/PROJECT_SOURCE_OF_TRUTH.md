> Inherited technical evidence, not the current per-game support contract.
> See FEATURE_MATRIX.md, PS3_2K_ARCHIVES.md and NBA_ROSTERS_AND_2K14.md for
> newer archive/roster variants. Current caching/audio/UI behavior is described
> in WORKFLOWS.md; fixed-capacity and experimental-only statements below may
> reflect earlier versions. Unknown bits remain preserved.

# Project source of truth

Target: PS3 College Hoops 2K8, Python 3.11+, argparse and PySide6. Read
CURRENT_STATUS.md, COLLABORATION.md and SECONDARY_CODEX_PROMPT.md first. This
technical baseline preserves inherited evidence; newer project-specific docs and
tested code supersede older conservative restrictions. No JavaScript runtime.

## Provenance and confidence

Read-only references: expanded 2026-06-18 master handoff; original continuation README, archive configuration; downloaded Reborn gameProfiles, ChoopsReader, IFFReader, CDF extractor, H7A utilities, ToolWrappedReader and floor notes. Constants, pointer formulas and useful filename hash/name pairs were intentionally rewritten into Python. No Node runtime, native editor, conversion executables or legacy build products are retained. Original source authors' provenance is recorded here; upstream licensing must be clarified before adding more borrowed implementation or distributing proprietary assets.

`MASTER_HANDOFF.md` preserves the full research record and inventory. Confirmed below means corroborated by source and/or current fixture checks; candidate fields remain read-only. No game assets belong in Git.

## Archive and identity

The archive header is six BE u32 words: magic AA00B3BF, alignment, part count, zero, entry count, zero. Part descriptors are 16 bytes: first word is size in 0x800 units; bytes +8..+15 encode the part filename as UTF-16BE. Logical space concatenates listed parts, allowing entries across boundaries. CH2K8 TOC uses 16-byte records: hash +0, offset units +4, unknown +8, stored size units +12. Offsets multiply by alignment. Stored sizes must be validated against archive boundaries; derive only from next offset/end and flag the derivation. Preserve padding by extracting the complete bounded extent. Do not clamp an invalid read silently.

Case-insensitive ASCII filename hashing matches CRC32 of uppercase bytes for generated candidates. Retained reference hash/name pairs take precedence. Namespace includes ua/uh/ux/selua/seluh/selux/s/m/p/coach 000..999, h0000..9999 and known named banks, with iff/cdf/bin variants. Outer TOC names and inner IFF names are distinct identities. Unresolved entries remain hash names. Sparse alternates are meaningful: a cache name does not add a game-loadable archive or team.

Caches live under output/cache, keyed by source path, and record part sizes/mtime; stale fingerprints are rejected. Current cache validation reparses the TOC; it is a reproducible index, not yet a speed optimization. It does not prove payload integrity after timestamp-preserving changes.

## Standard IFF: FF3BEF94

BE header is 0x20 bytes: magic +0, payload start/headerSize +4, payload end/fileLength +8, zero +0C, block count +10, observed 13 +14, file count +18, observed blockCount*0x20+5 +1C. FileLength excludes optional name table and padding. Preserve all bytes beyond it.

Block descriptors are 0x20 bytes (eight BE words): name/hash, type/hash, unknown1, logical size, unknown2, absolute stored start, stored size, indexed flag. Keep descriptor order; bank IDs such as BB05A9C1 and 411536D5 are not subfile types. Block ranges must fit within payload bounds.

The BE file pointer table follows the blocks. Target = pointer field position + value - 1; inverse = target - field + 1. Follow actual pointers rather than assuming records are contiguous. Each file record is ID, type hash, offset count, then block-relative logical offsets. FFFFFFFF means absent. Infer each span using the next larger valid offset in that block or its logical end. Duplicate starts can imply aliasing; replacement must reject ambiguous shared ranges.

Optional AA171516 name table starts at fileLength: BE magic, LE body size/pointers, UTF-16LE strings. The body contains count and relative pointer to entry-pointer table; each entry has relative name/type pointers. Missing name tables may be valid. Fallback names are numeric, with known type hashes when available.

Common types: TXTR 5C369069, SCNE E26C9B5D, LAYT 86A1AC9E, ROST C61649B2, AUDO 1AEDDA1F, NAME 68B693B2, CDAN A7701F00. Full historical type map remains in MASTER_HANDOFF.

H7A wrapper: 0E4837C3, logical size, stored size including 0x14 header, unknown, shift. Descriptor bits are read low to high: 0 literal, 1 BE 16-bit backreference. Distance is low shift bits; copy length is (token >> shift)+3. Validate wrapper sizes, shifts, lookback and truncation. Decoder caps a single logical block at 512 MiB. Unchanged compressed blocks are copied verbatim. The current bounded writer preserves logical slice sizes, reuses original compression token choices where valid, and expands invalidated references to literals. Recomputed block locations/file lengths and preserved NAME table must fit the original archive extent; otherwise writing is blocked.

## CDF-backed metadata: F0985030

Always handle metadata IFF with its paired CDF; uniforms are not this family. Header +4 is metadata end; +10 block count; +18 record count. +20 points relatively to segment pointer table; +24 points to UTF-16BE CDF name. Primary record pointers start at 0x68. Primary records contain five BE words: ID, type hash, offset count, virtual header offset, virtual payload offset. Virtual offsets are not physical CDF offsets.

Each secondary descriptor is four BE words: CDF header offset/length and payload offset/length. Validate both actual ranges. Optional name table uses the same mixed-endian scheme. CDF TXTR fallback hash is 5C36FB69 (different from standard); AUDO is 1AEDDA1F. Preserve CDF segment headers, gaps, tails, compression and metadata. Same-size physical payload replacement is supported only when no preserved range overlaps. This validates bounds, not codec semantics or console compatibility. Whole CDF-pair staging is supported with paired preflight validation; physical payload growth remains blocked.

AUDO segment headers can carry a payload length at +18; interleaved audio banks must preserve headers as well as payload. H7A/GTF texture layouts vary; do not infer codec validity from DDS conversion failures.

## Tool files, textures and uniforms

2kTl is BE magic 326B546C, header size, u16 type ID, u16 block count, BE u32 sizes, concatenated blocks. Header size = 12+4*count. Use numeric type IDs; no unvalidated semantic ID mapping. Strictly reject trailing/truncated wrapper bytes.

Standard TXTR often uses separate header and payload blocks; exports preserve individual blocks plus record manifest. Uniform jersey_numbers and names are embedded TXTR subfiles, with separate NAME records possible. Indexed font glyph metrics and static placement are validated; see ROSTER_SCALE_AND_PREVIEWS.md. Validated TXTR descriptor: +58 format byte, +59 mip count, +5A dimension, +5B cube flag, +60 width u16, +62 height u16, +64 depth u16, +68 pitch u32; +A4 is payload offset+1. Unknown variants remain raw-preserved and blocked for DDS edits.

## SCNE / courts

SCNE package header is 0x54 bytes. +20 texture count; +24 relative texture pointer; +44 model-part count; +48 relative model-part table. Model records are 0xB0 bytes; texture headers also 0xB0. Part name at +0 is relative UTF-16BE. +04 ID; +08 flags; +10 radius-like float; +30..38 center; +4C..54 scale. Section counts/pointers: material +60/+64, draws +7C/+80, buffers +84/+88, declarations +94/+9C. +A4 is index flags, +A8 index count, +AC index offset+1 (do not confuse flags with count). Known floor parts: floor, paint, centerlogo, lines. Full-court imagery requires validated UV/material routes; changing texture dimensions alone does not create full-court coverage. OBJ writing and geometry edits are deferred.

## Roster and development direction

v1.11 correction: team roster pointers are an 18-element array at editor +0x6C;
the active u16 count is +0x188. Runtime array/count are anchor +0x3C/+0x158. All
443 stock arrays validate with those fields. Player row zero is real when active;
only trailing row-zero references are empty. See ROSTER_SIDE_PANELS.md for evidence
and guarded transfer/brand propagation. Historical 16-slot assumptions are superseded.

Conference scalar provenance: the public
[conferences.py](https://github.com/bphit4/CH2k8-Roster-Editor/blob/main/conferences.py)
defines the same +0x0A..+0x22 field offsets and big-endian u16/RGB widths. The
separate Conference_Parser.py only locates rows/names; it does not establish those
scalar meanings. Source captions are retained and gameplay effects remain unverified.

Current corrections: jersey number is byte +0x1B, preserving adjacent flags at
+0x1A. Tables/counts derive from the header. Verified ratings, equipment/shoes,
appearance choices, optional conference/D1 updates and alternate links are
editable through declared masks. The older restricted-field paragraph below is
historical; ROSTER_EDITOR.md and projects/ define current scope. Six palette words
remain unresolved; long string rebuilding and unknown fields remain blocked.

Roster adapters support standard IFF ROST, raw ROST, type-21 wrapper, length-prefixed decrypted USERDATA, one-USERDATA decrypted ZIP, and the observed CH2K8 Legacy-mode USERDATA profile. In that profile, a validated ROST-shaped payload begins at save offset 0x438 and has the standard 0x003DF800-byte extent; the remaining mode data is preserved, not interpreted. The writer allows only fixed-size edits to this embedded roster and checks bytes before/after it remain unchanged. No encrypted-save decryption is provided. Known ROST tables: players 0x0271AC/5685/308, arenas 0x1D5C84/379/28, teams 0x1D85E0/443/704, coaches 0x23F78C/1373/44.

ROST runtime string pointers are field + signed delta - 1, consumed as UTF-16BE (77FB1C / 7C5818). Stored reference anchors retain the documented +1 biases. Player last/first pointers +0x10/+0x14 target aligned big-endian text; do not use the shifted ASCII-only LE interpretation. Jersey number is byte +0x1B (preserve adjacent flags and player ID +0x18), height +0x3A, position +0x3B. Team roster references +0x6C, 18 slots, point to player row +0x11. Team arena +0x44 targets arena row +0x19, coaches +0x60/+0x64/+0x68 target coach row +0x15, rivals +0x4C/+0x50/+0x54 target team row +0x31. Asset IDs are high u16 at +0x18C/+0x190/+0x194; preserve low words and require consistent existing IDs. Conference record fields +0x0A..+0x22 are exposed with their source labels and original u16/RGB widths, based on the public CH2k8 roster parser and cross-checked against supplied USERDATA record values. The source labels identify founded year, championship-order values, Final Fours, prior-year bids, rank, tournament settings, and color; gameplay effects are not independently verified. Prestige and unknown appearance fields remain read-only. Names use copy-on-write UTF-16 growth with preserved aliases and fixed table locations; keyboard limits are advisory. Conference +0x1A is now confirmed as a tournament index and protected pending a backlink writer; logo routing uses 900 + conference index. See CONFERENCE_ASSETS.md.

Current TXTR descriptor +0x58 contains format, mips, dimension, cube, remap,
width/height/depth and pitch. GTF wraps descriptor/image in a 0x30-byte header.
Conversion is built-in Python for L8, ARGB8, DXT1/3/5 and RGBA16F, mips/cubes.
Historical converter switches are reference evidence only. Non-stadium imports
normalize to the selected base layout; stadiums allow supported dynamic sizes.
SCNE textures share the TXTR pipeline while geometry is preserved. CDF headers
and images may each be H7A compressed; sideline_items contains SCNE records.

Future development should extend validated texture variants and bounded writers, add meaningful regression fixtures, and verify console behavior. Do not expose speculative roster fields or geometry modifications as safe.

## Current safety contract and evidence

Generated outputs live under project output/. Reject source overwrite/overlap,
traversal and linked builds. Supported record/archive growth uses validated
relocation; unknown offsets/aliases remain blocked. Manual builds are transactional
and source-bound; agents must not create testing game copies or launch RPCS3.
PySide6 GUI and CLI share services; workers use signals rather than widget writes.
Experimental AUSB/AUDO evidence is in AUDIO_RESEARCH.md. EBOOT stays read-only.

Validation procedures are documented in TEST_REPORT.md and rebuild/ACCEPTANCE_TESTS.md. Public documentation excludes fixture fingerprints, extraction measurements, session records and environment-specific results. Do not infer current capability from historical smoke observations or command registration.
