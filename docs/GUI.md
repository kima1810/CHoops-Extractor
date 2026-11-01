# Native GUI

Models / Courts > **Uniform meshes…** exports source-selected OBJ cages, prepares
experimental shorter shorts/fitted jerseys, and reimports an edited collection.
See [mesh editing and runtime limits](UNIFORM_MESH_EDITING.md).

v1.11 provides side tabs for every roster category, including school palettes,
footwear edit/preview and linked jersey preview. Player School changes assignment
safely. Neck/shorts dropdowns in Models/Courts render top and shorts together or
individually. Retired roster edit/palette/shoe toolbar actions are absent.

v1.10 roster layout: Schools combines Teams/Edit Schools. Players show a compact
table and persistent Player/Ratings/Scholarship pane with direct edits. Shoes and
export are grouped menus. D1/alternate/independent-asset public actions are removed.

Launch `python -m choops_py.studio` or CHoops-Studio.exe. PySide6 provides Explorer,
Texture Editor, Roster Editor, Models/Courts, Mod Builder, Research and Diagnostics.
No Tkinter, Node or browser server is required. Long jobs run in bounded workers;
widgets update on the Qt main thread through signals.

Explorer opens read-only JB/PS3_GAME/USRDIR, searches hashes/names and nested IFF
records. Texture Editor previews/exports supported TXTR/SCNE artwork with built-in
conversion. Roster Editor exposes confirmed fields, RGB color picker, ratings,
player/team shoes, save-copy/export and undo/redo. New alternate-asset controls are removed. Audio has
separate Licensed Music and Fight Songs tabs, catalog browsing, selected/section
WAV export, WAV replacement preparation and shared jukebox cover-art actions.
Song titles and artists are read-only. Models/Courts
previews supported arena/cloth/shoe geometry and selected material artwork, with
orbit/look/pan/keyboard movement. Mod Builder stages recursive overrides and builds
only on the user's explicit action. Research/Diagnostics support bounded inspection.

See USER_GUIDE.md and AUDIO_WORKFLOW.md for controls and codec setup. The audio
workspace uses the shared Python services and bundled LGPL audio helpers in the
Windows package; it writes replacement assets under `output/`. Users stage
changes and build JB folders manually. No song-name/EBOOT editing. Agents do not
open RPCS3 or trigger full testing JB builds.
