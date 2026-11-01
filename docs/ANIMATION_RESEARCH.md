Current NBA extension: see [NBA roster/container support](NBA_ROSTERS_AND_2K14.md) and
[animation portability research](ANIMATION_PORTABILITY.md). Those pages define the
newer per-game boundaries; historical College Hoops-only statements below remain
specific to that earlier scope. NBA 2K14 SDAT rebuilding and complete NBA ratings
semantics are not implemented.

# Motion-capture extraction research

Stock embedded NAME metadata identifies record hash 0x60900D71 as `SingleMoCap`.
Located banks include crowd, gumbel, kellogg, playercreate, gameintro_cameras,
gamedata and global. These are mixed banks: discovering clips does not mean every
record in the bank is an animation. Explorer adds an Animation banks category for
the confirmed focused banks; unknown filenames may retain researched internal
labels. The standard IFF type fallback now recognizes SingleMoCap even without
an appended NAME table.

Use these commands on an extracted standard IFF:

```powershell
python -m choops_py.cli inspect-animations bank.iff output/temp/motion_inspection
python -m choops_py.cli export-animations bank.iff output/rips/motion_records
```

Inspection reports clip identities and decoded block sizes. Export extracts only
SingleMoCap records, decompresses their containing blocks, and retains each
record's exact byte span. The manifest explicitly says skeletal tracks have not
been decoded. A record with conflicting hash and embedded type name is rejected.
Original inputs remain immutable; no animation writer or FBX/BVH conversion is
claimed.

Initial motion blocks contain a compact header followed by packed streams; two
examined gumbel clips had different lengths but a common header structure. Bone
identity, frame timing, quantization, channel tables and keyframe decoding remain
under investigation. Do not infer a frame rate from a plausible float alone.
Stadium CDAN records describe crowd placement candidates and are not relabeled
as skeletal clips. Further extraction is currently lossless raw-block extraction.

Further read-only inspection located 319 SingleMoCap records in the sampled
standard-bank inventory. Candidate count/duration header relationships differ
between presentation and crowd clips; mirrored entries can be only 64 bytes.
Therefore a guessed universal frame rate or stand-alone BVH decoder is not
exposed. Clip dependency/alias resolution must precede skeletal export.
# v1.21 event/payload bridge follow-up

[Native event evidence and commands](ANIMATION_EVENT_BRIDGE.md) now cover the
eight/twelve-byte row difference, first/last marker lookup, exact timestamp bits,
event90's category-word consumer and NBA11's counted membership pairs. The guarded
offline writer requires explicit reviewed mappings and blocks opaque payloads.
It adds no default semantic dictionary, runtime bank or new jump-shot registration.
