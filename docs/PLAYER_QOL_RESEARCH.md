# Player editing and scholarship evidence (v1.10)

The v1.10 editor shows player details without a separate properties/attributes
button. Player, Ratings and Scholarship tabs share the existing validated model,
undo/redo and save-copy/export services. Names retain equal encoded lengths.

Height stays an integer byte at player row +0x3A and sorts numerically; only its
presentation/input changes to feet/inches. Position stays the whole byte +0x3B,
using 0 PG, 1 SG, 2 SF, 3 PF, 4 C. Edit-player getter/setter 0x69DAA8/0x69DABC
read/write anchor +0x2B; the runtime getter 0x753104 reads the same byte. All 5,685
stock player values fall in that five-value set. It is a single confirmed position
field, not two packed primary/secondary nibbles. No independent secondary field
has been established; the editor does not expose a guessed second position.

## Scholarship / walk-on

The localized Scholarship control (English key 0x360FDA01) is registered in the
edit-player constructor at 0x6971FC, with callback 0x68FE40. That callback toggles
bit 31 of a big-endian word at player anchor +0x8C, equivalent to model row +0x9C.
The name formatter at 0x69F30C tests the same signed word. Its nonnegative branch
at 0x69F3E4 uses suffix key 0xDEBE7B99 (walk-on); the negative branch uses the empty
suffix key 0x3729608D. Thus **bit 1 = Scholarship; bit 0 = Walk-on**.

The stock roster contains 5,166 set flags and 519 clear flags. These counts are
cross-checks, not format requirements. The editor masks only 0x80000000 and preserves
weight (bits 11–19) and all neighboring data. Tests check exact payload changes,
undo/redo and visible selection continuity. Recruiting-menu eligibility callback
0x68F974 has roster/context restrictions; this offline editor changes roster data
and does not claim to reproduce those Legacy restrictions or validate gameplay.

## Equipment and readable values

One-bit data uses established captions: hand L/R, muscle tone Buff/Ripped, sock
colors Black/White. Equipment bands/pads are multi-valued, so treating all codes
as booleans would be incorrect. Localized option arrays supply None, White Pad,
Black Pad, team-color variants and other styles for the established packed getters.
Unconfirmed left-arm styles remain read-only and display None/Style rather than
an invented semantic label. Confidence, potential, ratings and tendencies remain
numeric quantities. Unknown source enum values are preserved unless edited.

## Scope removal

Schools combines the former Teams/Edit Schools views. Realignment remains a
reciprocal conference-membership action without a conversion checkbox. Player
properties/attributes buttons, D1 conversion, alternate availability/creation,
five-jersey builds and independent-asset buttons are absent. Public CLI commands
for new alternate/archive insertion are no longer registered. Lower-level research
code/history is retained; no alternate assets are created or added in this update.

Executable/stock inputs were inspected read-only and are not distributed. EBOOT
is not modified. No emulator or automatic testing JB is used for this release.
