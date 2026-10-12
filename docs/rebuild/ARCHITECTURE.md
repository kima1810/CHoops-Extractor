# Native studio architecture

The existing choops_py package remains the parser/writer source of truth. Migration is incremental:

- archive: split TOC/ranged IO, identities, hashed staging, transactional JB builds.
- formats: bounded IFF/CDF/H7A/TXTR/SCNE/wrapper readers and conservative writers.
- roster: source adapters, validated model, undo/redo, copy-save and reopen checks.
- texture_tools: one shared DDS/GTF pipeline, original converter subprocess contracts.
- studio/services.py: streaming extraction, materialized private inspection copies, paired folder import and source preconditions; imported by both GUI and CLI.
- studio/app.py: Qt Widgets QMainWindow, virtualized tables/proxies, nested record tree, image preview, roster forms, builder and diagnostics.
- tools/rebuild: private real-game verification and PyInstaller onedir entry/build scripts.

Archive indexing is lazy with respect to payloads. Standard IFF span boundaries are precomputed once; duplicate starts remain detectable by the writer's overlap checks. Extraction uses 1 MiB chunks, cooperative cancellation, exclusive generated targets and per-entry SHA-256. Known IFF/CDF companions are included automatically.

Qt work runs on a bounded QThreadPool (one active operation). Signals return results on the GUI thread; progress is throttled to 10 Hz and normalized before 32-bit Qt integer emission. Widget logs are capped at 1,000 lines. Raster decode uses Pillow in a worker; QImage/QPixmap are created on the GUI thread. Selected assets are inspected from private scratch copies; the source game is never a save target.

Folder staging matches canonical outer TOC names, rejects links/unknown names, preflights all replacements in an owned temporary workspace, and records original entry hashes as source preconditions. Builders validate these before copying. Build publication is transactional. Exact output patch bytes and every unpatched byte are compared with source before success.

Known architectural debt: app.py should be split into panel modules; legacy modules remain sparsely typed; caches still reparse the TOC, no SQLite persistent acceleration; output roots remain constrained to output/; conversion/parse jobs lack cooperative cancellation. These are explicit acceptance gaps, not finished features.

modding/patch_package.py writes source-bound XOR ZIP deltas, validates bounded ZIP members/checksums, reconstructs matching allocation-sized replacements and reuses the staging preflight. UI and CLI share this service. JB copy is chunked with cooperative cancellation during copy/verification; cleanup handles CLI interruption and never targets source.
