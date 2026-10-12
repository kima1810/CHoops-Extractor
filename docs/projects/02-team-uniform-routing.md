# Team and uniform routing

The ROST header at +0x70 describes an eight-byte uniform table. The engine's uniform lookup counts records belonging to a team, then selects the requested matching record in table order. It compares the record's owner with the team's asset identity.

| Uniform field | Storage | Evidence |
|---|---|---|
| Team owner | First word, bits 22–31 | Runtime uniform lookup and getter |
| Uniform asset selector | First word, bits 12–21 | Packed getter/setter |
| Variant code | First word, bits 8–10 | Runtime formatter: 0 Home, 1 Away, 2 Alternate 1, 3 Alternate 2, 4 Alternate 3 |
| Unlock ID | First word, bits 0–6 | Zero is unconditional availability; nonzero invokes profile unlock lookup |
| Jersey shape | Second word, bits 27–29 | Packed getter/setter and cloth filename dispatch table |

Shape dispatch: 0 U, 1 V, 2 V triangle, 3 triangle, 4 wishbone. The game's dispatch falls back to U for out-of-range codes. The Uniforms roster tab exposes the table, allows known shapes and existing asset selectors, and preserves all other bits. Save a roster copy and stage it normally. Offline structural validation does not establish gameplay consumption of an edited shape.

Runtime bank prefixes are `uh`, `ua`, `ux`, `uy`, and `uz`. Uniform and `selu` menu-selection filenames use the record's asset selector, independently of its owner ID. Archive naming includes all five banks and ten-bit selectors. The preview selector changes only preview images.

The copied-JB alternate builder clones uniform and menu-selection art and appends a team-owned record with unlock ID zero. Existing unlock IDs remain intact. Notre Dame's stock owner has all five banks; one record carries unlock ID 95. Full profile/UI behavior has not been validated in game.

Alternate availability checkboxes remove/restore the corresponding record in the counted list. Restored records keep their original unlock ID; enabling a linked record does not bypass profile unlock conditions. Missing asset banks require the copied-JB builder. Five-bank builds are explicit operations and preserve team classification.
