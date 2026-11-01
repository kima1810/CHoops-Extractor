# Selected-record side panels (v1.11)

Select one row in Players, Schools, Arenas, Coaches, Conferences or Uniforms.
The right pane changes to that category. Double-click a writable detail; references
use named selectors and existing validated model writers. Read-only metadata
remains marked. The Edit selected, Team palette and separate shoe toolbar actions
are removed. Existing save, export, undo/redo and known field editing remain.

Schools have School, References, Players, Palette, Shoes and Jersey tabs. Palette
opens the RGB/alpha picker directly from its swatches. References include safe
reciprocal conference realignment. Players exposes all **18** roster slots, with
count updates and guarded transfer/reordering. Coaches/Arenas/Conferences expose
their supported strings/scalars; Conferences also lists member schools. Uniforms
expose their existing writable selectors/shapes and a jersey preview tab.

## Player school assignment

The player School tab shows current ownership and allows move/unassign. The game
uses a team player array at runtime anchor +0x3C and a count at +0x158, corresponding
to editor row +0x6C and +0x188. Removal routine 0x7644B8 walks that array; assignment
routine 0x764548 onward checks capacity, appends a player and increments the count.
The mapped file pointers use player row +0x11 and signed self-relative deltas.

The stock data confirms 18 contiguous pointer slots, including the previously
hidden final members of 17/18-player schools. All 443 stock arrays agree with
their counts. Player row zero is a real Charlotte member, not always an empty
sentinel: an active slot may name it, while row-zero references beyond the active
count are empty. The reader now makes that distinction.

Transfers update source/destination arrays and counts in one undoable transaction.
Player attributes and current footwear remain unchanged. Full destinations,
duplicate/shared player records, invalid pointers and inconsistent/unmapped counts
are blocked with no partial change. Roster-slot editing uses the same guarded
membership writer; choosing an existing teammate swaps positions, removing a
member compacts slots, and incoming players transfer safely. Legacy recruitment,
eligibility and scholarship limits are not reproduced; gameplay is unverified.

Whole-table JSON exports now contain 18 slots. Refresh older 16-slot exports before
applying them; guessing omitted players or silently deleting row zero is unsafe.
Individual edit patches remain supported through the guarded writer.

## Shoes

Player and School Shoes tabs contain brand/style/home/away controls and a direct
preview button. Player edits affect that player record. Applying school shoes
automatically applies its brand to **that school’s roster only**, as requested.
Compatible player styles/colors remain; incompatible values use the first valid
choice for the new brand. School style/color defaults do not overwrite compatible
individual artwork choices. Shared player records block scoped propagation.
The school/default/player updates form one undo step and preserve unrelated bits.

## Jersey preview

Player, School and Uniform side panes offer direct Jersey preview of linked,
existing artwork. Models/Courts then shows neck, jersey build, shorts cut and
Top + shorts / Top only / Shorts only dropdowns. Neck choices are U, V, V triangle,
Triangle and Wishbone; available cloth bodies/cuts are Thin, Regular and Fat.
Existing top/short meshes are combined in their original coordinates and their
texture roles are routed independently. No artificial repositioning is applied.
These dropdowns affect the preview, not saved roster shapes. Static cloth preview
does not reproduce skinning, cloth simulation, player body or runtime name/number
overlays. Opening another JB clears prior preview context. No assets are added.

Stock verification used read-only source inputs: row-zero transfer/undo, scoped
brand propagation/undo and actual combined jersey+shorts geometry. Synthetic
tests cover guarded writes, field editing, palettes, references and texture roles.
No RPCS3, EBOOT writes or automatic testing JB is involved.
