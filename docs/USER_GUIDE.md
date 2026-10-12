# Native studio user guide (development build)

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
6. Mod Builder: Open the source JB folder, choose a new mod path, then **Stage replacement folder…**. The importer searches all subfolders and automatically recognizes Python texture/record export manifests and older record-folder layouts. There are no format-selection switches. Complete IFF/CDF replacements retain their canonical filenames; unresolved Python ripper assets can retain their `hash_XXXXXXXX.iff` identity. Older record folders use archive names such as `s256`, with `arena.scne`, `floor.scne`, and nested texture folders. Supplied SCNEs replace source SCNEs first; matching DDS files then override TXTR artwork, preserving the DDS dimensions, compression and mip count. Larger supported records and archives are relocated automatically in the copied JB. Unknown targets, ambiguous duplicates, unsupported layouts and invalid DDS files produce errors instead of silently falling back to another texture. Dry run reviews patches; **Build JB copy** creates a separate output/builds folder and verifies the result. The source JB and replacement folder remain unchanged.
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

Player attributes edits the 30 executable-backed named rating channels. Player properties displays recovered appearance/equipment codes; Edit selected additionally supports weight, potential, handedness and shot tendency channels. Edit Schools shows school records and links to their 31-slot palette. The palette dialog identifies the 22 color-control indices found in the game's Edit Schools callback arrays. Conferences displays names and member-team links; conference assignment is currently read-only.

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

Team selection logos live in `teamselectlogo.iff` and its paired `teamselectlogo.cdf`. Put named DDS replacements under `teamselectlogo/_logoNNN.txtr/logoNNN.dds`, using the actual record name shown in Explorer. Older `teamselectlogo/TXTR/logoNNN/logo.dds` folders also work: the record folder supplies the target name even when the DDS filename is generic. Recursive staging updates both files together and resizes larger artwork to the base logo layout. Uniform selection files such as `seluhNNN` contain different assets and do not replace this menu logo bank. A folder without menu logo artwork leaves those logos unchanged.

Rebuild existing mods with the corrected importer. Build preflight repairs old incompatible compressed streams while retaining their decoded bytes; repairing compression alone does not correct artwork sizing or alignment from an older import. Python checks validate byte preservation, addresses, descriptors, paired bank metadata and compression. They do not establish gameplay compatibility.

All non-stadium banks import artwork into the selected base JB texture's dimensions, format and mip count. Higher-resolution artwork is resized and its mip chain regenerated for that layout. Import details show the original DDS layout and whether artwork was resampled. Source DDS files remain unchanged. Stadium banks retain dynamic texture and replacement SCNE sizing. Select a vanilla JB to use vanilla resolution references.

Models / Courts now includes **Prepare single-texture court…** for the supplied full-court ZIP. It produces a separate floor SCNE and two DDS overrides, with extra floor surfaces disabled and arena assets untouched. See [single-surface court preparation and memory limits](SINGLE_SURFACE_COURT.md). This creates template files, not a JB build; gameplay compatibility still needs a manual check.

Override staging displays an informational popup when DDS prioritization and preflight finish. A separate popup reports a completed JB build and its output path. Cancelled operations and dry runs do not show success popups. During processing, the status bar distinguishes DDS conversion, archive compression, source validation and staged-archive preflight.
