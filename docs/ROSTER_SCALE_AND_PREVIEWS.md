# Roster scale and preview project (in progress)

Baseline: merged v1.11, master 7796fcbd72c127730f484c67a5b0de26440ed066.
Recent functional PRs were already merged when this project began. The remaining
old setup draft is superseded, not new code to merge.

## Implemented source work

- School filter and school column for players; existing text search/sorting remain.
- Ratings edit inline in the side panel with a bounded spin box. Copy ratings and
  tendencies, then paste to selected players in one atomic undo step. Large batches
  write confirmed masks and validate/reparse once, not once per cell.
- Export editable cells as CSV. Values and preconditions are JSON values inside
  CSV cells; edit Value, retain Original and source identity. Import previews changes
  first and refuses wrong sources, stale values, duplicates and invalid channels.
  Spreadsheet context columns show school/player; source binary data is excluded.
- Compare two supported roster files; show current/incoming values by school and
  record, filter, check individual fields, then import selected compatible changes.
  Unique player IDs and school ownership are used where available; name matching
  is the fallback. Duplicate/unmatched identities and unresolved references are
  excluded. Renumbered/recycled IDs are not automatically reconciled. Review is
  required; imported fields share existing writers. Arrays of roster membership
  are excluded from bulk CSV/comparison, retaining the guarded School interface.
  Review uses a table model with persistent source-row selections across filtering
  and sorting, avoiding one widget allocation per edit in large comparisons.
- School footwear imports use scoped propagation, not a separate unsafe writer.
  Coupled field conflicts roll back. Undo remains one action; patches are replayable.
- Height/weight use pickers. Body Build and Muscle Tone already have confirmed
  dropdowns. Class, Redshirt and Redshirt Used are newly mapped and editable.
  Confidence uses its confirmed getter/setter and 35–99 UI range.
  Conference History separates the supported history/record scalar fields.
- A shared Source JB / Selected overrides toggle reloads SCNE and texture previews.
  Staged archives must match source preconditions and replacement checksums. Shoes,
  uniforms and general named/hashed archives use the same overlay. Standalone assets
  with no corresponding JB identity retain their standalone source; no counterpart
  is invented. No game folder is built for previewing.
- Loaded roster palettes update confirmed court bindings; manual school association
  handles shared stadium families. Arena mask routing remains unconfirmed.
- Explorer categories support shoes, uniforms, cloth geometry, stadiums, logos,
  players, audio, menus and rosters; category and roster-reference columns sort and
  search. Unknown identities retain hashes and evidence-labelled internal names.
  The known hi_shoe1 container gains a verified internal-record display label.
- Content-addressed DDS/GTF conversion and base-layout normalization caching checks
  input, layout, converter source and Pillow version, validates stored checksums,
  and limits the cache to 512 MiB. Changed/corrupt entries regenerate. The GUI build
  summary lists replacements, resized images, reuse and compatibility problems;
  machine staging metadata remains available to the build validator.

## Text growth and actual text-entry evidence

Strings no longer require the original encoded length or unique shared storage.
Copy-on-write appends a terminated UTF-16BE entry (stored delta includes +1) and updates only the selected
signed-relative pointer. Original strings, aliases, table positions and unknown
bytes remain intact. USERDATA length prefixes, type-21 wrappers, decrypted ZIP
members and sole-ROST/single-block IFF lengths rebuild and reparse. Unsupported
multi-block IFF growth is explicitly refused. These are structural checks, not a
claim of gameplay validation. No original roster or executable is overwritten.

