# Shared development rules

Read `docs/SECONDARY_CODEX_PROMPT.md`, `docs/CURRENT_STATUS.md`, and
`docs/COLLABORATION.md` before changing this repository. Those documents are the
current handoff; dated historical research is supporting evidence.

- Upstream: https://github.com/ZMO34/CHoops-Extractor-Reborn, base branch `master`.
- Work on a feature branch. Publish every reviewable update through a PR to
  upstream master. Continue an existing PR for fixes to the same task; a new
  unrelated update gets a separate PR. Do not push directly to master, merge,
  force-push another person's branch, or publish a release without the owner's
  authorization. The owner can explicitly authorize exceptions.
- Every update maintains documentation: current status, changed format evidence,
  user/CLI instructions where applicable, and exact verification results. Follow
  the PR template. Record unresolved questions instead of inventing semantics.
- NEVER launch RPCS3, automate it, or run emulator/gameplay tests. Do not create
  automatic/testing JB folders. Use synthetic fixtures, Python checks, read-only
  supplied inputs and Qt/packaged startup checks. The user builds JB manually.
- Keep source JB files, supplied overrides, ZIPs, rosters and executable copies
  immutable. EBOOT is read-only research; song-name editing must not require
  EBOOT writes. D1 conversion is optional, never automatic.
- Keep game assets, exported music/artwork, logs, private paths, credentials,
  local settings and generated binaries out of Git. Cleanup is limited to known
  generated files; never remove user builds or staging folders on another PC.
- Writers preserve unknown bytes/bits, validate bounds and identities, reparse
  output, and compare untouched ranges. GUI work uses the shared backend; workers
  must not manipulate widgets. Unknown formats remain read-only.
- Review PR code and dependencies before executing it. Test the exact PR head in
  an isolated checkout. New commits invalidate earlier approval and test evidence.
- Cross-PC communication uses PR discussions, issues and committed status notes.
  Other Codex sessions cannot see this session's memory or local private files.
  Check discussions at session start and before pushing; report blockers there.

Detailed commands and evidence requirements are in `docs/COLLABORATION.md`.
