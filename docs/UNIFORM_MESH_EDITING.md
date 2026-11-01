# Experimental editable uniforms and modern fit

Models / Courts now has **Uniform meshes…** with export-all, experimental modern
fit and collection reimport actions. Export uses the global **Preview source**
selection, including source-bound complete overrides. Outputs are separate
collections under `output/uniform-models/`; imports create a new
`output/uniform-imports/` folder. Sources and existing outputs are never replaced.

## Coverage and preset

Read-only inventory of the supplied College Hoops 2K8 PS3 source found:

- Five necklines: U, V, V triangle, triangle and wishbone.
- Thin, regular and fat builds for each neckline, plus three shorts builds.
- 21 IFF containers / 33 SCNE–Clth record pairs. This includes the aggregate
  containers and the individual build containers, so both existing resource
  routes are represented. These are 18 distinct garment/build combinations;
  the duplicated routes are not additional jersey styles or new team alternates.

`modern-fit-2` raises the shorts hem by 20% of that mesh's original vertical
extent, fading to zero displacement at 65% of its height so the waist and upper
hips remain fixed. The deformation is monotonic in height; no rows are cut off.
Jersey torso X/Z are reduced by up to 7%, with smooth fades at the bottom and
above the mid torso. The upper 28% stays fixed, preserving the collar/upper
armhole region. This changes existing shared meshes for all schools using them;
it does not change team artwork, body/build selectors, roster records or EBOOT.

## Editing and reimport

The collection contains `originals/` IFF copies, editable `models/` OBJ cages and
source-bound manifests. Modern-fit collections also include untouched
`original-models/` OBJ cages and ready experimental replacements in `overrides/`.
Select **only `overrides/`** in Explorer to prepare the edited game assets. The
collection root includes originals and must not be used as an overrides folder.
Do not mix complete cloth IFF replacements with a different cloth geometry mod.

The OBJ preserves original vertex indices, per-vertex UVs and expanded strip
triangles. Coordinates are unchanged native units, Y up. In a DCC editor, preserve
vertex order and axis conversion on export. Do an untouched roundtrip before
editing: DCC versions may reorder faces or vertices. No welding, subdivision,
triangulation, decimation, vertex deletion or UV editing is supported. Move
coincident seam duplicates together. OBJ normals are ignored; native packed
normal/tangent attributes remain byte-exact. No external DCC application has
been certified by this change.

Choose **Reimport edited uniform models…**, selecting the collection root.
The importer checks the original IFF hash, manifest identities, ordered triangles,
vertex count, UV identity, sewn particle agreement, finite coordinates, a maximum
20-unit displacement and collapsed/flipped triangles. It updates XYZ in
SCNE vertices and their exact matching Clth rest particles, plus the observed
packed stretch/bend distance fields. Unknown attributes,
UVs, skinning-associated stream bytes, indices and helper particles are retained.
The observed stretch/bend distance fields are scaled by the ratio between edited
and original particle separation, preserving authored prestrain and slack. Unsupported declarations and ambiguous matches fail explicitly.
Collection operations are cancellable; a failed/cancelled collection may contain
completed files but has no final success report. Choose a new empty destination
for retry. Each individual IFF is fully validated before writing.

CLI equivalents, always writing under project `output/`:

```powershell
python -m choops_py.cli export-uniform-models SOURCE_JB output/uniform-export
python -m choops_py.cli modern-fit-uniforms SOURCE_JB output/modern-fit
python -m choops_py.cli import-uniform-models output/modern-fit output/edited-cloth
python -m choops_py.cli export-uniform-iff cloth_u.iff output/u-models
python -m choops_py.cli import-uniform-iff cloth_u.iff output/u-models output/new-cloth_u.iff
```

## Confirmed binary evidence and limits

