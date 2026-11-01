Mac users: see [installation, data folders and platform limits](MACOS.md).

# Team assets (v1.20)

Use **Team Assets** for the searchable assignment list and checked S/Home/Away/
X/Y/Z/Menu-logo creation. Review changes, apply a separate overrides folder, then
use the normal JB builder. **Save roster to overrides** preserves your full edited
community roster; selected-team copy buttons move activation/asset assignments
between roster sources. Classic shared stadiums can be forked independently.
Missing linked alternate assets use Home with explicit log notices. See
[Team asset guide](TEAM_ASSETS.md) for the full workflow and native limits.

# Native studio user guide

Start with [current workflows](WORKFLOWS.md), the [support matrix](FEATURE_MATRIX.md)
and [troubleshooting](TROUBLESHOOTING.md). The versioned sections below preserve
detailed behavior introduced over time; removed actions are not available. NBA
scope is defined in [NBA support](NBA_ROSTERS_AND_2K14.md).

Active development: Export > Roster CSV exports editable cells. Import / compare
opens a review with field checkboxes before applying changes. Ratings edit inline;
Copy ratings/Paste to selected players supports school-filtered batch work.
Class and Redshirt choices join the Player panel; Conference History holds the
supported record scalars. Save a copy after editing. Name growth preserves old
storage and uses verified game input limits where mapped.

The continuation maps school/short names (16 UTF-16 units), abbreviation (4),
plural mascot (16), event name (64), student section (32), and stadium name (15)
to the game's entry capacities. Existing longer text is preserved until edited.
Jump shot animation uses confirmed IDs 0–111; descriptive animation names remain
under research. In Explorer, teamselectlogo's nested logoNNN records show their
school references. Source switching resolves unique SCNE names after reordering.

The Preview source toolbar switches SCNE and textures between Source JB and
Selected overrides. Select the overrides folder in Explorer first; no JB build is needed.
The same choice applies to shoes and uniforms. Named/hashed counterparts reload;
unrelated standalone files retain their own source. Archive categories and roster
reference columns support sorting/filtering. See ROSTER_SCALE_AND_PREVIEWS.md.

v1.11: select a row in any roster category for the right-side editor. Schools have
References, Players, Palette, Shoes and Jersey tabs. Players add Shoes, Jersey and
School assignment tabs. Footwear edits/previews and jersey previews are now in
these panes. School brand changes apply to its players only; use Undo to revert
the whole group. Palette swatches open the RGB picker. Player transfer updates
roster slots/counts and blocks ambiguous/full/inconsistent cases. All 18 slots are
shown. Models/Courts provides combined top/shorts and neck/cut preview dropdowns.
Edit selected/Team palette/shoe toolbar actions are removed. More details:
[side-panel guide](ROSTER_SIDE_PANELS.md).

In v1.10, select a player to see Player, Ratings and Scholarship tabs beside the
table. Double-click a value to edit it; height is entered as e.g. 6 ft 3 in. Position
uses PG/SG/SF/PF/C. Scholarship offers Scholarship/Walk-on. Undo and Save copy work
across these edits. Schools combines the former Teams/Edit Schools categories;
Realign conference retains reciprocal membership. Shoes and export actions are
grouped menus. Team Assets now supplies alternate/independent-asset creation;
D1 conversion remains unavailable. Older dialog/button descriptions below are
historical; use the current side panels and Team Assets guide.

Current release/limits: [CURRENT_STATUS.md](CURRENT_STATUS.md). Experimental
audio uses the shared GUI/CLI backend described in [AUDIO_WORKFLOW.md](AUDIO_WORKFLOW.md).
Titles/artists remain read-only. Users manually stage/build their JB; agents do
not create testing JB folders or launch RPCS3.

