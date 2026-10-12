# Current limitations

Updated 2026-10-11. CURRENT_STATUS.md and TEST_REPORT.md are the living evidence.

- Python/Qt checks do not establish game behavior. Agents never open RPCS3 or
  create testing JB folders; users build/test their own copies.
- DDS/GTF conversion is built in. Unknown TXTR layouts, DX10 and true volumes
  remain unsupported. Unused stored depth on declared 2D/cubes is tolerated.
- Validated standard IFF/TXTR/SCNE growth and archive relocation exist. Unknown
  pointers and aliases remain blocked; general CDF virtual/physical growth is
  unresolved. Do not apply obsolete same-size rules to every supported writer.
- Six team palette words and full arena shader masks remain unresolved. Preview
  lighting, cloth/skinning, jersey glyphs and material effects are simplified.
- Roster names generally need equal encoded length/unshared storage. Encrypted
  saves need external decryption. Community wrappers are preserved; invalid
  pointers/new corruption remain fatal. Unchanged bad name characters are warnings.
- Alternate/linking operations and optional D1 conversion exist, but complete
  game/profile unlock behavior and independent decloned IDs need validation.
- Shoe editing uses verified brand/style/color ranges and artwork IDs; commercial
  style names and the exact special-family manufacturer caption are unresolved.
- 4096 is a court texture dimension ceiling, not a tested safe GPU allocation.
  Floor template preparation disables only extra floor draws, preserving arena.
- Audio has an experimental Python backend/CLI and a shared-backend Qt workspace
  for Licensed Music, Fight Songs, WAV workflows and mapped cover art. Title/artist
  editing remains unavailable because archive-only routing is unproven; EBOOT
  writes are prohibited. Unknown AUDO loops are blocked and CDF audio growth is
  unsupported. The LGPL helper package has passed Windows CI on PR #6's current
  head; it remains an unreleased branch until review and publication.
- Outputs are constrained to output/. Game assets, exported music/art, private
  paths, logs, fixtures and EBOOT are not supplied publicly.
