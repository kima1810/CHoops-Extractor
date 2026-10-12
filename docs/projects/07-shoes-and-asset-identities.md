# Shoe assignment, preview and archive identities

The executable's player-to-team assignment routine copies four team shoe defaults into the player: manufacturer, style, home color, and away color. Players retain their own packed values afterward. The stock current-school data has a team manufacturer matching every active player on 336 consistently assigned teams; all 11,370 player home/away texture paths resolve to existing archive hashes.

Offsets below use the editor's existing legacy row starts. The executable's player anchor is 16 bytes later and team anchor is 48 bytes later.

| Field | Team offset / shift / width | Player offset / shift / width |
|---|---|---|
| Manufacturer | 0x2E8 / 20 / 3 | 0xA8 / 29 / 3 |
| Style | 0x2E0 / 22 / 5 | 0xA0 / 27 / 5 |
| Home color | 0x2E0 / 17 / 5 | 0xA0 / 22 / 5 |
| Away color | 0x2E0 / 12 / 5 | 0xA0 / 17 / 5 |

The assignment copy is at executable routine 0x7646D8 onward. The filename formatter at 0x728AD8 uses manufacturer base codes (0, 100, 200, 300, 500), style, and the selected home/away color. Generic shoes use shoe_0.iff / shoe_1.iff; branded styles use shoe_MODEL_COLOR.iff with two-digit color values. Getters 0x72965C and 0x729674 choose the home/away colors. The Edit Player color cycling/display routines use manufacturer-indexed lists: two colors for generic and special styles, sixteen for the regular branded families. These are finite style/color packages, not a separate set of textures for each school.

The stock archive contains 90 shoe texture packages: 2 generic, 48 Nike (three styles), 16 Reebok (one style), 16 Adidas (one style), and 8 special-family packages (four styles). Special-family art includes Jordan branding; its exact original UI manufacturer caption has not been recovered. Regular color captions are White, Black, Red, Yellow, Blue, Green, Orange, Purple, followed by Black / White through Black / Purple. Exact commercial style names have not been mapped, so editing uses artwork IDs. Player assignments and school defaults are writable through **Edit shoes…** and the confirmed scalar fields. The writer changes only the declared bit masks, validates the combined brand/style/color selection, and records one atomic undo entry. Changing school defaults does not silently rewrite current players.

## Preview

Models / Courts has a searchable shoe-artwork list and **Preview selected shoes**. **Preview assigned shoes…** in the roster editor selects a player's current shoe package or a school's default for Home/Away. The standalone hi_shoe1 SCNE is found in the current JB folder by verified container contents. Its original filename is still unresolved; its stable TOC hash is retained. The packed signed-short position and UV declarations contain scale/bias vectors; decoding them yields 885 triangles. Embedded 60-byte material records name eight parts. sole_mat uses shoe_sole; fastener, midsole, toe, heel, logo, hitop and upper use shoe_upper. The preview is a static shoe silhouette; selecting artwork does not claim to reproduce model-specific gameplay shape or full shaders.

TXTR/GTF descriptors contain RSX channel remapping. Some white/black shoe textures store luminance only in green, with descriptor 0xA9A8 selecting green for RGB and constant alpha. Applying descriptor routing fixes their false-green preview. The identity mapping is 0xAAE4. This read-only preview conversion does not change texture export/import bytes. The [RPCS3 texture implementation](https://github.com/RPCS3/rpcs3/blob/master/rpcs3/Emu/RSX/RSXTexture.cpp) provides the primary-source RSX remapping reference. Specialized high-word remap orders remain unsupported.

## Naming hashed assets

The archive stores CRC32 identities rather than filenames. New built-in patterns recover the shoe packages and thin/regular/fat cloth containers. Additional executable literals are kept in a small verified name table. On the stock fixture, 3,343 of 3,376 entries have canonical name candidates matching their CRC32 identities.

**Identify unnamed assets** reads bounded IFF metadata, tries internal names as filename candidates, and labels remaining containers with their internal SCNE/TXTR records. **Match filename list…** accepts a UTF-8 list of candidate filenames. Only candidates whose CRC32 matches a TOC identity can become canonical names; conflicting candidates are left unresolved. CRC32 alone is not an invertible or globally collision-free naming scheme. Internal-record labels are display hints, never substitute archive identities. Results are cached against bank size/mtime fingerprints and reused only for the same source state. Original archive files are never renamed or rewritten.

Synthetic tests cover packed coordinates, shoe fields, material names, remapping, cache invalidation and name/hash separation. Real-source checks cover all stock player texture routes, shoe selection and native OpenGL rendering. Gameplay verification remains pending.
