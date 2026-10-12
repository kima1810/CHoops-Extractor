# Current feature matrix

Updated 2026-10-11; supersedes the historical rebuild matrix. Tested here means
software/structural checks, never game compatibility. Details: ../CURRENT_STATUS.md.

| Feature | Current state | Remaining limit |
| --- | --- | --- |
| Native Qt GUI, CLI | Shared backend, virtual tables and workers | Panel decomposition/profiles/history |
| JB archives | Split TOC, hashes, streaming extraction and source checks | More names/cache acceleration |
| IFF/H7A | Bounded parsing, compression and validated record growth | Unknown pointer semantics/aliases |
| CDF | Paired parsing and supported layout-preserving edits | General relocation/audio growth |
| DDS/GTF | Built-in supported formats, mips, complete cubes, remapping | Unknown layouts/DX10/volumes |
| Overrides | Recursive, DDS/SCNE priority, base normalization outside stadiums | Ambiguous identities rejected |
| SCNE preview | Arena/court/cloth/shoes, texture routing and movable camera | Full shaders/skinning/authoring |
| Rosters | Confirmed ratings/fields, RGB, shoes, undo, ZIP save and IFF export | Opaque fields/long strings |
| Uniforms/alternates | Shape/owner/asset linking and explicit builders/check boxes | Complete runtime unlock behavior |
| D1 conversion | Explicit optional roster action | Independent IDs/asset copy validation |
| Palettes | 22 exact captions and three runtime roles | Six words and arena masks |
| Courts | Single-surface preparation and proper bump semantic | Crash-free GPU allocation unknown |
| Audio | Experimental AUSB/AUDO/WAV/cover backend + CLI; Qt Licensed Music/Fight Songs workspace; LGPL codec package with Windows CI smoke | Title routing, unknown loops/CDF growth |
| JB builds | Manual transactional copy, supported growth/insertion | Gameplay unverified; no agent test builds |
| Collaboration | Documented PRs, shared status, portable tests and CI | Independent review requires active session |

Current test results belong in ../TEST_REPORT.md and PR discussions with exact SHAs.
