# Single-surface court templates

In Models / Courts, choose **Prepare single-texture court…** and select the
user-supplied full-court ZIP. The tool writes a new folder under
`output/templates/`. It does not build a JB folder or alter the ZIP.

The prepared folder contains `s258/floor.scne`,
`s258/_floor.scne/texture_0.dds`, and
`s258/_floor.scne/texture_2.dds`. Copy these into your overrides. To reuse the
floor for another stadium, copy the contents into that stadium's `sNNN`
folder. Keep its own arena assets. The report records the resulting layout.

Only the floor surface draws. Paint, center-logo and line parts retain their
identities and geometry but have no draw runs. Unused texture slots retain
their IDs with tiny placeholder images. Imports recognize this draw/material
configuration and ignore DDS or raw texture replacements for its disabled
slots, preventing older extra floor artwork from restoring their memory cost.
The arena is neither copied nor changed by preparation.

Texture 0 holds the complete court artwork. Texture 2 now binds to the arena's
actual `BumpSampler` shader semantic, rather than remaining an unused albedo
mask. The preparation uses the clean raw `floor_normalglossdetail` TXTR:
the supplied exported normal DDS has scrambled pixels. The normal's red/green
components are repacked to the donor bump texture's DXT5nm convention, X in
alpha and Y in green. A second vertex stream supplies normal, tangent,
bitangent and secondary UV attributes. Original positions, indices, primary
UVs and instance transforms remain unchanged. The basic GUI preview displays
base color; it does not reproduce game bump shading.

## Resolution and memory

The prepared defaults are **2048 × 1024 DXT5** for the complete court and
**512 × 512 DXT5** for the normal, both with complete mip chains. Their
combined image allocation is approximately **3 MiB**, including the tiny
inactive images.

| Image dimensions | DXT5 including complete mip chain |
| --- | ---: |
| 512 × 512 | 0.33 MiB |
| 2048 × 1024 | 2.67 MiB |
| 2048 × 2048 | 5.33 MiB |
| 4096 × 2048 | 10.67 MiB |
| 4096 × 4096 | 21.33 MiB |

The RSX graphics library declares a **4096-pixel dimension ceiling**, also
consistent with its 13 supported 2D mip levels. See
[RSXGL texture constants](https://github.com/gzorin/RSXGL/blob/master/src/library/gl_constants.h)
and [RSXGL screen limits](https://github.com/gzorin/RSXGL/blob/master/src/nvfx/nvfx_screen.c).
Imports reject an image exceeding that dimension after any base-layout
normalization.

That ceiling is not a measured crash-free game budget. Two 4096-square DXT5
images require about 42.67 MiB before arena, player and other allocations.
The game's maximum crash-free court resolution has **not** been established
by the Python layout checks. The report explicitly records that runtime
validation is outstanding. Preparation does not open an emulator or create a
test game build.

## Automatic non-stadium normalization

Recursive override staging restores every supported texture outside `sNNN`
stadium archives to the selected base JB's dimensions, format, mip count,
channel routing and storage layout. This includes uniform/menu/gameplay
banks, raw TXTR replacements, complete IFF replacements, SCNE textures and
paired CDF banks. Replacement artwork remains the artwork being imported.
Scene geometry remains the replacement geometry. Inputs are not modified.

Stadium archive matching uses names and known filename hashes. Stadium
textures retain dynamic sizing within the dimension ceiling. There is no
format/version checkbox or special legacy-folder mode.

Use a vanilla JB as the source when vanilla resolutions are desired. A modded
source supplies its current layouts; the importer cannot recover an unknown
original size from an already modified source. Unknown or ambiguous reference
identities fail explicitly rather than borrowing another texture's layout.

Source CLI equivalent:

```powershell
choops prepare-court-template "court-template.zip" "output/templates/my_court"
```

Generated game geometry and artwork are local outputs and are not included
in the repository or Windows release.
