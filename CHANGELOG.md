# Change log

## Unreleased — reviewed audio GUI continuation

Fix scene/shoe navigation after Audio insertion; clean-clone converter tests use
synthetic fixtures. Batch WAV exports publish atomically and remove incomplete
batches on cancellation/failure.

## Unreleased — LGPL audio package

Build a restricted FFmpeg CLI from pinned upstream source with GPL/nonfree
components disabled, ship corresponding FFmpeg/AtracDEnc sources and notices,
and include both audio helpers in the standalone Windows GUI. Windows CI run 54
built the package and passed the frozen synthetic WAV round trip on the current
PR head. ATRAC PCM input now accepts finite samples through ±4.0, matching the
encoder's 1/4 input scaling and avoiding rejection of over-range floating WAVs.
Song replacements are trimmed or silence-padded to the selected track's original
sample length.

## v1.08 audio development bundle

Experimental WAV/audio-bank/AUDO/jukebox-art CLI, unchanged-WAV checksum skipping,
sample-extent checks, portable setup and shared Codex PR/documentation workflow.
Experimental Audio workspace adds separate Licensed Music/Fight Songs tabs, WAV
export/replacement preparation and mapped cover-art actions. Song-name editing
remains unavailable. No emulator or testing JB.

## v1.07

Community roster ZIP/rating fixes, packed player/team shoe editing, game roster
IFF export and declared 2D stored-depth compatibility. Source inputs preserved.

## v1.06

Reusable single-surface court preparation and automatic non-stadium base texture
normalization. Dynamic supported stadium sizes retained; runtime budget unknown.

## 1.0b0 development (Git tag v1.0beta reserved, not created)

Native Qt studio; streaming cancelable raw extraction; precomputed IFF spans; replacement-folder staging and source preconditions; verified unpatched build bytes; roster redo; source/packaged smoke tooling. CI branch deletion/release side effects removed. Historical higher-looking version tags remain untouched. This is a new rebuild train, not a replacement of preserved releases.
