# NBA PS3 support and roster evidence

## Verified scope

College Hoops 2K8 keeps its existing editor. Roster payload detection now selects
separate NBA 2K9 or NBA 2K14 schemas automatically for raw ROST, standard IFF,
length-prefixed decrypted USERDATA and supported save ZIP wrappers. Filename or
selected game title does not authorize applying another game's field offsets.
Unknown/malformed schemas fail; saved outputs are reparsed and preserve unknown
bytes. No savedata encryption, account signing or gameplay certification is added.

NBA 2K9: 1,064 player records (452 bytes), 69 team records (572 bytes), 72 arena
records (60-byte anchor stride) on the supplied stock copy. NBA 2K14: 1,665 player
records (460 bytes), 105 teams (760 bytes), 102 arena records (56-byte anchor
stride). Counts come from validated relative table directories, not fixed stock
counts. The following offsets are relative to the player record's physical start.

| Field | NBA 2K9 | NBA 2K14 | Storage |
|---|---|---|---|
| Last / first name | +0x10 / +0x14 | +0x10 / +0x14 | signed relative UTF-16 BE pointers; field + displacement - 1 |
| Height | +0x34 | +0x1C | BE float, centimeters; UI edits inches |
| Weight | +0x30 | +0x20 | BE float, pounds |
| Jersey number | word +0x38, bits 16–22 | word +0x30, bits 12–18 | masked writes, 0–99; 100 displays 00 |
| Face artwork ID | low 16 bits at +0x38 | high 16 bits at +0x2C | pngNNNN.iff CRC candidates |
| Primary position | +0x71 low 3 bits | +0x45 high 3 bits | PG=0, SG=1, SF=2, PF=3, C=4 |
| Secondary position | unestablished | +0x45 bits 2–4 | same codes; 5=None |

Names and floats are directly corroborated against named stock players. Number
and face masks match the stock player/artwork sequences. Position runs match the
observed lineups and valid-code distributions across both full player tables.
NBA 2K14's position pair and height/weight/portrait relationship also agree with
the original NBA 2K13 editor's field relationships. That reference is supporting
evidence, not permission to transplant all PC/2K13 offsets. A candidate body field
at that reference's offset is constant across all NBA 2K14 players and was rejected.
College Hoops still has no independent secondary-position field.

The NBA panel has Players / Teams / Arenas lists, team filtering, search and a
side editor. Numeric editors/dropdowns cover supported measurements, number, face
and positions. Undo/redo and Save copy use the same validated backend. Team and
arena names are editable where their existing string storage is unique. Links to
player membership and arena/floor/LED/dorna/menu assets are read-only. Explorer
references show confirmed face IDs and literal arena/menu asset strings; team
uniform ownership is not inferred from row ordering.

Text allocation is intentionally bounded: no larger replacement than the existing
UTF-16 string is written, and shared-string edits are rejected after scanning
aligned relative references, including unparsed tables. NBA heap relocation and
engine/display text limits remain unestablished. These bounds are editor safety
rules, not claimed engine limits. Unknown ratings, tendencies, appearance, contract
and history semantics remain read-only. Existing College Hoops ratings are not
shown under NBA labels. NBA bulk CSV import/comparison and the College Hoops byte
audit are blocked explicitly rather than reusing incompatible schemas. CLI decode
can export NBA editable fields as CSV; source-bound JSON patches can edit them.

## NBA 2K14 containers

The supplied PS3 copy identifies itself as NBA 2K14 / BLUS31204. Its main archive
has 8,594 entries and seven logical banks. Bank descriptors are 72 bytes rather
than 16, with bounded UTF-16 names such as DVD:1A and SDAT:2A. Only these recognized
prefixes are stripped; arbitrary paths remain rejected. TOC rows retain the
size64/hash32/sector32 schema.

0A, 0B, 2A and 3A are NPD v4 SDAT files. The Python random-access reader supports
only observed flags 0x0100003C, verifies the header CMAC and each accessed block's
HMAC before returning plaintext, and caches at most eight decoded blocks. No
whole-bank plaintext copy or emulator is needed. Unsupported versions, flags,
compressed/debug variants, bad hashes and truncated blocks fail explicitly.
PyCryptodome supplies the cryptographic primitives. Original bank files remain
unchanged. **SDAT/72-byte-descriptor JB rebuilding is blocked**, including on fully
decrypted copies with the extended descriptors: authentication/header regeneration
has not been validated. Export edited roster IFF/USERDATA copies for research;
this update does not claim a tested in-game installation path for NBA 2K14.
Supported override preparation can run in preview-only validation mode; this
does not bypass the independent JB writer guard.

ZLIB block wrappers use a 16-byte BE header (magic, logical length, stored length,
opaque flags) followed by a strict zlib stream. Writers preserve flags, update
lengths, reject trailing/oversized/truncated streams and reparse changed output.
The supplied NBA 2K14 roster decodes to 2,540,288 bytes; NBA 2K9 to 983,328 bytes.

Some IFFs have an extended metadata area: the file pointer table is located through
header +0x1C rather than assumed to immediately follow the block descriptors.
Reading/texture inspection supports it. Rewriting these extended IFFs is blocked
until the additional metadata's pointer semantics are established. The roster IFF
uses the normal pointer-table layout and can be exported with edited payloads.

NBA 2K14 scene variants observed and decoded: 128-byte instances, extended vertex
buffer descriptors and 64-byte draw records with packed material indices. Each
layout must uniquely pass bounded structural validation. Courts are separate
fNNN.iff packages; selecting floor for sNNN.iff resolves the corresponding source's
fNNN.iff when present. On the supplied samples: two floor meshes, 61 arena meshes;
one arena lighting mesh has unsupported UVs. NBA 2K14 jersey artwork/cloth binding
is still unresolved; its direct combined jersey preview remains unavailable.
Runtime shader accuracy is not certified.

## Filenames and repeatable research

Expanded CRC candidate families include pngNNNN.iff faces, logoNNN/NNNN.iff, fNNN.iff,
roster.iff, localized language banks, players.bin, teams.bin, motion.iff and music.iff.
Candidate matches reduce generic names without asserting unknown file semantics;
CRC32 alone is not proof of a unique authored spelling. The bounded candidate
survey found 1,607 matches across previously unresolved entries of the two NBA
copies (including three incidental patterns not promoted to the default dictionary).
Shared record type labels are corroborated against authored College Hoops NAME
trailers (SKEL, Clth, STRG, MRKS, SCOS, SPCI, AMCR and FxTweakables).

Open a source JB in Explorer, then Roster editor > Load from JB or Load from
overrides. External roster IFF/decrypted saves use Open USERDATA / roster IFF.
Save copy retains the input wrapper; Export USERDATA emits a decrypted length-
prefixed payload, not a signed PS3 savedata folder. CLI roster-detect/decode/save
uses the same payload dispatch. The source game is never modified.

## Primary references

- [RPCS3 SDAT format implementation](https://github.com/RPCS3/rpcs3/blob/master/rpcs3/Crypto/unedat.cpp)
  and [format constants](https://github.com/RPCS3/rpcs3/blob/master/rpcs3/Crypto/key_vault.h).
  Source inspection only; RPCS3 was not launched. The new reader is independently
  written and deliberately supports a narrower observed format.
- [Original NBA 2K13 PlayerReader](https://github.com/leftos/nba-2k13-roster-editor/blob/master/NBA%202K13%20Roster%20Editor/Data/Players/PlayerReader.cs)
  and its Position enum. No PC/2K13 schema is treated as NBA 2K14 PS3 proof without
  matching supplied-byte evidence.
