# Format specification index

Current additions/confidence: [CURRENT_STATUS.md](CURRENT_STATUS.md) and
[AUDIO_RESEARCH.md](AUDIO_RESEARCH.md). AUSB and known ATRAC3 AUDO headers have
experimental support. Standard IFF/SCNE/archive growth exists for validated cases;
older allocation-only descriptions below are conservative historical contracts,
not universal current limits.

Canonical layouts/confidence remain in PROJECT_SOURCE_OF_TRUTH.md, FORMAT_NOTES.md and preserved MASTER_HANDOFF.md. This rebuild does not replace their evidence with guesses.

Archive AA00B3BF: BE alignment/part count/entry count; UTF-16BE part names; offsets in alignment units. Stored sizes on this fixture are invalid and bounded extents derive from next offset/logical end. Derived status remains visible.
IFF FF3BEF94/CDF F0985030: relative target = pointer field + value - 1. ROST: signed target = pointer field + delta. Standard IFF offsets are block logical positions; CDF physical payload positions must use secondary descriptors, never virtual offsets.
Name tables AA171516: BE magic, LE length/pointers, UTF-16LE strings. Unknown words, headers/trailers, block order and shared-slice identities remain preserved. H7A logical-size-preserving encoding reuses valid token choices; capacity must fit original allocation.
SCNE declarations/indices/materials are inspected read-only; no stable geometry writer claim. Verified texture/roster field contracts remain in TEXTURE_CONVERSION.md and ROSTER_EDITOR.md. Tests include malformed slices/pointers, overlap, wrappers, capacity, source hash mismatch and untouched byte identity.

## Two-block menu SCNE geometry addressing (v1.15.3)

Two blocks do not imply all geometry belongs to block 1. Supplied stock
frontend_sync menu scenes use vertex stream flag 0x40000002 with field-relative
plus-one pointers into block 0 (e.g. value 5 points four bytes after the pointer
field). Their index flag is 0x10, also field-relative plus-one into block 0.
Other menu scenes use stream flag 0x40000003 and index flag 0x20000010 with
absolute plus-one offsets into block 1. The flags must not be conflated by a
high-bit mask. Image packing leaves inline header geometry and pointers intact,
relocates only declared data-block buffers, and verifies all geometry bytes.
This evidence concerns image repacking; it does not establish animation or
arbitrary unknown stream semantics. True image/GPU-buffer overlaps still reject.

### Legacy single-face DDS exports

Legacy flat DDS artwork targeting a base cubemap is handled only in recognized
legacy folder imports: it updates the first (+X) face, resampled to the original
format, dimensions and mip chain; the other five faces are retained from source.
The result remains a full cubemap and its descriptor is preserved. The GUI
compatibility summary identifies this operation. Modern manifest-based imports
and direct DDS imports still require matching complete cubemap inputs.
