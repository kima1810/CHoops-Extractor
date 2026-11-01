# Documentation index

Current release: **v1.23**. This index separates usable instructions from format
research and earlier development records. A documented parser result is not proof
of gameplay compatibility. The per-game support matrix takes precedence over
historical claims that all related games behave identically.

## Using the editor

- [macOS installation and platform limits](MACOS.md)

| Need | Start here |
| --- | --- |
| First launch, source selection, normal workflows | [Workflows](WORKFLOWS.md) |
| Supported games, operations and limits | [Feature matrix](FEATURE_MATRIX.md), [current status](CURRENT_STATUS.md) |
| Overrides, build failures, missing preview assets | [Troubleshooting](TROUBLESHOOTING.md) |
| Detailed existing GUI controls | [User guide](USER_GUIDE.md), [GUI](GUI.md) |
| Team asset assignments and expansion | [Team Assets](TEAM_ASSETS.md) |
| College Hoops rosters and side editors | [Roster editor](ROSTER_EDITOR.md), [side panels](ROSTER_SIDE_PANELS.md) |
| NBA roster editing and NBA 2K14 | [NBA evidence and limits](NBA_ROSTERS_AND_2K14.md) |
| CSV, comparisons, text growth and previews | [Roster scale](ROSTER_SCALE_AND_PREVIEWS.md) |
| WAV export and queued soundtrack import | [Audio workflow](AUDIO_WORKFLOW.md) |
| Reusable court texture template | [Single-surface court](SINGLE_SURFACE_COURT.md) |
| CLI commands | [Commands](COMMANDS.md), executable `--cli --help` |

[Modern-feature backport feasibility](MODERN_FEATURE_BACKPORTS.md) separates
existing asset/data routes, animation conversion research, companion workflows
and changes requiring new runtime systems.
[NBA 2K11 donor ratings](NBA2K11_DONOR_ASSESSMENT.md) report actual archive/asset
inspection and distinguish useful conversion sources from unproven direct ports.

[Executable modernization research](EBOOT_MODERNIZATION_RESEARCH.md) ranks small
EBOOT candidates using named code paths, separating confirmed routes from
unverified camera, rules, timing and save semantics. EBOOT remains read-only.
The subsequent [local executable experiment](EBOOT_EXPERIMENT_01.md) is a narrow
owner-authorized exception using separate copies; patching is not in the editor.

## Development and evidence

[Developer guide](DEVELOPER_GUIDE.md) explains the modules and prerequisites.
[Testing](TESTING.md) maps regression suites to risks and explains optional skips.
[Releasing](RELEASING.md) covers exact-head checks, Windows packaging, licenses,
ZIP validation, checksums and GitHub publication. [Test report](TEST_REPORT.md)
records the current results rather than mixing them with old release counts.

Format evidence: [shared PS3 archives](PS3_2K_ARCHIVES.md),
[format specifications](FORMAT_SPECIFICATIONS.md), [roster semantics](ROSTER_SEMANTICS.md),
[arena shader masks](ARENA_SHADER_MASKS.md), [conference assets](CONFERENCE_ASSETS.md),
[texture conversion](TEXTURE_CONVERSION.md), [audio research](AUDIO_RESEARCH.md),
[scorebug research](SCOREBUG_RESEARCH.md), [animation portability](ANIMATION_PORTABILITY.md).
[Player-face research](PLAYER_FACE_RESEARCH.md) maps College Hoops generated faces,
the seven dedicated likeness slots and the limits on borrowing NBA cyberfaces.
Unknown bits, shader modes, text ceilings and animation tracks remain research
until the evidence and preserving writer tests exist.

Coordination: [AGENTS](../AGENTS.md), [collaboration](COLLABORATION.md), and the
[generated secondary-instance prompt](SECONDARY_CODEX_PROMPT.md). Both instances
must update current status, affected guides/evidence and exact test results before
publishing; regenerate the prompt with `python tools/dev/handoff.py`.

## Historical material and maintenance

[Earlier status](history/STATUS_THROUGH_V117.md) and
[earlier verification](history/VERIFICATION_THROUGH_V117.md) preserve research
provenance. Their counts and support claims are dated records, not current promises.
The master handoff, old architecture audit, rebuild baseline/progress and project
notes may contain superseded UI names. Current docs above govern user behavior.

The stale unpublished-beta release draft and obsolete pinned Windows dependency
snapshot were removed in v1.18. A tiny wrapper regression module was consolidated
into binary tests without removing its assertions. Remaining suites cover supported
behavior or explicitly optional research; age alone is not a reason to delete them.
Local cleanup removes only identified generated caches/build intermediates, never
source games, supplied overrides, user builds or private research evidence.

Animation gameplay port scope and native evidence: [implementation ledger](ANIMATION_GAMEPLAY_PORT.md).