Install Python 3.11+ and project desktop dependencies, or run the local onedir prototype. No Node/browser server is used.

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m choops_py.studio
# packaged executable
.\CHoops-Studio.exe
.\CHoops-Studio.exe --cli --help
```

1. Explorer: Open game selects a JB root, PS3_GAME, or USRDIR containing 0A. Source remains read-only. Search by name/hash/index, multi-select rows, extract raw selected/all into a new output/rips folder. Cancel extraction retains only completed entries and a cancellation manifest.
2. Double-click an archive row to inspect its nested records. Texture Editor displays actual texture candidates. Double-click a texture row to decode its image; failures explain unsupported layout/converter/capacity. Export textures writes DDS/GTF/raw and a per-texture manifest. Standard IFF imports accept changed DDS dimensions, compression and mip counts, updating texture descriptors and relocating larger payloads in a new output/temp container. CDF-backed imports still require the existing compatible layout.
3. Roster Editor: Load game roster or open supported original/raw/wrapped/decrypted roster. Search players/teams/arenas/coaches. Select a player/team row and Edit selected. Only confirmed fields are enabled; existing references are selected from records. Undo/Redo and Save copy preserve the original source. Names must have identical encoded length and unshared storage. Encrypted-save decryption and speculative fields are unsupported.
4. Audio: open a JB in Explorer, choose Audio, then **Load / refresh catalog**. Licensed Music and Fight Songs are separate tabs. Select rows to export WAVs or export the whole tab. Choose a new output folder under `output/`. Replace one selected track from a WAV, or edit exported WAVs and prepare a batch replacement from that export folder's manifest. Select one track to export or replace its mapped cover art; fight songs share cover record 021, and some soundtrack tracks also share artwork. WAV export needs the LGPL FFmpeg helper; replacement also needs the ATRAC3 helper. Output is a staging workspace, not a complete JB.
5. Models/Courts: select a SCNE nested record in Explorer to preview its supported geometry and textures. Court texture work uses Texture Editor. Mod Builder can replace complete SCNE records from an override folder; authoring individual vertices and faces is unavailable in this development version.
6. Explorer: Open the source JB folder, then **Select overrides folder…**. The importer searches all subfolders and automatically recognizes Python texture/record export manifests and older record-folder layouts. There are no format-selection switches. Complete IFF/CDF replacements retain their canonical filenames; unresolved Python ripper assets can retain their `hash_XXXXXXXX.iff` identity. Older record folders use archive names such as `s256`, with `arena.scne`, `floor.scne`, and nested texture folders. Supplied SCNEs replace source SCNEs first; matching DDS files then override TXTR artwork, preserving the DDS dimensions, compression and mip count. Larger supported records and archives are relocated automatically in the copied JB. Unknown targets, ambiguous duplicates, unsupported layouts and invalid DDS files produce errors instead of silently falling back to another texture. **Build JB copy** validates patches automatically and creates a separate output/builds folder and verifies the result. The source JB and replacement folder remain unchanged.
7. Research shows a bounded raw hex view; Diagnostics checks built-in texture conversion and generated round trips. No converter installation is required. Logs retain recent operation outcomes. Extraction, override staging and JB copying/verification are cancelable.

All generated paths currently belong under output/ beside the source project or executable. Existing files are refused. A staged mod has original-source hash preconditions; changed originals block a build. No workflow authorizes writing to the supplied game. Save/export paths containing spaces are supported.

DDS conversion is included in the app for L8, ARGB8, DXT1/3/5 and RGBA16F, including complete mip chains and cubemaps. Legacy converter executables are unnecessary; see CONVERTER_PROVENANCE.md. Structural tests do not establish PS3/RPCS3 gameplay. Follow rebuild/ACCEPTANCE_TESTS.md for manual runtime validation.

Older numeric texture folders are resolved against the selected archive's record indices. A uniquely misplaced named scene can be associated with its correct archive; canonical files in the correct archive folder take priority over relocated duplicates. All such resolutions are recorded in the import report. DDS files referring to nonexistent scene texture slots require the corresponding replacement SCNE. These unmatched files remain unchanged in the input folder and are listed under `unapplied_overrides`; valid replacements can still produce one JB build. The tool does not fabricate missing geometry or silently claim unmatched artwork was imported.

Mod Builder also exports/imports .chpatch ZIP packages of XOR differences. They contain source/result SHA-256 preconditions and no original or unchanged game bytes. Import validates every identity, size and checksum before publishing a new staged workspace. Limit: 128 MiB per extent and 512 MiB total. Share only changes you are authorized to distribute. Never distribute copied JB game folders.

Open extracted asset also accepts an individual 0A part and routes it to the archive index. Interactive asset decode is capped at 128 MiB; larger files retain a bounded raw inspection and remain stream-exportable.

### Archive texture previews

In Explorer, double-click an archive entry or use Preview selected to inspect its IFF and automatically preview the first supported texture. Use the texture dropdown below the nested records to browse additional textures. Open IFF opens a standalone extracted container in the same preview panel. Reading and decoding run in the background and use scratch copies under output/temp; originals remain unchanged. Paired CDF data is included when available. Most formats require the configured gtf2dds converter; linear L8 decodes directly. Unsupported layouts, missing converters, and containers without textures show a message. The existing 128 MiB interactive decode limit still applies.

### Stadium 3D preview

Open a stadium sXXX IFF in Explorer, select a SCNE nested record (such as arena or floor), and click Preview 3D scene. Models / Courts displays supported mesh parts. Drag with the left mouse button to orbit, use the wheel to zoom, and click Fit camera to reset framing. Material textures now load automatically for individual draw groups. Include all SCNE sections combines arena and court by default. Cutaway hides roof and light-effect meshes so the interior is visible; turn it off or select an individual part to inspect those meshes. Use the texture dropdown for an explicit override or Untextured for neutral geometry.

The viewer is read-only. This initial preview supports declared big-endian float positions, half-float, float or signed-normalized UVs, instance transforms, a single vertex stream, and 16-bit triangle strips with restart markers. Unsupported parts are listed in the details panel. Automatic material previews use declared shader sampler semantics and parameter offsets to resolve embedded base-color textures. Bump, normal and gloss slots are excluded; missing base color stays neutral instead of falling back to another sampler. Unknown or external texture references remain neutral. Overrides apply to all displayed parts. Simple preview lighting helps distinguish faces; game shader effects, animation, exact material colors, and geometry editing are not implemented. OpenGL 2.0 and the existing texture converters are required for textured rendering (linear L8 and non-power-of-two DXT base-level previews use native decoding). The existing interactive container size limit applies.

Floor preview preserves original geometry. Its coplanar wood, paint, logo and line layers use ordered depth bias to avoid camera-dependent interference; there is no height adjustment. An unresolved runtime-injected court pass is omitted from the color preview rather than covering the court with a neutral texture.

### Expanded roster tools

Player attributes edits the 30 executable-backed named rating channels. Player properties displays recovered appearance/equipment codes; Edit selected additionally supports weight, potential, handedness and shot tendency channels. Edit Schools shows school records and links to their 31-slot palette. The palette dialog identifies the 22 color-control indices found in the game's Edit Schools callback arrays. Conferences lists each conference's membership, founded year, championship-order fields, Final Fours, prior-year bids, rank, tournament settings, presentation ID, and RGB color. Select a conference row and choose **Edit selected…** to edit a supported field; the editor checks the field's stored width and preserves all other record bytes. The USERDATA file remains the input/output roster source; it is not bundled into the executable.

For a standalone stadium archive, choose Associate roster in Models / Courts to load the matching roster. For a modded JB folder, Load game roster reads that folder’s current roster. A unique stadium asset ID match enables verified court color bindings; missing or ambiguous matches retain embedded textures and display an association message. There is no vanilla palette fallback. Arena mask-channel routing is still under investigation.

Camera exploration: click the 3D view to focus it. Left-drag orbits; right-drag looks around from a fixed camera position; middle-drag or Shift+left-drag pans. WASD moves forward/backward/sideways, Q/E moves down/up, Shift accelerates and Ctrl slows movement. The speed control scales keyboard motion. Wheel zoom can move inside the arena; F or Fit camera restores framing.

Roster tables display bounded summaries for palette/ratings/property lists rather than expanding them into enormous columns. Names appear first, and opening a table resets its horizontal scroll position. Both Team palette and Edit selected palette fields provide the RGB picker.

Non-arena SCNE preview also supports single-block scenes with embedded relative buffers and separate vertex streams for positions and UVs. Open an extracted raw or 2kTl-wrapped `.scne`, or select a SCNE record in a cloth IFF. Cloth jerseys and shorts display their stored rest-pose meshes; skinning, cloth simulation and runtime-injected uniform textures are not reproduced. Use a texture override when appropriate. Unsupported declarations remain explicitly reported.

To preview a uniform: open a cloth jersey/shorts SCNE, then choose a searchable uniform from the Models / Courts uniform list, or use Open uniform IFF for a standalone package. The selected source’s authored RGB artwork is applied to the corresponding cloth mesh. The preview does not synthesize player names/numbers or full material shading.


### Shoe previews and file identities

In Models / Courts, choose a shoe artwork package and click **Preview selected shoes**. The current JB folder supplies both the standalone shoe mesh and selected upper/sole textures. In the roster editor, select one player or school and use **Edit shoes…** to change brand, style/artwork ID and home/away colors. The available styles and colors follow the selected brand. All four fields save as one undoable edit; unrelated packed bits stay unchanged. School defaults change independently of existing player assignments. **Preview assigned shoes…** displays the current player assignment or school default for Home/Away. Previewing another package does not edit roster assignments.

Community roster ZIPs can be opened directly, including ZIPs with a nested USERDATA and optional save metadata/icon files. **Save copy…** preserves that ZIP structure and defaults to a `.zip` filename. Raw USERDATA saves remain USERDATA. Existing source names containing control characters are shown as warnings when their pointers and string bytes remain unchanged; they do not block unrelated ratings or shoe edits. Newly introduced string errors, out-of-bounds pointers and invalid references still block edits. Names with existing control characters retain their decoded text and may be corrected with a valid replacement of the same UTF-16 byte length.

To use a community save roster in a manual JB build, open the destination JB, load/edit the community ZIP, then choose **Export game roster IFF…**. This wraps its current roster payload in the loaded game's `roster_english.iff` metadata and validates the round trip. Stage that exported IFF through Mod Builder before your manual rebuild. Exporting the roster does not create a JB build.

Explorer's **Identify unnamed assets** adds internal-record descriptions beside unresolved hashes. **Match filename list…** checks a UTF-8 candidate list against TOC CRC32 values. Confirmed matches become names; descriptive hints retain the original hash identity. Results are cached per JB source and invalidated when its banks change.

### Artwork resolution and menu logos

Stadium DDS artwork can update GPU image dimensions within the 4096-pixel dimension ceiling. Outside stadium archives, recursive staging automatically restores the selected base JB's texture dimensions, format and mip chain while importing replacement artwork. This keeps menu widgets and gameplay texture memory at their base layouts. Replacement SCNEs supply their own geometry. Enlarged GPU records retain 128-byte alignment; obsolete image copies are removed when their relocation semantics are known. Unknown resources remain at their original addresses.

Team selection logos live in `teamselectlogo.iff` and its paired `teamselectlogo.cdf`. Put named DDS replacements under `teamselectlogo/_logoNNN.txtr/logoNNN.dds`, using the actual record name shown in Explorer. Older `teamselectlogo/TXTR/logoNNN/logo.dds` folders also work: the record folder supplies the target name even when the DDS filename is generic. Recursive override selection updates both files together and resizes larger artwork to the base logo layout. Uniform selection files such as `seluhNNN` contain different assets and do not replace this menu logo bank. A folder without menu logo artwork leaves those logos unchanged.

Rebuild existing mods with the corrected importer. Build preflight repairs old incompatible compressed streams while retaining their decoded bytes; repairing compression alone does not correct artwork sizing or alignment from an older import. Python checks validate byte preservation, addresses, descriptors, paired bank metadata and compression. They do not establish gameplay compatibility.

All non-stadium banks import artwork into the selected base JB texture's dimensions, format and mip count. Higher-resolution artwork is resized and its mip chain regenerated for that layout. Import details show the original DDS layout and whether artwork was resampled. Source DDS files remain unchanged. Stadium banks retain dynamic texture and replacement SCNE sizing. Select a vanilla JB to use vanilla resolution references.

Models / Courts now includes **Prepare single-texture court…** for the supplied full-court ZIP. It produces a separate floor SCNE and two DDS overrides, with extra floor surfaces disabled and arena assets untouched. See [single-surface court preparation and memory limits](SINGLE_SURFACE_COURT.md). This creates template files, not a JB build; gameplay compatibility still needs a manual check.

Override selection displays an informational popup when DDS prioritization and preflight finish. A separate popup reports a completed JB build and its output path. Cancelled operations do not show success popups. During processing, the status bar distinguishes DDS conversion, archive compression, source validation and prepared-archive compatibility checks.

Jersey side-panel previews render front/back numbers: choose 0–99/00 or follow the selected player’s roster number. Preview choices do not change the roster. Reborn lettering uses the uniform’s surname font and curved placement. Source JB / selected overrides also applies to glyphs; missing font records produce a warning.

Additional appearance/tattoo/post/free-throw fields and all 112 jump-shot captions are now supported; see ROSTER_SEMANTICS.md. Arena vertex-colour/alpha, lightmap, glow and flare routing is implemented; see ARENA_SHADER_MASKS.md for evidence and remaining runtime effects.

Text edits now grow beyond old allocations and keyboard entry capacities. The UI separates advisory game-keyboard sizes from unproved engine ceilings; structural pointer/UTF-16/adapter guards still apply.

### Selecting overrides again

Select overrides folder… prepares a complete mod workspace and checks it before
building. If the configured workspace already exists, the tool automatically
chooses the next unused numbered sibling (for example my_mod_2). Existing folders
are preserved. The Mod workspace field, previews and Build JB copy all
use the newly prepared workspace. Failed or cancelled preparation leaves the
previous workspace and GUI selection intact. This action does not build a JB.
## Roster and preview continuation

Text edits show an orange border beyond known game keyboard capacity; longer text
remains allowed. School References includes the editable Conference index.
Conference Logo opens its exact texture record for preview/DDS replacement;
save and stage that paired bank manually. Floor 3-point/outer-border toggles use
the game's authored line geometry, including missing layers from the matching
source JB. See CONFERENCE_ASSETS.md, ARENA_SHADER_MASKS.md and
ANIMATION_RESEARCH.md for limitations and raw motion-extraction commands.

Alignment guides start disabled. Use Alignment guide toggles only to position full-court texture artwork. Guides use fixed stock S256 coordinates raised 1 game unit, not apron bounds; toggling them leaves the real floor and palette rendering intact.

Reference guide width uses the central 10% of the authored strip UV: U across both 3-point and boundary strips. This thins guides without moving their centerlines or modifying floor geometry.

### Direct 3D previews

Load a JB folder, then open Models / Courts. Choose a uniform and click Preview
selected jersey; choose shoe artwork and Preview selected shoes; or choose a
stadium and the arena/floor mode, then Preview selected stadium / floor. No IFF
must be opened in Explorer first. Select overrides folder… in Explorer to
prepare artwork, then use the global Source JB / overrides toggle to compare
both geometry and textures. Missing required cloth/shoe meshes are reported;
no substitute geometry is guessed. Uniform top/shorts and shape dropdowns are
available after a direct jersey preview. School labels appear when a roster is
loaded, while archive selectors also work without a roster.

Preview source/list hotfix: the top toolbar dropdown selects Source JB or Selected
overrides for every preview category. Models / Courts has Jerseys, Shoes and
Stadiums / Floors subtabs with pick-only asset lists, preventing typed unmatched
filenames. Override mode labels replaced assets and JB fallbacks explicitly.
Unnamed archive entries no longer break stock court-reference lookup.
v1.14 is published from 2158df982f43ba3dbb1e2df1cfcd2030fb0a25ea;
this follow-up targets the reported missing-name error and source-list UX.

Override-source refresh fix: selecting another overrides folder while Selected
overrides is already active now refreshes asset lists immediately and reloads
the active preview after preparation. Preview loading uses the visible Mod
workspace field, not an older cached path. The toolbar shows the loaded override
count; an unavailable workspace is not mislabelled as JB fallback. Existing
legacy DDS/SCNE folder names remain supported; no bulk rename is required.

Explorer/workspace update: Select overrides folder… now lives in Explorer,
with source-aware asset sizes and Override/JB labels. Dry run is removed from the
GUI; Build JB copy still performs automatic validation. Roster references cover
home/away/alternate selection menus (SELUA/H/X/Y/Z), gameplay uniform banks,
confirmed cloth geometry, player/team shoes, stadiums, paired CDF payloads and
conference/school logo banks. These links use the loaded roster. The wider
reference column, full-text panel and tooltips preserve long references.
Unsupported display metadata is reported without escaping the Qt result callback.

JB and override indexes remain available together. Source-specific scratch files
are reused while file fingerprints are unchanged; RGBA previews share a bounded
64 MiB content cache. Changed manifests invalidate override snapshots; changed
payloads still undergo source/checksum validation. DDS artwork skips the matching
raw TXTR replacement; TXTR remains the fallback only when no DDS is present.
SCNE replacements remain supported. CSVs use explicit binary-backed field
whitelists: asset references, preview labels, research fields and row offsets are
excluded, while source/stale-edit safety columns are retained.

## Explicit roster sources and exports

Roster controls explicitly open external roster IFF or decrypted USERDATA/USRDATA
(and supported save ZIPs), load the source JB roster, or load a real override
roster replacement independently of the preview dropdown. Export offers roster
IFF and decrypted USERDATA. An external IFF supplies its own export template;
other inputs use the loaded JB or a chosen IFF template. Save copy preserves the
original wrapper, including other members of a loaded save ZIP. USERDATA export
does not create encryption, PARAM files, or a complete console save package.
All writers validate and reparse the result and protect the original input.

The observed Legacy-mode `USERDATA` save can also be opened in Roster / Legacy
save editor. The first supported view edits confirmed fields in its embedded
roster. Save copy preserves the complete file and all surrounding Legacy-mode
bytes; size-changing text edits are blocked. Mode-specific season, recruiting,
and progression fields remain read-only until their storage is mapped.

## Resizable 3D preview

Models / Courts reserves more height for the full-width preview. Drag the wide
divider above it up or down to enlarge or shrink it. Controls scroll independently
when space is reduced; the main application window can also be resized normally.
Fit camera frames the model after changing the available viewing area.

# v1.15.2 — current override files in previews

Folder-based previews now use current loose DDS, SCNE and archive inputs instead
of treating an earlier prepared build snapshot as the selected folder. Only the
requested archive is compiled for preview; unchanged inputs reuse a bounded
64 MiB compiled cache. File changes invalidate materialized and decoded previews.
Missing or incompatible live inputs raise an error rather than showing JB art.
The same source applies to Explorer, texture, jersey, shoe and stadium previews.

Select overrides folder once after upgrading to register live input locations.
Older workspaces and imported patches remain usable prepared snapshots and are
labelled accordingly. New or renamed files require selecting the folder again.
After editing inputs, preview again (or switch sources) to reload. Select the
folder again before building to prepare an updated build snapshot; previews do
not change prepared builds or any original input. JB fallback applies only where
no replacement exists. No emulator, testing JB or EBOOT changes.

## Faster overrides loading

Select overrides folder uses CPU/RAM-limited parallel workers automatically.
The progress line shows active workers and completed archives. Repeat selection
reuses unchanged completed archives from the current Mod workspace; edited
inputs recompile only affected archives. Old workspaces without reuse metadata
prepare once before benefiting. No switches or extra converter tools are needed.
Cancellation preserves the previous workspace.

Reuse checks loose input paths, file identities, sizes and modification times;
it validates the original JB archive and cached output with SHA-256 and also
checks importer code. It does not hash all loose input contents on every scan,
so deliberate same-size edits with preserved metadata can evade that quick
input-change check. Ordinary saved/replaced files invalidate affected archives.


## Rebuild speed and validation (v1.16)

Select overrides once and reuse the prepared workspace. Unchanged DDS conversion
results and prepared archives remain cached; edited inputs invalidate their
matching cache entries. Build JB copies files to your chosen destination, then
checks replacement payloads and all preserved bytes. Growing archives use
sequential verification, including unused bank padding and copied non-bank files.
Progress identifies copying, relocating, checking entries and checking preserved
archive bytes. Those checks still read the new output on every build.

Cancel safely through the job dialog. A failure or cancellation removes the
owned incomplete output and leaves an existing completed build intact. DDS
preflight scratch files are cleaned up automatically. Insufficient free space is
reported before copying. Keep the source and overrides unchanged during a build.


## Shared PS3 2K sources (v1.17)

Open a supported PS3 2K JB through the same source-folder action. The editor detects
the archive layout and displays the game title automatically. Explorer extraction,
textures, authored 3D previews, overrides and building use that source's layout;
there is no game-mode selector. College Hoops 2K8 roster editing remains specific
to its confirmed roster format. Unknown layouts/resources produce a clear error
instead of a guessed conversion. See PS3_2K_ARCHIVES.md for verified games and
research-only extraction commands. Included in Windows v1.17.

## Rebuild and override errors

The former “Incomplete archive header” path assumed the pre-body header region
fit inside 0A. The updated planners read that region across banks and append writes
respect each bank boundary. This automatically fixes valid split-header sources;
it does not fabricate missing data in a damaged rip.

For failures, Mod Builder retains Problem / Suggested fix / Details. Details name
the offending archive/selector or source bank; short source banks include expected
and actual byte counts. Restore a named damaged bank from the same original rip
and reselect the source; do not rename DDSes to fix source metadata. For ambiguous
selectors, resolve duplicate equal-priority DDSes; DDS still wins over TXTR. Match
CDF companions from the same rip, re-export invalid DDS encodings correctly, and
reselect original overrides after a source change. Unknown geometry/metadata must
not be deleted to force an import. Unsupported errors retain their exact raw text.
NBA2K14 can prepare supported overrides for preview, but its success message warns
that authenticated JB rebuilding is not supported yet.

## Key and center-circle alignment guide

Models/Courts includes “Alignment guide: key and center circle” alongside the
3-point and out-of-bounds toggles. It is off by default and available when the
stock reference court's matching geometry was loaded. The toggle shows the key
outline/free-throw circles and center-circle outline; it does not fill the key.
These thin guides sit one game unit above the court and stay independent of
school palettes, selected floor texture/layout and the other guide toggles.
The stock reference requirement and College Hoops guide boundary are unchanged.
