Current NBA extension: see [NBA roster/container support](NBA_ROSTERS_AND_2K14.md) and
[animation portability research](ANIMATION_PORTABILITY.md). Those pages define the
newer per-game boundaries; historical College Hoops-only statements below remain
specific to that earlier scope. NBA 2K14 SDAT rebuilding and complete NBA ratings
semantics are not implemented.

## Shared 2K compatibility boundary

The editor auto-detects two verified PS3 TOC schemas, not arbitrary game formats.
College Hoops 2K8 and the supplied NBA 2K9 copy have read-only extraction/preview
evidence; both writers have synthetic round-trip evidence. Other years/platforms,
unknown resources and gameplay need further verification. NBA roster semantics,
number placement and dynamic shader behavior are not established. See
PS3_2K_ARCHIVES.md. College Hoops-specific roster features remain available.

## Current continuation evidence

Floor alignment guides are independent flat-colour stock S256 reference geometry,
raised 1 game unit. They never hide real floor materials or apply roster colours.
Without the source reference they are unavailable.
Conference logos have verified logo900+index routing; the separate
tournament index is protected pending a backlink writer. Animation clips can be
identified/extracted as raw SingleMoCap blocks, without decoded skeletal tracks.
Orange text warnings concern confirmed keyboard buffers, not proven engine caps.
Secondary positions are closed by owner confirmation and are not being searched.
Unknown roster bits, reflection/fake-bump/AO and all runtime palette modes remain
unestablished. See the current evidence docs; older dated limits below are history.

# Current evidence boundary

Arena vertex colour/alpha, lightmap, glow and flare masks are now supported;
ARENA_SHADER_MASKS.md distinguishes them from unimplemented dynamic lighting/AO.
ROSTER_SEMANTICS.md records new appearance, tattoo and signature edits. Complete
semantics for all roster bytes, all engine text ceilings and remaining runtime palette links are not certified. Earlier notes
that describe these newly mapped controls as unavailable are superseded by these
evidence documents. Source data, EBOOT and unknown bits remain preserved.

# Current limitations

The scale branch remains incomplete semantic reverse engineering. Confirmed Edit
Schools entry capacities are mapped; conference/coach/singular-mascot limits and
the renderer's broader text ceiling, arena shader channels, number geometry/colour and
Secondary-position research is closed by owner confirmation. CSV/comparison use supported
writers and exclude ambiguous references. Text growth is structurally tested;
game runtime remains unverified. See ROSTER_SCALE_AND_PREVIEWS.md.

v1.11 transfers/brand propagation reject shared or inconsistent ownership and full
18-player destinations. Whole-table older 16-slot JSON exports need refreshing.
Static jersey preview has authored number/Reborn overlays; runtime cloth, skinning and animated bodies are not reproduced.
No automatic Legacy eligibility/scholarship enforcement or gameplay guarantee.

v1.10 removes D1 conversion and new alternate/independent-asset actions from the
public editor/CLI. Single position and Scholarship/Walk-on are confirmed; secondary
position is unproven and not exposed. See PLAYER_QOL_RESEARCH.md for evidence.

Updated 2026-10-11. CURRENT_STATUS.md and TEST_REPORT.md are the living evidence.

- Python/Qt checks do not establish game behavior. Agents never open RPCS3 or
  create testing JB folders; users build/test their own copies.
- DDS/GTF conversion is built in. Unknown TXTR layouts, DX10 and volumes with
  more than one stored slice remain unsupported. Single-slice 3D descriptors
  accept 2D artwork while preserving their descriptor. Unused stored depth on
  declared 2D/cubes is tolerated.
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

## Experimental uniform mesh edits

Known College Hoops garment OBJ reimport edits both visible and cloth rest XYZ.
Observed stretch/bend distances are adapted; collision, other solver parameters
and normal/tangent regeneration remain unchanged. A static modern-fit preview is not an animated fit certification;
see [uniform mesh editing](UNIFORM_MESH_EDITING.md). No arbitrary topology/NBA writer.
