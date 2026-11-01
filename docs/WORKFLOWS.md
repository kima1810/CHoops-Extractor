# Practical workflows

## Edit uniform fit

Use Models / Courts > **Uniform meshes…** to export all supported garments or
prepare the experimental modern-fit collection. OBJ cages and originals remain
separate from ready IFF overrides. Reimport validates topology, UVs, source hash
and cloth seam correspondence. The [mesh workflow](UNIFORM_MESH_EDITING.md)
documents CLI commands and unresolved runtime cloth/collision behavior.

## Select a game and overrides

Open the source JB, PS3_GAME or USRDIR in Explorer. Detection is based on verified
container structure, not a user-selected game mode. Keep every required split
bank available together. For SDAT input, extraction is authenticated and bounded;
a successful read does not imply the editor can sign/rebuild that container.

Choose **Select overrides folder** in Explorer. Discovery is recursive and handles
supported current and legacy rip structures, including V5.5 exports whose top-level
numeric folders are source archive TOC indices. Keep those folder names intact.
Geometry SCNE replacements override
vanilla SCNE records; corresponding DDS artwork wins over TXTR artwork. A TXTR
is used when its DDS does not exist. This preparation resolves identities,
validates layouts and caches conversions; it does not create the game output.
Do not rename unrelated files merely to bypass an ambiguous selector error.
Opaque `.bin` replacements are preserved as binary payloads and are not parsed as IFF.

Selecting unchanged sources reuses cached work. Source metadata changes invalidate
matching entries, and content/conversion keys protect supported prepared operations.
Timestamps are not a general proof against deliberately timestamp-preserved changes;
reselect edited input and investigate unexpected fallback before building.

## Preview the intended artwork

The top **Preview source** dropdown applies across model categories. Choose Source
JB to inspect the original, or Selected overrides to resolve replacement geometry
and textures. The asset lists in Jerseys, Shoes and Stadiums/Floors avoid manual
IFF-name entry. A fallback label means a matching replacement was not resolved;
it does not mean the override artwork has been loaded.

Select an asset and press its preview button. Use the neck/build/shorts/render
controls for supported combined uniforms, and Floor only for court inspection.
Roster palettes require a unique confirmed association or an explicitly selected
matching roster. Unassociated meshes use embedded material artwork.

Drag the pane splitter to resize controls versus the preview. Left-drag orbits,
right-drag looks around, middle-drag or Shift-drag pans; WASD moves, Q/E moves
vertically, Shift/Ctrl changes speed, wheel zooms and F fits the camera.
For full-court texture alignment, independently enable border, 3-point and
key/center-circle guides. They are fixed stock court references raised one game
unit, not boundaries inferred from the apron edges and not exported artwork.

## Edit and compare rosters

Load from JB, load from selected overrides, or open an external supported IFF,
raw ROST/decrypted USERDATA or supported save wrapper. Encrypted saves need an
external authorized decryption step. Format detection chooses the schema; do not
apply College Hoops offsets to an NBA roster.

Select a row for its side editor. Double-click writable values. Confirmed choices
use readable labels; unknown values are preserved rather than guessed. College
Hoops ratings support copying to selected players, CSV export/import review and
selective comparison. Retain CSV identity/safety columns and import only compatible
edits. UI/research references are excluded from game-data CSVs.

School transfers use guarded slot/count updates. A school shoe-brand change
propagates only to that school's players. Export a copy in the requested supported
IFF/save format, reopen it and inspect the result. Names exceeding established
keyboard capacities get orange warnings where mapped; an unknown limit is not
inferred from the old string's length. NBA text growth/shared storage has separate
restrictions documented in NBA_ROSTERS_AND_2K14.md.

## Replace soundtrack audio

Use Audio's Licensed Music or Fight Songs subsection. Export WAV to inspect the
supported stream. Queue/import multiple songs before saving the rebuilt
cribmusic.bin; review each queue item and save to a separate output. The licensed
Windows helpers handle the supported WAV/ATRAC3 path. Keep their corresponding
source archives and notices with redistributed binaries. Names/artists remain
read-only; cover-art actions operate only on established mappings.

## Build manually and inspect the report

For a supported writable source, prepare overrides, choose a **new empty output
folder** in Mod Builder and start the build. Destinations can be on another drive
but must not overlap source/mod data or overwrite an existing build. The tool
validates records, source preconditions, sizes and relocation support, copies to
transactional output, verifies generated/preserved bytes and publishes on success.
Read the GUI summary for replacements, resizing and compatibility problems.

Non-stadium artwork is normalized to the selected base layout where required;
stadium assets can grow only through supported writers. No universally safe maximum
GPU texture size has been certified. The editor rejects unknown layouts instead
of treating a successful DDS decode as proof of game compatibility.
No agent creates a real testing JB or launches RPCS3. The user chooses when and
how to test the manually built output.
