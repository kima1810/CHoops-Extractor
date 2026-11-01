# Format notes

AUSB type 61DF2234 indexes raw .bin streams; known AUDO type 1AEDDA1F uses a
36-byte ATRAC3 header. See [AUDIO_RESEARCH.md](AUDIO_RESEARCH.md) for offsets,
priming, uncertainties and read-only title-routing restrictions.

Authoritative consolidated rules are in PROJECT_SOURCE_OF_TRUTH.md. Full inherited research, including roster field tables and inventory, remains in MASTER_HANDOFF.md. Standard magic FF3BEF94 and CDF metadata F0985030 are distinct formats. Uniforms are standalone standard IFFs; names/numbers are embedded TXTR. CDF pairs preserve metadata, headers and physical payload extents separately. 2kTl is a tool wrapper, not an on-disc archive.

Standard/CDF relative pointers use field + value - 1; ROST runtime string pointers use field + signed delta - 1. Standard/CDF metadata is big-endian; name-table pointers/strings are LE. Archive descriptor names are UTF-16BE and ROST names are UTF-16BE. Do not silently import PC NBA behavior.
