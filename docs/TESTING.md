# Testing and regression maintenance

## Reproducible portable checks

```powershell
python tools/dev/setup.py
.\.venv\Scripts\python.exe tools/dev/verify.py
```

The runner checks generated handoff freshness, compiles Python, runs synthetic/Qt
pytest cases, CLI help, offscreen GUI startup, fatal-error lint, scoped typing and
diff whitespace. CI runs on Windows and Linux. Capture the exact commit, command,
pass/skip/deselection counts and unavailable dependencies in TEST_REPORT/PR.

Before reviewing another PR, inspect its diff/dependencies/scripts, then test the
exact head in an isolated checkout. Use `--python` with an existing environment
when appropriate; ensure imports resolve to that checkout. New commits invalidate
old exact-head evidence. Public jobs must not receive private games or tokens.

## Regression map

| Risk | Main test modules |
| --- | --- |
| Split banks, TOC layouts and opaque header bytes | test_dynamic_2k_archives, test_split_archive_header, test_archive_identity |
| SDAT authentication/read boundaries | test_sdat_2k14 |
| Newer IFF/ZLIB/scene descriptors | test_nba14_formats, test_standard_iff, test_compression_rebuild |
| Transactional output, relocation, preserved bytes | test_modding, test_build_streaming, test_asset_insertion |
| DDS layouts, CDF/SCNE packing, overrides | test_builtin_conversion, test_runtime_texture_layout, test_scene_image_packing, test_cdf_folder_import |
| Concurrent preparation and cache/source routing | test_parallel_overrides, test_cache, test_live_override_previews, test_preview_source_caching |
| Roster bits, wrappers, identity and batch review | test_roster_editor, test_roster_semantics, test_roster_bulk, test_roster_csv_fields, test_nba_rosters |
| Side editors, school assignment and footwear | test_roster_side_panels, test_school_assignment, test_shoes |
| Reference guides and authored uniform artwork | test_scene_palette, test_jersey_preview, test_uniform_preview, test_scene_number_gl |
| Audio queue/writers and output destination | test_audio, test_audio_batch, test_audio_queue_build_outputs |

Read the code for fixture-specific scope; a suite name does not imply all semantics
are understood. Keep rejection, untouched-byte, aliasing, rollback and cancellation
coverage when consolidating modules. In v1.18 the small wrapper regression moved
into test_binary.py; no assertions were discarded.

## Optional and forbidden checks

`real_game` and `runtime_manual` markers and the optional legacy native comparison
are excluded by the portable runner. Offscreen OpenGL, absent native codecs and
private fixtures may explicitly skip. A skip is not a pass. Read-only supplied-input
checks may inspect archives/metadata and in-memory round trips without modifying
originals. Never run verify_game.py --build, create a full automatic/testing JB,
launch RPCS3 or edit EBOOT. Tiny synthetic archive fixtures are allowed.

## Windows package verification

Use the exact release commit. Run packaged `--smoke`, `--audio-codec-smoke` and
`--cli --help`. Test extraction/format paths using read-only supplied or synthetic
inputs. Check source-schema handling and preservation with synthetic builders,
not a copied game. Validate the ZIP after creation, include its SHA-256, and pair
LGPL helpers with exact matching sources/notices. Record what was skipped.

## Cleanup policy

Remove superseded generated logs, bytecode/pytest caches and owned temporary review
checkouts only after checks finish and required evidence is recorded. Resolve and
check absolute paths before recursive removal. Preserve regression tests for
supported legacy formats, real user overrides/builds, private evidence and original
game files. Do not delete a test just to make a failure disappear.
