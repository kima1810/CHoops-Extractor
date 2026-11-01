# Donor translation research APIs

`choops_py.research.donor_header.translate_donor_motion` accepts decoded donor/target
ELF bytes, a donor header address and separate explicit metadata/event contracts.
It returns a relative CH component and provenance manifest; it writes no files.
Metadata contracts require full source/target and header fingerprints plus explicit
mode/state/planar assertions and evidence. No automatic/default metadata contract,
signature-IFF source adapter, executable installation or GUI action is supplied.
`ResidentLoaderModel` is an offline callback/lease protocol with a Python-local
registry. See [evidence, contract fields and native integration limits](ANIMATION_RUNTIME_ADAPTER.md#contract-gated-donor-header-construction).

The optional Ghidra `tools/research/AllocatorABITrace.java` script takes a **new**
output JSON path. It requires the observed decoded CH analysis project, checks
allocator descriptor revision, and exercises bounded wrapper instructions against
synthetic heap callbacks. It does not run the game, modify EBOOT or invoke the
real heap implementation.

# Deep native shot dependencies

`inspect-shot-registration CH_ANALYSIS.ELF OUTPUT.json --motion-extents` adds
full registered target header, pose/root and event-sentinel extent checks and
reports load-segment ownership. Unknown auxiliary extents stay explicit. This
is read-only; neither this option nor the resident-image research backend installs
an EBOOT patch or translates unresolved NBA authoring metadata. See
[native residency evidence](ANIMATION_RUNTIME_ADAPTER.md#target-header-ownership-and-native-relocation-follow-up).

# Offline motion sampling and donor registry

`sample-native-motion DONOR_ELF TARGET_ELF HEADER_ADDRESS SECONDS OUTPUT.json
[--cache-bytes BYTES]` samples the observed NBA11 packed motion family with a
verified canonical CH bind. It emits a separate one-frame research JSON, uses
bounded retained payload, rejects unsupported layouts/stale inputs, and protects
both input files. No installable motion bank or native hook is written.

`inspect-donor-registry INPUT.iff nba-2k11 OUTPUT.json
[--related-bank OTHER.iff]` indexes the observed 31-category signature collection.
Repeat related banks to resolve exact type/ID dependencies; duplicates stay
ambiguous. Group member selectors are described, not translated or installed.
See [runtime adapter evidence and remaining work](ANIMATION_RUNTIME_ADAPTER.md).

# Motion event bridge

`inspect-motion-events INPUT PROFILE ADDRESS OUTPUT.json [--native-elf]`
reads CH2K8/NBA11 event rows and known payload-word metadata. Add
`--auxiliary-start ADDRESS` for NBA11's counted membership pairs.
`transcode-motion-events INPUT nba-2k11 ADDRESS CONTRACT.json OUTPUT.bin`
writes a separate CH-format event table only with explicit per-ID/payload rules
and evidence. Both commands use block offsets by default or absolute decoded-ELF
addresses with `--native-elf`. Unknown payload schemas/missing rules block output;
no built-in semantic map or installable game bank is supplied. See
[event evidence, contract syntax and limitations](ANIMATION_EVENT_BRIDGE.md).

# Scorebug native table inspection

`inspect-scorebug-runtime DECODED_ELF OUTPUT_JSON` validates the observed CH2K8
popup descriptors and executable code/TOC mappings. It is read-only, revision
bounded, and does not observe live queue state or patch executables.

# Adaptive NBA11 motion resampling

`resample-motion-frames POSE_INPUT TIMING_INPUT ROTATIONS TRANSLATIONS OUTPUT`
expands the observed NBA11 byte-delta keyframe timeline into fixed CH pose samples.
Optional `--root-track INPUT --root-output OUTPUT` translates the matching root
track; add `--root-without-heading` for its confirmed six-byte mode. Original keys
are exact; inserted samples use mathematical SLERP/linear interpolation and native
quantization. This does not reproduce native FP bit-for-bit or write containers,
bone maps, auxiliary tracks/events, executable tables or installable animations.
Keep rate/time-scale in the future header adapter. `gameplay_ready` remains false.

# Packed motion channel translation

`transcode-motion-frames INPUT SOURCE_PROFILE TARGET_PROFILE ROTATIONS TRANSLATIONS FRAMES OUTPUT`
accepts `nba-2k11` and `college-hoops-2k8` for the observed packed XYZ channel layout.
It converts the quaternion permutation selector while preserving all other bits.
Use confirmed counts and an isolated stream, not an entire IFF/ELF. It does not
retarget skeletons, handle auxiliary tracks/events, register jump shots or make
an installable bank. Output reports `gameplay_ready=false`. Sources are protected.

# Native animation investigation

`inspect-embedded-motion ANALYSIS.ELF PROFILE OUTPUT.json` accepts
`college-hoops-2k8` or `nba-2k11` on an already decoded private ELF analysis copy.
It bounds-checks the observed full-body header family and absolute dependency
starts, distinguishing file-backed and zero-filled memory. It writes metadata,
not clips; no SELF decryption, executable writes, complete coverage or port is
implied. Keep real-game reports private.

`inspect-animation-links INPUT.iff PROFILE OUTPUT.json` accepts
`college-hoops-2k8` or `nba-2k11`. It reports local alias candidates, unresolved
external IDs, ambiguities and cycles, with native envelope bounds checks. It does
not decode poses or write animation/gameplay files. See
[the implementation ledger](ANIMATION_GAMEPLAY_PORT.md) for inventory commands,
new archive labels, Ghidra evidence and current limits.

# Native rebuild additions

v1.10 no longer registers add-uniform-alternate, fill-five-uniforms or
add-archive-assets. v1.20 restores asset creation through the guarded Team Assets GUI; those legacy CLI entry points remain removed.

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

# Read-only player-face research

With the development Python environment, run
`python -m choops_py.research.player_faces "PATH_TO_ORIGINAL_CH2K8_JB"`.
Add `--players` for the source roster's per-player likeness selectors.
Prints JSON only; no face import, roster writing or executable patching.
See [player-face evidence](PLAYER_FACE_RESEARCH.md) for supported meanings.


## Canonical motion bind / shot registration audits

`inspect-motion-bind NBA11_ANALYSIS.ELF CH_ANALYSIS.ELF output/research/bind.json`
checks the observed 21-bone parent/rest/default-route correspondence.
`inspect-shot-registration CH_ANALYSIS.ELF output/research/registration.json`
checks native stock preservation, table ranges, known consumers and label writes.
Both are read-only; no executable patch application is exposed. Reports are private
research outputs and do not certify a playable animation port.

`inspect-motion-events ... --payload-consumers` optionally annotates individually
traced NBA11 payload reads. It requires the NBA11 inspection command; opaque
payloads remain blocked from conversion. See ANIMATION_BIND_REGISTRATION.md.
## Read-only recruiting research

```
choops inspect-recruit-pool roster-or-save output/recruit-pool.json
choops inspect-recruit-pool roster-or-save output/recruit-pool.json --interest-nodes identified-nodes.bin --free-head 0
choops inspect-recruit-pool roster-or-save output/recruit-pool.json --recruiting-state identified-component.bin
```

The input uses existing roster adapters, including the recognized Legacy wrapper.
Reports stay under output/ and cannot replace any input/dependency. The optional
interest block must be a separately identified 128,000-byte native node array;
`--free-head` is optional and applies only to that block. The alternative recruiting
component must be exactly 0x415A4 bytes, with its own serialized free heads. The
options are mutually exclusive. No offset within a complete Legacy save is guessed.

This audits class/preferences, native flags and links. It does not add transfers,
edit records, treat blank slots as safe to overwrite, repair unknown data or export
research fields through game-data CSVs. The second node pool and remaining queue
semantics are reported as incomplete. See LEGACY_TRANSFER_PORTAL.md.
