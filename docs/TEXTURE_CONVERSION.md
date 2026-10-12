# Texture conversion

DDS/GTF conversion is built-in Python for L8, ARGB8, DXT1/3/5 and RGBA16F, including
mips and complete cubes. Handles RSX endian/Morton/row-pitch/channel-remap rules.
No gtf2dds.exe or dds2gtf.exe is required. Legacy executables are optional private
comparison oracles and excluded from releases; see rebuild/CONVERTER_PROVENANCE.md.

Export supported raw/wrapped TXTR, IFF, paired CDF or SCNE textures with a manifest
and raw data. Unsupported conversion can retain raw exports; --strict fails instead.
Unknown descriptors/DX10/true volume layouts remain blocked. Declared 2D/cubes
ignore unused stored depth rather than being misclassified as volumes.

```powershell
python -m choops_py.cli export-iff-textures output/rips/ua000.iff output/rips/uniform --dds
python -m choops_py.cli replace-iff-texture output/rips/ua000.iff unif output/temp/edited.dds output/temp/ua000.iff --same-format-only
```

Recursive staging discovers modern/older layouts automatically, replaces supplied
SCNEs before artwork, and gives matching DDS priority over raw TXTRs. Non-stadium
artwork is normalized to the selected base JB's layout; stadiums retain supported
dynamic sizes. No version checkbox. Vanilla sizes require a vanilla source.

Validated standard IFF/SCNE payload growth and archive relocation are supported;
unknown shared ranges/offsets remain rejected. CDF uses validated paired edits,
not unrestricted relocation. Keep original headers/unknown bits/trailers and
unrelated records; reparse and compare untouched data. See SINGLE_SURFACE_COURT.md
for bump routing, floor-only draw suppression and texture memory limitations.
