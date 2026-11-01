# Conference assignment, logos and tournament evidence

School → References → Conference shows the name and numeric index. Double-click
to choose an existing conference. This updates the school pointer, both member
arrays and their counts together, reparses and validates every reciprocal link,
and provides one undo step. Negative, out-of-range and Boolean indices are
rejected without changing bytes. Conference row ordering is preserved.

Conference → Logo → Edit / preview conference logo opens its exact
`teamselectlogo.iff` record in the texture editor. Use Import edited DDS to assign
different artwork, save a new paired bank, then stage that folder for your manual
JB build. The source/overrides preview selector controls the opened bank. This
changes artwork in the existing asset, without changing the conference identity
or adding executable/asset entries.

Read-only executable evidence: menu helper 0x6A0734 reads the selected conference
through 0x6A0668, adds 900 and calls the 0x4A1294 thunk to 0x7FD80. That formatter
uses `logo%3d` (TOC 0xA54AC8 − 0x6D28). 0x6E7120 repeats the same routing. Stock
records `logo900` through `logo938` corroborate the 39 conference indices. Higher
indices are not assigned speculative logo names. Explorer subrecord references
now include conference owners as well as schools.

Do not confuse this with conference raw +0x1A. Getter 0x73D808 resolves the
conference through 0x4A1FF4 → 0x1BD9E0 and loads that u16. Its consumers include
0x65A1E8 → 0x58F74C and 0x73D840 → 0x58C420, indexing a 97-entry tournament
table with stride 0xAC. The legacy `presentation_id` read key is retained for
compatibility, but its displayed label is corrected to Tournament index and
editing is protected until tournament backlinks have a validated writer.

These traces establish asset naming and structural assignment behavior. They do
not certify gameplay or establish full tournament/history semantics. No RPCS3,
EBOOT changes or automatic/testing JB folders are involved.