Read-only EBOOT callbacks establish **game editor input capacities**, excluding
the terminator: player first/last 16 (0x693F98/0x691ACC, buffer 0x11); School Name
16 (0x6D17F8); Abbreviation 4 (0x6D18FC, buffer 5); Stadium Name 15 (0x6D1A00,
buffer 0x10); Nickname 16 (0x6D1AF4); Student Section 32 (0x6D1CFC, buffer 0x21).
The Edit Schools save path now connects those temporary strings to serialized
fields: 0x6D09FC–0x6D0E5C writes team anchor +0/+8 (short/school name), +4
(abbreviation), +0xC (plural mascot), +0x16C (event name) and +0x168 (student
section). The team anchor bias is +0x30. Keyboard capacities are advisory, not engine storage caps:
16/16/4/16/64/32 UTF-16 units. Stadium-name temporary string 0x3140(r2) loads
from arena anchor +0 at 0x6D605C, matching arena row +0x18; its entry cap is 15.
Text storage may grow beyond those keyboard capacities; unknown engine ceilings are not guessed. Singular mascot,
conference and coach names are not assigned guessed caps.
The text-buffer constructor is 0x7C708C through 0x1E3224; keyboard initialization
0x1D8AAC uses that buffer descriptor. These are not claims that the renderer cannot
display longer authored vanilla strings. Existing longer values are preserved.

Conference and other unmapped text fields have **no invented field-specific cap**;
the UI identifies their engine limit as unresolved. Payload/relative-pointer size
guards still apply. The old arbitrary 256-character parser ceiling is removed.
Do not describe those unresolved limits as fully reverse-engineered.

## New eligibility evidence

Class display 0x68F4D0 dispatches through 0x49DBD4 to 0x1C0054. Initializer
0x1C7248 writes the table: 0–3 HS Freshman/Sophomore/Junior/Senior, 4–7 college
Freshman/Sophomore/Junior/Senior, 8 Graduate. Menu setters establish writable
0–7; Graduate is preserved, not newly assigned. Storage: row +0x94, bits 28–31.

Redshirt display 0x691D7C and controls 0x68F594/0x68F5F0 use row +0x94 bits
26–27. Constructor option table gives None/Normal/Transfer/Medical. A nonzero
selection clears Redshirt Used at row +0x9C bit 30. Used controls
0x68F64C/0x68F518 toggle that bit; setting it clears active Redshirt. Scholarship
bit 31 and weight bits 11–19 remain untouched. Tests cover these coupled effects.

Confidence callbacks 0x69E910/0x69E924 read/write anchor +0x70, row +0x80.
Constructor metadata exposes bounds 35 and 99; source values outside those bounds
are preserved until explicitly edited. Jump-shot getter/setter +0x83 and its 0–111
range were also located. The side panel now edits that animation ID with a
bounded dropdown; exact localized animation captions remain unresolved.

Continuation fixes: preview workers receive a source snapshot without reading Qt
controls. Unique SCNE names survive archive record reordering; missing names are
refused. Duplicate rest-pose records retain their explicit index and are not
assigned invented identities. Comparison maps conference references by unique
conference identity and excludes unnamed records. New rosters reset school
filters/preview association to avoid carrying a previous roster's school index.
Explorer nested records expose exact `teamselectlogo.iff/logoNNN` school links;
stadium references follow the arena pointer/code rather than guessing from a
school's asset ID. Other menu-bank subrecord routes remain under research.

Read-only jersey colour tracing: 0x4DC8A0 binds semantic hashes 0x72251300
(`CustomJerseyColor`) and 0xDC165DB5 (`CustomPipingColor`). Its normal team
object path reads anchor +0x170/+0x174, corresponding to palette slots 0/1 with
the confirmed +0x30 team-anchor bias. It unpacks RGB through a lookup table and
normalizes the low byte separately; do not assume the fragment channel masks.
A separate mode calls 0x532C64, which uses getters 0x763DB0/0x763E00 at anchor
+0x1A8/+0x1AC (slots 14/15) and can swap their order based on team selection.
Thus these shader constants reuse both equipment and school primary/secondary
colours in different runtime paths. The enabling mode and fragment routing still
need proof before automatic jersey recolouring is implemented.

## Outstanding work (do not claim complete)

