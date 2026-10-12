# Technical handoff reference index

This public handoff contains portable development guidance. Personal context, session records, environment details and fixture-derived inventories are excluded.

## Current references

- [Secondary Codex master prompt](SECONDARY_CODEX_PROMPT.md): full portable startup instructions.
- [Current status](CURRENT_STATUS.md): living capabilities, tasks and provenance.
- [Collaboration](COLLABORATION.md): two-account PRs, bug review and documentation duties.
- [Audio research](AUDIO_RESEARCH.md) and [audio CLI](AUDIO_WORKFLOW.md): experimental audio evidence/commands.

- [Project source of truth](PROJECT_SOURCE_OF_TRUTH.md): established format contracts and confidence notes.
- [Format notes](FORMAT_NOTES.md) and [specification index](FORMAT_SPECIFICATIONS.md): parser/writer reference points.
- [Architecture](rebuild/ARCHITECTURE.md): application services and GUI boundaries.
- [Feature matrix](rebuild/FEATURE_MATRIX.md): implemented, experimental, read-only and unavailable operations.
- [Safety model](SAFETY_MODEL.md): immutable inputs, output separation and transactional validation.
- [Roster editor](ROSTER_EDITOR.md) and [texture conversion](TEXTURE_CONVERSION.md): supported editing workflows.
- [Developer guide](DEVELOPER_GUIDE.md): reproducible commands and test groups.
- [Acceptance gates](rebuild/ACCEPTANCE_TESTS.md) and [risks](rebuild/RISKS.md): remaining validation and release conditions.

Historical design proposals do not establish format compatibility or current-version verification. Validate changes with generated test data and authorized read-only inputs. Preserve unknown bytes, block unsupported writes, and keep game assets and environment-specific reports out of public source.
