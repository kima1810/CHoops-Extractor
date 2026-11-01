# Team assets (v1.20)

The **Team assets…** button opens the large assignment matrix. It exposes the
separate team index, asset, uniform-owner, stadium and menu-logo identities and
prepares checked-category additions for overrides/JB builds. See TEAM_ASSETS.md.
This supersedes the alternate/independent-action removal notes for v1.10 below;
D1 conversion remains unavailable. Existing roster side editors remain intact.

Current continuation: text edits warn in orange beyond known game keyboard
capacity without truncation. School References exposes the guarded Conference
index. Conference Logo opens its exact bank record for preview/DDS replacement.
The tournament link remains read-only. Research byte coverage now separates
known and unknown bits within packed words. See CONFERENCE_ASSETS.md.

# Roster editor

v1.11 supersedes earlier dialog/16-slot descriptions: every category uses a side
editor; school references, 18 roster slots, palettes and shoes are editable there.
Player school assignment is an atomic guarded membership update. School shoe
brands propagate to that school’s roster only. See ROSTER_SIDE_PANELS.md for scope,
row-zero/count correction, safeguards and static combined jersey previews.

v1.10: Player, Ratings and Scholarship tabs are always beside the selected player.
Double-click a writable value to edit it; Scholarship has a named status picker.
Height uses feet/inches, positions PG–C and equipment readable styles. Schools
combines Teams/Edit Schools. Realign conference changes membership without D1
conversion. Alternate/new-asset/independent-asset actions and separate properties/
attributes buttons are removed. [Research evidence](PLAYER_QOL_RESEARCH.md).

Open the GUI Roster Editor and choose roster_english.iff, raw ROST, decrypted USERDATA, a type-21 tool wrapper, or a decrypted ZIP containing exactly one USERDATA. Encrypted saves are not decrypted by this tool.

Roster / Legacy save editor also recognizes the observed Legacy-mode USERDATA
layout. It edits the validated roster region in place and preserves the mode
header and trailing state bytes. The full Legacy-mode state is not yet decoded;
unknown fields remain unchanged. Text edits must keep their current UTF-16 byte
length so the outer save layout cannot shift.

Players, teams, schools, arenas, coaches, conferences and uniforms have searchable
views. Long operations run off the Qt GUI thread. Confirmed ratings, appearance/
equipment, RGB palette choices and shoes are editable with undo/redo. Save copies
preserve ZIP/decrypted wrappers; Export game roster IFF uses the loaded JB wrapper.
Unchanged bad name characters warn; invalid pointers/new corruption still block.

The active scale branch uses copy-on-write UTF-16 text growth instead of equal
length/unshared storage. Verified player and Edit Schools text-entry limits are used;
other unresolved per-field engine limits are identified, not guessed from
existing names. See ROSTER_SCALE_AND_PREVIEWS.md; this work is not yet released.
Verified references,
ratings, attributes, packed equipment/appearance and school fields use their
declared masks. Opaque fields remain read-only. Palettes have 22 exact captions,
three additional runtime roles and six unresolved words. Optional D1/conference
updates and alternate operations are explicit actions; never automatic conversion.
See projects/README.md and CURRENT_STATUS.md for exact evidence and remaining limits.

```powershell
python -m choops_py.cli roster-detect output/rips/roster_english.iff
python -m choops_py.cli roster-export-json output/rips/roster_english.iff output/reports/roster_review
python -m choops_py.cli roster-save output/rips/roster_english.iff output/reports/roster_review/roster.json output/temp/edited_roster.iff --safe-only
python -m choops_py.cli roster-validate output/temp/edited_roster.iff
```

Edit only documented editable JSON fields. The source SHA256 must match. Alternatively use a patch with `source_sha256` and `edits`, each containing table/index/field/value and optional slot. Invalid pointers or references block saving. Save preserves source wrapper type, unknown bytes and unrelated IFF records, and emits a sibling edit report. Standard IFF compression rebuild must fit the original archive extent. Stage the saved copy as roster_english.iff and build a separate JB folder to use it.

## Team palette and stadium linkage

The team asset ID identifies the sXXX stadium art family; the team row index and arena reference index are separate identities. In Models / Courts, load the roster and use Linked roster palette to find the unique team whose asset ID matches the stadium filename. The Team palette dialog shows RGBA swatches, exact slot indices and contextual role candidates. Edits participate in undo/redo and copy-save validation. Candidate labels do not establish a particular shader channel or in-game effect.

Palette words are four RGBA bytes at team row +0x1A0 through +0x218 inclusive (31 slots). Repeated colors across school slots support primary/secondary candidate labels. The palette can contain white, gray and accent colors as well as school colors. Green regions in some arena textures may be shader tint masks; no automatic green-to-roster recoloring is enabled because channel-to-slot routing is unproven.