Full roster semantic reverse engineering,
remaining school/coach/player records, complete per-field engine text limits,
arena channel-to-palette masks, complete jersey lighting and full menu asset
subrecord links remain unfinished. No secondary position control appears in the
traced localized player bindings; the confirmed position is a whole byte at +0x3B.
Class/Redshirt findings do not justify guessing those other bits. Body shape and
muscle masks are already confirmed; no guessed body geometry is added.

Existing conference-parser reference:
https://github.com/bphit4/CH2k8-Roster-Editor/blob/main/Conference_Parser.py.
Executable evidence is retained privately, read-only; no proprietary bytes/assets
or workstation paths are distributed. NEVER launch RPCS3 or make testing JB copies.

## Authored jersey lettering (PR #13 continuation)

The Jersey side panel supports every preview number 0–99 and **00**. A selected
player can follow the roster number or use a preview-only number; neither preview
numbers nor the requested **Reborn** surname alter roster data. Source/override
selection applies to glyph artwork as well as cloth/texture records.

Font TXTRs jersey_numbers/names use indexed L8, remap 0x5500, and a 256-entry
ARGB palette after the four-byte-aligned mip payload. The remap forces GPU ones;
CPU path 0x7A87B4/0x79F33C uses the palette instead. Preview decoding preserves
that authored RGBA and rejects missing palettes rather than using a system font.
NAME/numbers holds ten BE (x,width) u16 pairs; aligned copies/advances reproduce
0x4E7C8C, including sentinel 100 -> 00. Global jerseynum00 supplies the template.
UnAD/unidata +1C..28 places front numbers and +2C..38 places back numbers;
**the latter is not a surname transform**. 0x4DCD5C sets their reciprocal-extent
UV transforms; NumberMap is CRC32 0x7FF175D8.

Surname consumer 0x4E7F0C calls 0x520898. 0x520740 maps apostrophe/hyphen to
indices 0/1 and A–Z/a–z to 2–27; spaces advance without copying. NAME/names
metrics and 0x5207B8/0x520898 supply aligned spacing and centering. Global
jerseyname00 supplies the template (stock 256×32). UnAD +08..18 supplies the
polar horizontal/vertical centre, radius, angular width and radial scale.
The preview renders Reborn with authored uppercase glyphs and curved placement.
GLSL atan/length evaluates the polar transform rather than reproducing the
game's half-precision atan approximation; full cloth/lighting is not simulated.
RSX instruction definitions used for read-only interpretation:
https://github.com/RPCS3/rpcs3/blob/master/rpcs3/Emu/RSX/Program/RSXFragmentProgram.h.

Explicit glUniform1i corrects Qt scalar overloads for sampler/bool uniforms;
rendered-pixel tests cover front/back numbers, names and palette switches.
Supported material DiffuseColor is read at the shader-declared CPU offset;
confirmed court palette edits replace it. Arena channels are not assigned
unproven palette roles. Edit Schools save 0x6D0CC0..0x6D0CD0 copies slots 14/15
to 16/17; these are labelled school primary/secondary runtime copies. Slots
27–30 remain unresolved, not writable guesses. Secondary positions are closed by owner confirmation.

Additional appearance/tattoo/post/free-throw fields and all 112 jump-shot captions are now supported; see ROSTER_SEMANTICS.md. Arena vertex-colour/alpha, lightmap, glow and flare routing is implemented; see ARENA_SHADER_MASKS.md for evidence and remaining runtime effects.

Keyboard limits no longer block external edits. Dynamic text uses copy-on-write UTF-16 storage, NUL/control-character checks, signed-relative-pointer bounds and the adapter’s 60 MiB safety guard. That guard is a tool limit, not a claimed engine maximum; gameplay compatibility of arbitrary long names remains unverified.

Secondary-position search is closed by owner confirmation; only the primary position is exposed. See CONFERENCE_ASSETS.md for current index/logo behavior and tournament-link protection.

CSV boundary: both editable and per-table exports whitelist actual roster fields. Asset references, UI/source badges, research notes and row offsets do not enter CSV data. Editable CSV retains source SHA, table/index/slot identity and original values for safe import.
