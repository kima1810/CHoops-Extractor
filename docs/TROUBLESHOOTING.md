# Troubleshooting

Start with the persistent GUI **Problem / Suggested fix / Details** report. Keep
the exact named archive, record selector and expected/actual sizes in a bug report.
Do not replace a structural error with guessed identities or silently skipped bytes.

| Symptom | Meaning / next step |
| --- | --- |
| Incomplete archive header | Check all split banks and their names/sizes. The current reader follows header/TOC boundaries across banks. Restore a truncated or missing bank from the original; send the named details if it persists. |
| Geometry overlaps a texture image | The replacement image/geometry ranges cannot safely coexist. Use the reported record to check its SCNE and image layout; preserve the originals. Supported relocation is format-specific, not a blanket permission to overlap. |
| Unknown/ambiguous record or no unique archive record | The selector matches none/multiple destination records. Verify the correct source JB and rip identity, nested name/hash and CDF partner. Do not rename every record to a generic logo. |
| No archive folder for a numeric V5.5 path | Update Studio and select the folder against the matching vanilla JB. Numeric folders map to source TOC indices, so keep the original numeric folder names and use the correct source archive. |
| Not a standard PS3 IFF | Read the archive name, source/replacement role and hex magic. Raw TXTR/SCNE records belong under their archive record folder, not renamed to complete .iff files. Restore damaged containers from the same rip. |
| Base cubemap faces error | Update/reselect overrides: flat folder DDS imports update +X and preserve five base faces, including manifests. For complete replacement use a six-face cube. Direct texture imports remain strict. |
| Unsupported texture layout | Confirm 2D or a supported complete cube. A stored depth-one volume has specific support; true deeper volumes, DX10/arrays and unknown encodings remain restricted. |
| Overrides show JB fallback | Check the chosen root, recognized archive/SCNE structure and matching selector. Reselect after edits and inspect diagnostics. DDS must belong to the resolved override record. |
| Old artwork despite replacement | Check both selected SCNE and DDS paths, the global source dropdown and fallback labels. Compare source vs override, not just the IFF display name. Report the specific asset/record and folder structure. |
| Preparing DDS appears slow | First import validates/converts many images. Bounded workers and caches accelerate subsequent unchanged selections. Check progress/target details; do not assume loading archives performs the same work. |
| Output directory rejected | Use a new empty folder outside source, overrides and prepared workspace. Both parent/child overlap and overwrite are guarded; choose another drive if free space is insufficient. |
| NBA 2K14 build blocked | SDAT read support does not provide authenticated write/signing support. Extraction/preview is available; do not remove this guard to produce an invalid game. |
| Roster edit blocked | Confirm schema, pointer validity, wrapper and shared-string constraints. Previously observed bad characters are distinguished from newly introduced damage. Unknown bits remain opaque. |
| Orange name outline | Text exceeds a confirmed game keyboard capacity for that field. Review it; capacity is measured in the documented encoding/units, not arbitrary old allocation size. |
| Audio helper missing | Extract the full release. Source developers must build the pinned LGPL helpers; no proprietary DDS executable is required. |
| Windows app fails after copying just EXE | Restore the entire ZIP, including `_internal`. CLI smoke and audio smoke can separate Qt/runtime and codec failures. |

## Useful evidence for a bug report

Include version/source commit, operating system, game/title ID and detected layout,
workflow steps, exact error text and relevant small metadata. State whether the
preview is source/overrides/fallback and whether input was recently changed.
Do not upload game banks, copyrighted audio/art, credentials or private save data
to a public issue. Prefer a minimal synthetic reproduction. Logs/screenshots may
contain private paths; redact them before posting.

## Recovery

Original game/override inputs should remain unchanged. Keep your manually exported
roster/texture copies and any user-created builds. A failed/cancelled transactional
build should not be treated as a completed output. Report unexpected leftover
folders before deleting them; never bulk-delete a research directory to clear a
cache. The project does not launch RPCS3 for diagnosis or patch EBOOT.
