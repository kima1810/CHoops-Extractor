# Current native port investigation

See [animation/gameplay implementation ledger](ANIMATION_GAMEPLAY_PORT.md) for
Ghidra findings, implemented inventory/link tools and explicit remaining work.
The old NBA 2K14 count of 7,460 was incomplete: a 10,000-record inventory ceiling
excluded nba_animations.iff. The corrected count is 22,139 SingleMoCap records.
The observed CH/NBA11 packed pose/timing/root converter is now available as an
offline research command. No complete bank swap or modern control implementation
is enabled; see the ledger for its exact bounds.

# NBA animations to College Hoops: research only

No animation port, bank replacement or gameplay patch is implemented.

Read-only inventory of supplied PS3 archives finds:

| Game | SingleMoCap records (0x60900D71) | Old SKEL records (0x7657AB8A) |
|---|---:|---:|
| College Hoops 2K8 | 319 | 1 |
| NBA 2K9 | 904 | 1 |
| NBA 2K11 | 4,705 | 0 |
| NBA 2K14 | 22,139 | 0 |

These are identifiable IFF records, not counts of all gameplay clips. Other raw
banks remain undecoded. Zero old SKEL records does not mean NBA 2K11/2K14 lack skeletons.
NBA 2K14 motion.iff also contains three records of unresolved type 0x9D34E89E,
with sample decoded lengths 166,408 / 15,464 / 8,128 bytes and leading version word
0x21. Their gameplay lookup/graph semantics are unestablished. players.bin and
teams.bin are named by CRC candidates but their large opaque payloads have not
been decoded as animation containers.

College Hoops and NBA 2K9 share the observed older SingleMoCap envelope: examples
include 64-byte reference-like records and longer packed records with track data
following the header. Both global SKEL samples begin with 21 and contain matching
matrix-like data, but names/identity metadata differ. Crowd track masks also differ
(for example 0x003DF7DD versus 0x003B77DD). Shared type hashes or matrix bytes do not
prove the same bone ordering, bind pose, event format or clip lookup contract.
NBA 2K9 is the stronger candidate for a future controlled retargeting study.

The [2K11 donor follow-up](NBA2K11_DONOR_ASSESSMENT.md) authenticated the observed
v3 SDAT banks and decoded selected SingleMoCap samples: 56/64-byte reference-like
records and longer packed records. It is a rich next donor to compare after the
closer 2K9 baseline, not proof of a compatible full library. Track masks, skeleton
dependencies, events and lookup/selection consumers remain unestablished.

NBA 2K14 uses changed sample envelopes: 32-byte reference-like records and longer
records with different header organization/packed data. Sharing SingleMoCap's type
hash does not make those records directly compatible with the College Hoops reader.
The evidence argues against copying NBA 2K14 banks directly into College Hoops.

A future converter would need to establish bone identities/order and hierarchy,
translation/rotation packing, time units/key interpolation, root motion, mirrored
tracks, skeleton scale/bind transforms, animation/event IDs, gameplay lookup tables
and contacts/ball/hand interactions. It would decode into an intermediate skeleton
and clip representation, retarget deliberately, then encode the destination format
while preserving unrelated records. None of those steps is assumed proven here.
No direct swap is certified for either NBA title; no emulator or game was run.

Repeatable read-only report:

```powershell
python -m choops_py.research.animation_compat CH_JB NBA09_JB NBA14_JB --output output/research/animation-comparison.json
```

The command scans bounded IFF headers, counts established type hashes and decodes
up to five representative records per type. It checks that source bank metadata
remains unchanged. The report is local research output, never bundled game data.
See NBA_ROSTERS_AND_2K14.md for container and primary format references.
