# Remaining acceptance work

Updated 2026-10-11. See ../CURRENT_STATUS.md and ../KNOWN_LIMITATIONS.md.

- No game compatibility guarantee: emulator/gameplay checks are prohibited for
  agents; no full testing JB build. User reports can guide read-only/Python fixes.
- Uncertain pointer layouts, masks, loops and CDF growth remain blocked/read-only.
- Audio title routing remains unresolved. The Qt workspace is experimental;
  LGPL codec packaging passed exact-head Windows CI and the packaged audio
  round-trip on PR #6's current head, but remains unreleased until review.
  Unknown AUDO loops and general CDF audio growth stay blocked.
- Six palette words, exact shoe commercial names, alternate/profile behavior and
  independent IDs for decloned teams remain research tasks.
- The texture dimension ceiling does not prove a safe runtime memory allocation.
- Legacy converter permission is unresolved, but those tools are not needed or
  distributed. Normal texture conversion is built in.
- Profile/history, persistent caches, external output roots, advanced research
  tooling and remaining preview polish are not complete. Preserve known contracts.