Research layout profiles header count/pointer anchors and record offsets. This
is structural coverage, not full semantic reversal. Verified fields have separate
executable-backed evidence; variable-length heaps and opaque fields remain unresolved.

## Executable-backed semantics

The editor derives table starts/counts from the header, including coach/conference
anchors. Team +0x48 is a relative conference reference; conference +0x6E0 begins
the observed team list. Optional D1 conversion updates reciprocal membership;
see projects/06-declone-d1-teams.md for current scope and limits.

All 30 attribute names are linked through localized UI registration metadata to the game's getters and setters. Ratings occupy player +0x3C through +0x76 as big-endian u16 values. The getter displays clamp(floor(raw / 100), 35, 99); edits store rating * 100, while untouched fractional values remain byte-exact. Player attributes shows these named channels. Four byte tendencies follow at +0x78..+0x7B. Potential is at +0x7F; confidence at +0x80. Packed weight and handedness edits preserve neighboring bits. Named appearance/equipment fields are readable; their enum choice meanings remain incomplete.

Edit Schools displays team records separately from players. The color dialog distinguishes raw palette slot numbers from the game's color-control indices. The observed getter/setter arrays expose 22 controls targeting slots 2–10, 12–15 and 18–26. All 22 exact English captions are traced through menu selection callbacks to their RGBA getters/setters. Repeated Primary and Secondary captions are kept literal and distinguished by control and raw slot. Court material IDs now route to the verified roster getters and DiffuseColor uniform; arena mask-channel routes remain unresolved. Other palette words are preserved and can be inspected. Slots 0/1/11 have verified runtime roles; 16/17 are school-colour runtime copies. Slots 27–30 remain unresolved.

Full roster semantic reversal is not complete. The local evidence ledger retains executable traces and unresolved questions; proprietary executable and language payload copies remain private. Public methodological references: [RPCS3 SELF implementation](https://github.com/RPCS3/rpcs3/blob/master/rpcs3/Crypto/unself.cpp) and [community conference parser](https://github.com/bphit4/CH2k8-Roster-Editor/blob/main/Conference_Parser.py). External offsets were checked against the stock roster rather than copied without validation.

Confirmed control captions in order: Key Circle Outer, Center Line, Outer Line, Skirt Inner, Skirt Outer, Lane Right, Lane Left, Key Hash, Center Circle, Top Key Right, Top Key Left, Primary, Secondary, 3Pt Line, Key, Key Line, Basket Front, Basket Rear, Basket Metal, Primary, Secondary, Tertiary.

Court preview uses a unique matching asset ID in the explicitly loaded roster, including unsaved edits. Verified RGB values are converted from sRGB to linear color; the runtime gray sentinel (RGB 190/190/190) leaves the authored preview unchanged. This reproduces the color binding with simplified preview lighting, not the full game shader.

Jersey number is the byte at player row +0x1B (name-anchor +0x0B), corroborated by its localized UI increment callback. The adjacent byte at +0x1A contains flags in some records and is preserved by number edits. Static number previews use authored font colours and placement; full dynamic recolouring remains unresolved.

In Team palette, select a swatch and choose Pick selected color (or double-click it). The picker provides numeric RGB inputs, visual color selection, and an alpha control initialized from the existing value. Accept applies an undoable edit; Cancel leaves the roster unchanged. Hex RGBA remains visible in the palette table.

Uniforms links owner/asset selector, variant, unlock ID and shape. Known shapes
U/V/V triangle/triangle/wishbone and selectors are editable. Alternate 1/2/3
availability controls remove/restore counted records; explicit builders may add
assets/links. Restored unlock IDs remain intact. Handedness uses L/R, booleans
Yes/No, home socks Black/White; unknown enums remain explicit. See project tracker.

Jersey side tabs offer numbers 0–99/00 or the selected player’s roster number, with authored Reborn surname lettering. Preview choices do not edit roster data.

Additional appearance/tattoo/post/free-throw fields and all 112 jump-shot captions are now supported; see ROSTER_SEMANTICS.md. Arena vertex-colour/alpha, lightmap, glow and flare routing is implemented; see ARENA_SHADER_MASKS.md for evidence and remaining runtime effects.

Text edits now grow beyond old allocations and keyboard entry capacities. The UI separates advisory game-keyboard sizes from unproved engine ceilings; structural pointer/UTF-16/adapter guards still apply.

## Explicit roster sources and exports

Roster controls explicitly open external roster IFF or decrypted USERDATA/USRDATA
(and supported save ZIPs), load the source JB roster, or load a real override
roster replacement independently of the preview dropdown. Export offers roster
IFF and decrypted USERDATA. An external IFF supplies its own export template;
other inputs use the loaded JB or a chosen IFF template. Save copy preserves the
original wrapper, including other members of a loaded save ZIP. USERDATA export
does not create encryption, PARAM files, or a complete console save package.
All writers validate and reparse the result and protect the original input.
