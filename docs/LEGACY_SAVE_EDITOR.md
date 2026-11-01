# Legacy save editor

## What the current save establishes

The supplied Legacy-mode `USERDATA` is not a standalone IFF archive. It has a
16-byte observed signature, followed by a roster-shaped payload beginning at
offset `0x438`. That payload is `0x003DF800` bytes and passes the existing roster
table parser and structural validation. The remaining header and mode-specific
bytes are preserved as opaque data.

This is evidence for one observed profile only. It does not establish that all
Legacy saves, regions, game revisions, or save states share this layout.

## Current editing behavior

Open the save in **Roster / Legacy save editor**, edit fields already supported
by the roster editor, and use **Save copy**. The writer overlays the roster at
its original offset and verifies that every byte outside the roster region is
unchanged. Text edits that would change UTF-16 storage length are rejected so
they cannot shift data in the enclosing save. Exporting a detached USERDATA
payload is disabled for this profile because it would omit the surrounding mode
state.

The editor changes only the confirmed roster fields. **Recruiting diagnostics…**
now opens a read-only, searchable view of the native recruit table: HS/JUCO class,
commitment, location ID, preference profile/weights and metadata issues. Missing
or malformed tables are reported as unavailable; no speculative fields are
made editable. The view does not certify available recruit slots or full interest
and history semantics. See [LEGACY_TRANSFER_PORTAL.md](LEGACY_TRANSFER_PORTAL.md).

The requested transfer portal must operate fully in game while preserving player
statistics and historical school associations. No external save-editing, transfer
plan application or signing workflow is added. The native portal remains
unfinished. Season, schedule, progression and other unestablished Legacy-specific
data stay unchanged. The earlier request was to make all Legacy data editable;
that broader support is not yet implemented because this single save cannot
show which opaque bytes correspond to which values.

## Evidence needed to map more fields

For each field, provide two copies of the same save slot: one before changing a
single known in-game value and one after. Keep other actions and settings fixed.
The files can remain private; report the changed value and its meaning so the
byte diff can be correlated. Repeating this for each field makes it possible to
separate values, counters, checksums, and regenerated blocks before adding an
editor or writer. Never use a valuable original as an editing test target.

Until those comparisons are available, opaque mode bytes stay read-only.
