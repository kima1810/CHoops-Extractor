# CHoops Modding Studio — v1.23

Windows/macOS desktop editor and Python CLI for the verified PS3 College Hoops 2K8,
NBA 2K9 and NBA 2K14 asset layouts. Browse/extract archives, edit supported textures
and roster fields, preview authored models, and prepare compatible overrides.
College Hoops has the broadest roster support. NBA 2K14 archive writing remains
blocked because its authenticated SDAT container requires a separate validated writer.

[Download desktop releases](https://github.com/ZMO34/CHoops-Extractor-Reborn/releases)
· [Documentation index](docs/README.md) · [Support matrix](docs/FEATURE_MATRIX.md)
· [Current status](docs/CURRENT_STATUS.md) · [Known limits](docs/KNOWN_LIMITATIONS.md)

## macOS quick start

Download the **macos-arm64** ZIP for Apple Silicon or **macos-x86_64** for Intel.
Requires macOS 13+. Extract the complete ZIP and move `CHoops-Studio.app` to
Applications. The app is ad-hoc signed, not Apple-notarized; see
[Mac installation and limitations](docs/MACOS.md). No Python installation is needed.

## Windows quick start

1. Download the release ZIP and extract **all** files. Keep `_internal` beside
   `CHoops-Studio.exe`; no Python installation is required.
2. Open your original JB/PS3_GAME/USRDIR from Explorer. The application detects the
   supported archive layout. Originals remain read-only.
3. Choose **Select overrides folder** in Explorer for recursive replacement discovery.
   DDS wins over a corresponding TXTR; TXTR is used when no DDS exists.
4. Use the global **Preview source** dropdown to choose Source JB or Selected
   overrides. This choice applies to model geometry and textures. Missing override
   records can use a labelled JB fallback; selecting overrides does not build a JB.
5. Edit confirmed roster fields in the selected row's side panel. Export a copy.
   For supported writable archive layouts, select a new empty output folder in
   Mod Builder and build manually. Read the completion report before testing.

See [workflows](docs/WORKFLOWS.md) for rosters, previews, music and builds, and
[troubleshooting](docs/TROUBLESHOOTING.md) for corrective actions.

## Included features and boundaries

- Lazy IFF/CDF exploration, researched hash labels, category filters and roster
  references; built-in DDS conversion with no proprietary converter dependency.
- College Hoops roster side panels, ratings copy/paste, CSV review/import,
  comparison, guarded school assignment, palettes, footwear and readable choices.
- Separately detected NBA roster schemas with confirmed fields and guarded writes;
  full NBA ratings, contracts/history and arbitrary text growth remain unresolved.
- Static jerseys/shorts, shoes, arenas/floors, authored numbers 0–99 and the
  supported surname preview. Court alignment guides have independent border,
  3-point, and key/center-circle toggles. Full runtime rendering is not reproduced.
- Licensed Music and Fight Songs subsections, WAV export and queued soundtrack
  replacement. Titles/artists remain read-only; EBOOT is never edited.
- Cached DDS conversions/prepared overrides, bounded parallel conversion, persistent
  repair advice, transactional output and sequential source-preservation checks.

Gameplay compatibility is unverified. No emulator or automatic testing-game builds
are used in project verification. No game assets are distributed. LGPL audio
helpers include matching sources/notices in each desktop ZIP.

## Develop and contribute

```powershell
python tools/dev/setup.py
.\.venv\Scripts\python.exe -m choops_py.studio
.\.venv\Scripts\python.exe tools/dev/verify.py
```

Use Python 3.12 x64 for the Windows baseline. See [development](docs/DEVELOPER_GUIDE.md),
[test policy](docs/TESTING.md), and [release procedure](docs/RELEASING.md).
Every update maintains documentation and a PR handoff in the
[canonical repository](https://github.com/ZMO34/CHoops-Extractor-Reborn).
Both development instances follow [AGENTS.md](AGENTS.md) and
[collaboration rules](docs/COLLABORATION.md).
