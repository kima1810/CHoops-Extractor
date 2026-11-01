> Follow-up: the explicit mirrored-selector triplet contract and additional
> opt-in native payload reads are documented in
> [ANIMATION_BIND_REGISTRATION.md](ANIMATION_BIND_REGISTRATION.md).
> They do not constitute a complete event semantic map.

# Animation event bridge phase (v1.21)

The offline event-table bridge is implemented. It reads the established CH2K8 and
NBA 2K11 event layouts, retains exact time bits/order, inspects the known NBA11
payload-word consumer and writes a separate CH-format event table **only with an
explicit mapping contract**. It is not a playable clip, executable patch, built-in
semantic dictionary or completed animation-system port. No donor animation has
yet been registered for CH gameplay; no added jump-shot choice or new controller
default is installed.

## Native findings

Focused Ghidra analysis and independent PowerPC disassembly agree on these routes:

| Native route | Established behavior |
| --- | --- |
| CH 0x217FC | First matching marker ID, eight-byte rows from motion header +0x38, INT_MIN sentinel |
| CH 0x21DFC | First event strictly after a time; input zero is changed to -1 before comparison |
| NBA11 0x1A828 | First matching marker ID, twelve-byte rows from header +0x30, same sentinel |
| NBA11 0x1A7B4 | Last matching marker ID; duplicate IDs cannot be discarded |
| NBA11 0x15F24 | Relocates each row's +8 payload pointer using signed field-relative offset minus one |
| NBA11 call 0x460114 | Event 90 payload first word compared to category 7; selected against actor state |
| NBA11 call 0x47F4FC | Event 90 payload first word compared to actor +0x2E4; matching row time becomes playback start |
| CH call 0x31146C | Related selection path instead requests marker ID 89 + actor category at +0x214 |
| NBA11 0x1A880 | Header +0x34 points to a signed count followed by eight-byte pairs; first word is a membership key |

The latter pair-table value stays opaque. It is not relabeled a pointer, skeleton
or pose channel. A nearest OPD descriptor does not always identify a local function
start: a larger decompile rooted at 0x45FFB0 excludes the later event consumer.
The instruction-level call and payload loads above are the evidence, rather than
an inferred function body based on the nearest OPD.

Event 90 illustrates the semantic gap: the retained-motion candidate comparisons
associate donor payload values 0/3/4/5/7/9 with CH IDs 89/92/93/94/95/97. These are
candidate correspondences, not a validated complete category enum. Source and
destination category spaces differ. No `ID + constant` rule or candidate table is
silently installed. Event 90's consumer establishes a four-byte read, not the
meaning or total allocation size of arbitrary neighboring bytes.

## Read-only supplied-copy audit

The new parser was run against every distinct event-list pointer in the previously
identified full-body embedded-header family:

| Profile | Distinct event tables | Event rows | Malformed tables |
| --- | ---: | ---: | ---: |
| CH2K8 | 3,727 | 17,897 | 0 |
| NBA 2K11 | 9,574 | 49,639 | 0 |

All inspected tables have nondecreasing finite times. NBA11 has 7,564 payload-free
tables. Ten marker IDs have payload pointers: 89,90,92,93,94,173,176,177,178,186.
Of these rows, 151 use event 90's known word consumer and 2,850 carry other opaque
payloads. Event 90 values observed are 0–5 and 7–9; the absent value 6 must not be
invented or automatically compressed out of the category enum.

The auxiliary parser also accepts 101 distinct +0x34 membership tables containing
101 total pairs, with no extent errors. These counts cover this header family,
not every game animation or external bank. Source hashes before/after agree.
No game/executable bytes, generated clip data or private reports are distributed.

## Use the research commands

Run through `python -m choops_py.cli` or the Windows executable's `--cli` option.
Outputs must be separate files in the configured output workspace.

```
inspect-motion-events DECODED_BLOCK nba-2k11 0xOFFSET output/events.json
inspect-motion-events DECODED_ELF nba-2k11 0xADDRESS output/events.json --native-elf
```

For a decoded IFF block, ADDRESS is a block-relative event-table offset and payload
fields remain signed relative pointers. With `--native-elf`, ADDRESS and payload
pointers are absolute virtual addresses. Every requested byte must be file-backed;
an address inside the runtime BSS is not permission to read zero-filled file data.
`college-hoops-2k8` inspection uses its eight-byte layout. NBA14 remains unsupported.
An optional `--auxiliary-start 0xADDRESS` inspects NBA11's +0x34 pair table using
the same address convention. Null pointers are not table addresses.

```
transcode-motion-events DECODED_BLOCK nba-2k11 0xOFFSET REVIEWED_MAP.json output/ch-events.bin
```

This command also accepts `--native-elf`. The contract has schema 1 and a rules
list. Each rule requires `source_id`, `target_id`, `payload_word` (null for no
payload) and a nonempty `evidence` string. The following is a **synthetic syntax
example**, not an actual game mapping:

```json
{"schema": 1, "rules": [
  {"source_id": 70000, "target_id": 70001, "payload_word": null,
   "evidence": "Synthetic fixture only; no game semantic assertion"}
]}
```

The caller must establish and review the semantic evidence; writing an evidence
string does not validate it. There is deliberately no default identity map.
Event 90 rules can specify an exact consumed payload word, including zero. Other
payload-bearing event IDs block conversion even if an ID-only rule is supplied.
Missing mappings, duplicate rules, unsupported payload selectors, nonfinite times,
misaligned/out-of-range pointers and unterminated lists block the entire output.
All checks precede file writing. Input ELF/block and contract files are protected
from overwrite. A four-byte INT_MIN terminator follows the target rows.

The converter reparses its output and verifies mapped IDs and original float bits.
It retains duplicate markers, order and negative-zero time bits. CLI results retain
the applied rule evidence and report `gameplay_ready=false`, `complete_motion=false`.
Do not insert this standalone table into a game archive: header relocation, bank
registration, bind hierarchy, mirrored state and other tracks are still required.

## Phase boundary and next work

This phase completes bounded event/payload dependency inspection and the guarded
offline table writer. It does **not** complete semantic conversion of every marker
or the nine other payload schemas. Next, prove donor bone-channel/bind correspondence
and remaining payload consumers, then assemble a complete motion-header adapter
with all dependencies accounted for. Additive shot-table allocation, blend graphs,
ball/contact behavior and controller defaults remain separate runtime work.
No RPCS3 or automatic/testing game build was run.
