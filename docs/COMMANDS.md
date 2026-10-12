# Native rebuild additions

Experimental audio examples: [AUDIO_WORKFLOW.md](AUDIO_WORKFLOW.md). Commands:
audio-catalog, export-soundtrack, replace-song, import-audio-folder, export-audo,
replace-audo, export-jukebox-art, replace-jukebox-art. The Qt Audio workspace
uses the same Python services. The LGPL FFmpeg helper handles WAV conversion;
WAV replacement also needs the ATRAC3 encoder. Title editing is unavailable.
These commands create asset copies, not JB builds. Agents
must not use the manual build examples below.

`gui` now launches the PySide6 studio. `python -m choops_py.studio` supports --smoke and --game PATH. The packaged executable also accepts --cli followed by ordinary CLI arguments.

`extract-raw SOURCE OUTPUT [--file NAME | --index INDEX]` uses streaming paired raw extraction; `stage-folder SOURCE EDITED_FOLDER NEW_MOD_OUTPUT` automatically matches canonical filenames and stores original-source hash preconditions. Existing `rip` retains its decoded extraction options.

# Commands

Use `python -m choops_py.cli --help` or `<command> --help` for complete flags. All generated destinations must be within this checkout's output/.

| Workflow | Commands |
| --- | --- |
| GUI | gui |
| Archive | build-cache, cache-info, resolve-name, rip |
| Converter setup | texture-tools-status, setup-texture-tools --copy-from-old-sources, configure-texture-tools --gtf2dds PATH --dds2gtf PATH, test-texture-tools |
| DDS export | export-dds, export-iff-textures, export-cdf-textures, export-teamselectlogo-dds, export-uniform-atlas-dds, export-scne-textures, export-court-textures |
| DDS import | import-dds, replace-iff-texture, replace-cdf-texture, import-teamselectlogo-dds, import-uniform-atlas-dds, import-scne-texture, replace-court-texture |
| Mod staging | import MOD FILE --iff ARCHIVE [--sub TEXTURE], list-overrides MOD, validate-mod MOD |
| JB build | build-copy VANILLA_JB MOD OUTPUT --overwrite [--dry-run], validate-build VANILLA_USRDIR MODDED_USRDIR REPORTS |
| Roster | roster-detect, roster-decode, roster-export-json, roster-validate, roster-save INPUT JSON OUTPUT --safe-only |
| Container checks | inspect-txtr, inspect-iff, validate-iff, round-trip-iff, inspect-cdf-pair, validate-cdf-pair, inspect-tool-wrapper |

Texture exports accept --raw, --dds and --gtf2dds PATH as applicable; raw payload preservation is always performed. Imports require --same-format-only or --same-size-only as shown by help and accept --dds2gtf PATH. Standard IFF/SCNE imports output a new file; CDF imports output a paired folder. Team logo batch import uses the original export manifest and a directory of edited DDS files.

```powershell
python -m choops_py.cli rip "<GAME_ROOT>/PS3_GAME/USRDIR" output/rips/base --file ua000.iff --raw-iff
python -m choops_py.cli import output/builds/mod output/temp/ua000.iff --iff ua000.iff
python -m choops_py.cli build-copy "<GAME_ROOT>" output/builds/mod output/builds/my_build --overwrite
python -m choops_py.cli validate-build "<GAME_ROOT>/PS3_GAME/USRDIR" output/builds/my_build/PS3_GAME/USRDIR output/reports/my_build
```

Difference packages: `export-mod-patch SOURCE MOD OUTPUT.chpatch` and `import-mod-patch SOURCE INPUT.chpatch NEW_MOD`. Builder Ctrl+C cleans the owned staging copy and returns exit 130.
