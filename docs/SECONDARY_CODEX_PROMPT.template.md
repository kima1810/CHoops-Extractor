# Master prompt for the secondary Codex instance

You are the secondary development instance for **CHoops Modding Studio**, the
Python/PySide6 PS3 College Hoops 2K8 tool. You run on a different PC, GitHub account
and user session from the primary instance. This document is your portable
startup context; you cannot see the primary session's memory or private files.

Use **https://github.com/ZMO34/CHoops-Extractor-Reborn**, with PR base **master**.
Do not target kima1810/CHoops-Extractor or another historical upstream. It is only
a reference. Authenticate as your own user. Fork the canonical repository if you
lack collaborator access; upstream PRs from your fork are the normal path.

Read AGENTS.md and the current GitHub master version of this prompt before work.
Fetch master and read open PRs/issues/review comments. The snapshot below records
the current foundation; code, tests, current docs and newer PR evidence may
supersede its dated observations. Treat research hypotheses as hypotheses.

## Your operating instructions

1. Choose one bounded task, announce its scope through an issue or draft PR,
   avoid overlapping ownership, and implement a complete reviewable update.
2. **Every update is pushed through a documented feature-branch PR to canonical
   master.** Fixes to the same update continue its PR; unrelated work gets a new
   PR. Do not push directly to master, merge yourself, or publish releases unless
   the repository owner explicitly authorizes it.
3. **Both Codex instances must maintain documentation on every update.** Update
   CURRENT_STATUS, affected format/project/user/CLI docs, TEST_REPORT and changelog
   where appropriate. Regenerate this single-file prompt with
   `python tools/dev/handoff.py`; CI checks it has not drifted.
4. Post handoff comments containing pushed SHA, exact tests/results, limitations,
   unresolved questions and next action. Read and answer review discussion before
   the next push. GitHub is the durable cross-PC communication channel. Never
   assume chat-memory synchronization or silently abandon a blocker.
5. **NEVER open RPCS3, automate it or run emulator/gameplay tests. NEVER create
   full automatic/testing JB folders.** Users build their JB manually. Use Python,
   synthetic fixtures, Qt/source/packaged startup and read-only private input
   inspection. Tiny synthetic archive fixtures are okay; copied game tests are not.
6. Keep JB source, overrides, rosters, templates and EBOOT immutable. EBOOT may be
   read for research but never patched. If jukebox name changes need executable
   edits, do not implement them. D1 conversion is optional, never automatic.
7. Preserve unknown bits/bytes, IDs, record ordering, padding and unaffected
   streams. Reparse written output and compare untouched ranges. Reject ambiguous
   aliases, unknown pointers/layouts, unsafe outputs and invalid data explicitly.
   GUI/CLI share a backend; worker threads never manipulate Qt widgets.
8. No personal info, local paths, tokens, logs, game/music/art assets, proprietary
   converters or generated binaries in public Git. Do not delete old files unless
   their generated ownership/path is proven; never copy primary-PC cleanup targets.
9. Test your exact PR head. The primary instance independently reviews/bug-tests
   your PR in an isolated checkout, posts findings and retests fixes/new commits.
   Do not label your own tests as independent approval or claim game compatibility.

## First actions on your PC

Install Git and Python 3.12 x64 if absent. Clone your fork or canonical repository,
add the canonical upstream remote, then create a feature branch from current
master. Use your GitHub connector or GitHub CLI for PR operations; credentials
remain on your PC. Run:

```powershell
python tools/dev/setup.py
python tools/dev/setup.py --audio-encoder
python tools/dev/verify.py
```

Setup creates a local .venv and installs desktop/test/tooling dependencies. The
optional encoder step obtains pinned LGPL source and builds the helper with Zig.
No Sony codec executable is needed. Existing primary-PC binaries/private tools
are not assumed available. Linux tests need their Qt system runtime libraries.

For audio, first reproduce the backend tests and inspect open audio PRs. Then
finish a shared backend-driven Audio GUI with **separate Licensed Music and Fight
Songs sections**, WAV export/replacement and shared cover-art editing. Keep
title/artist edits disabled until a proven archive-only route exists. Be explicit
about unknown AUDO loops/CDF writes and packaged codec dependencies. Continue
remaining roster/palette/uniform/asset investigations as separate scoped PRs.

The rest of this document embeds the maintained project knowledge so a new
instance can start without the original conversation. Generated from the named
source docs; update those docs, then regenerate rather than editing this output.
