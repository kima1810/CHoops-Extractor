# Old tool architecture audit

The old sources are read-only references; no JavaScript tree is copied. Equivalent reader/writer versions are consolidated instead of retaining ripperV1/V2/V3 duplicates.

| Old module | Purpose and useful ported behavior | Python replacement | Parity / restriction |
| --- | --- | --- | --- |
| index.js, gui.js | Commands, pickers, logs, workflow | cli.py, commands.py, gui.py | Focused UI and shared registry; research panels removed |
| src/ripperV2.js, ripperV3.js, cache.js | Split archive TOC, hashes, namespace, rip | archive/usrdir_reader.py, cache.py, hash_names.py, ripper.py | Raw extraction/cache/name resolution implemented; candidates preserved in names.json |
| src/builder.js, buildCopy.js, importerV2.js, reverter.js | Staging and archive updates | archive/importer.py, build_copy.py | Transactional JB copy; never in-place vanilla edits; capacity growth blocked |
| parser/IFFReader.js, IFFWriter.js | Relative tables, slices, compressed blocks | formats/standard_iff.py, standard_iff_writer.py | Reader and bounded writer; unknown fields/name table retained, unchanged blocks exact |
| parser/PackageReader.js, PackageWriter.js | SCNE embedded texture layout | formats/package.py | Shared reader/same-size texture writer; geometry retained; geometry editing excluded |
| parser/ToolWrappedReader.js | 2kTl framing | formats/tool_wrapper.py | Read/write and strict bounds; wrapper preserved |
| choops/ChoopsTextureReader.js, ChoopsTextureWriter.js | TXTR descriptor/GTF image handling | formats/txtr.py, texture_tools/gtf.py, dds.py, pipeline.py | Inline/split/wrapped TXTR, DDS/GTF export/import; unknown layouts blocked |
| util/h7aCompressionUtil.js | H7A literal/backreference decompression | formats/compression.py | Bounds checked decode; preserve token plan when encoding modified blocks; growth capacity checked |
| src/cdfBackedIffExtractor.js, cdfTextureExtractor.js | Paired metadata/physical payloads | formats/cdf_backed_iff.py, texture_tools/pipeline.py | Paired decode/export, same-allocation payload writer; relocation blocked |
| src/teamselectlogoTool.js | CDF logo export/import | texture_tools/pipeline.py | Same shared CDF pipeline and manifest batch import; no separate competing writer |
| roster.js, src/rosterTool.js | Table fields, pointers, names and editing | roster/schema.py, adapters.py, editor_model.py, workflow.py, gui_editor.py | Confirmed safe fields plus preserved wrappers; speculative appearance/conference/prestige blocked |
| lib/gtf2dds.exe, dds2gtf.exe | DDS/GTF conversion | tools/ and texture_tools/external_converters.py | Both original binaries bundled and tested; Windows required |

Both reference sources contain identical converter bytes:

- gtf2dds.exe: 161280 bytes, SHA256 b0533529413ffc41f0d0de02602c1223d2be555455d950e89bd22c529c928a5d.
- dds2gtf.exe: 135168 bytes, SHA256 bcb75ca129ede3708d699510830a85288b47f0f36536930f54aff763991929d2.

Related texture export/import commands use one Container/Asset pipeline. Roster source detection/decoding/saving shares one adapter/model workflow. Compatibility modding modules delegate to the archive builder/importer. Additional skeleton modules were not introduced merely to match historical filenames.
