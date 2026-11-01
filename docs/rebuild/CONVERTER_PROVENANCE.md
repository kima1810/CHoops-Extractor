# Built-in texture conversion and historical converter provenance

DDS import, DDS export, texture previews and override-folder imports now use the
independent Python implementation in `choops_py/texture_tools/builtin_converter.py`.
No external converter executable is required. Supported formats are L8, ARGB8,
DXT1, DXT3, DXT5 and RGBA16F, including mip chains and complete cubemaps. Compressed
image blocks are preserved without recompression. Uncompressed conversion handles
RSX Morton order, endian conversion, row pitch and cube-face storage.

Generated fixtures cross-check descriptors and both conversion directions against
the historical tools. These tools are optional local reference oracles; their
implementation code is not copied into the built-in converter. Public hardware
format references and existing bounds-checked format readers supply the layout
knowledge. An explicitly supplied reference-tool path can still run an external
comparison; default operation always uses built-in conversion.

The optional archive acceleration library is built from this repository's own
`choops_py/formats/native/h7a.c`, with its accompanying MIT license. A portable
Python codec remains available. Neither the compiler nor historical converters
are bundled in Windows releases.

## Historical binaries

Historical binaries can remain as optional local reference tools, but are not
distributed in the current source tree or Windows package:

| File | Bytes | SHA-256 |
|---|---:|---|
| gtf2dds.exe | 161280 | b0533529413ffc41f0d0de02602c1223d2be555455d950e89bd22c529c928a5d |
| dds2gtf.exe | 135168 | bcb75ca129ede3708d699510830a85288b47f0f36536930f54aff763991929d2 |

The legacy audit records byte-identical copies in both historical trees. No redistribution grant was found accompanying these executables. They remain excluded from public Windows packages; their licensing is no longer a dependency of normal texture conversion.

Actual subprocess tests run on Windows with generated L8 and DXT1 DDS/GTF fixtures. Arguments, exit status, stdout/stderr, metadata and DXT1 payload equality are recorded in ignored conversion JSON reports. Tools run without shell=True. Input/output filenames are individual arguments. Unknown layouts and failed conversion outputs are preserved as raw data or rejected explicitly.

Public build workflows exclude the historical converters and all game assets. Optional local reference-tool copies do not become part of the released app.