The observed embedded SCNE has one mesh/instance, three streams with strides
4/24/4 and six exact declarations. Float32 big-endian XYZ occupies the first 12
bytes of each 24-byte vertex in stream 1. Stream 0 holds signed-normalized UVs;
stream 2 and the remaining vertex bytes are preserved. Existing triangle-strip
indices and draw data stay unchanged. No general-purpose SCNE writer is enabled.

In matching Clth records, the first big-endian uint16 is the rest-particle byte
extent. Absolute offsets at `0xc0` and `0xc8` bound that table; their difference
equals this extent. Each particle is 16 bytes: matching float32 XYZ plus 1.0.
All 33 supplied graphic records have unambiguous exact matches to this bounded
table. Several rendered seam vertices share a particle. Unmatched helper
particles and zero-initialized workspace are retained. This mapping establishes
rest-position editing, not the semantics of every Clth byte.

Writers preserve logical record addresses and sizes. Physical compressed sizes
can grow; the existing archive relocation workflow handles a larger replacement.
Every written IFF is reparsed; all changed and unchanged record slices are
compared against the expected bytes. No-op OBJ roundtrips are byte-identical.

**This is experimental.** Stretch/bend rest distances are adapted; collision
geometry, other solver parameters and normal/tangent regeneration are unchanged.
Animation may still show body clipping or shading differences. Rest-pose comparisons and
successful import/preflight cannot establish the animated result. Do not call
this a finished cloth-simulation port. No RPCS3/gameplay or real JB build is run.
NBA garment layouts and arbitrary new topology remain unsupported.


## Runtime correction: cloth distances and resource routing

The earlier rest-only package left both native distance tables unchanged. That
was an incomplete shape edit: the solver still enforced the original distances.
This is a confirmed omission, not proof of what was installed on an external PC.

Read-only native analysis establishes the following CH2K8 PS3 routes:

- Native `0x57F4B4` selects the five archive names at `0x934148`:
  cloth_u, cloth_v, cloth_vtri, cloth_tri and cloth_wishbone, all `.iff`.
  `0x57F4D4` reads the player's neckline and falls back to U outside the valid range.
  Requests at `0x57FEE4`/`0x57FFA0` use that selector for the two teams.
- `0x4DB324` resolves paired SCNE/Clth resource IDs. The jersey record table at
  `0x10016554` is five necklines by five body selector slots; slots 0/1 map to
  thin, 2/3 to regular, and 4 to fat. The shorts table at `0x100165B8` uses the
  same build aliasing. Each ID equals the case-sensitive CRC32 of the corresponding
  `jersey_<neck>_<build>` or `shorts<build>` record name. This establishes the
  shared garment resources used by the model loader, rather than team DDS artwork.
- Aggregate and individual build IFF routes both remain in the collection.
  The 18 distinct garment shapes cover 45 jersey-build/shorts-build pairings.
  A combination package changes its named shapes; it does not force roster selectors.
- The executable's cloth SPU image descriptor is at `0x12502A00`; its code source
  is `0x124FF600`, length `0x33B0`, local address `0x80`. This is read-only evidence.
  SPU routines `0x1260` and `0x1568` consume tables at Clth `0xD4`/`0xD8`.
  Counts are the big-endian uint16 fields at +4/+6 shifted right three.
- Each 48-byte batch has eight packed edge words and sixteen response bytes.
  A = word >> 20; B = A + (word & 1023). Distance = ((word >> 10) & 1023) / 32.
  Aligned vector loads discard the low four address bits occupied by distance.
  The response bytes, particle indices and self-edge padding remain unchanged.
  Replacing bend distances with geometric distance would discard authored prestrain;
  the writer instead scales each existing distance by new separation / old separation.

The importer adapts these fields for arbitrary supported OBJ edits as well as the
modern preset, rejects malformed tables and unrepresentable distances, reparses the
IFF and checks every untouched logical byte. An unchanged OBJ remains byte-identical.
No EBOOT patch is needed or produced. Native routing and offline consistency do not
certify animated appearance; the tester must verify the rebuilt JB and test in game.
