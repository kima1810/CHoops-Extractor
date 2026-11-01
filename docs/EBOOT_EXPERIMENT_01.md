# Combined correction candidate — Ghidra follow-up

The owner subsequently reported that the original combined prototype was visually
broken and explicitly requested one corrected combined executable plus matching
IFFs and documentation. The five-variant package described below is historical;
it is not the current delivery format or proof of working visuals.

## Confirmed defects and corrective design

Ghidra with the supplied PS3 OPD/TOC method and original PowerPC disassembly
confirms aligned vector loads in the SCNE style loader. Several old companion
property blocks were only four-byte aligned. Their literal vectors parsed in
Python but were read from different aligned addresses natively. The city clones
also retained score identity/marker properties. The new private companion uses
16-byte tables and two independent city skeleton markers with their own names,
hashes and hierarchy links; the two score centers are retained.

City draw callbacks alone use the existing complete native text renderer, which
honors confirmed width fitting. Stats keep their custom text-tag parser/timing;
the shot clock keeps its callback. A global plain-renderer replacement was rejected
because it would lose those native behaviors. The main bar's permanent popup
plane is removed. A confined private stats hook draws the native blackbar scene
only with the existing message timing window, positive text opacity and a
nonempty provider string, uploads its native pose and resumes the original stats
callback. Native event popups retain their separate existing visibility checks.
No persistent visibility flag, new asset loader or general hook system is added.

Authored native fonts, title-case College Hoops / Reborn, one sixth-man literal,
square logos, source palette material IDs, removed divider/glare geometry and two
separate message rows follow the owner's CBS references. This describes intended
presentation; static checks do not establish the final rendered appearance.

## Verification and delivery limits

The local ZIP contains ONE debug/fake SELF EBOOT.BIN, gamedata.iff, english.iff,
README, native findings, validation and checksums. It retains the documented
modern arc/corner scoring and new-transfer sit-out experiment. Source files stay
unchanged. No ELF/control variants, game copy or executable generator are included.
No assets or executable patch implementation are committed to Git.

Five edited scenes reparse, all 257 other gamedata records compare exactly, both
IFFs prepare and pass build preflight, the SELF payload round-trips, and the scoped
executable changes retain the existing combined gameplay experiments. Nine bounded
synthetic instruction paths verify background on/off conditions and original
callback inputs, stack and nonvolatile-register preservation. These simulate the
small private wrapper; they are not game execution or renderer verification.

The changed blackbar inferred header span retains the old unreferenced bottombar
header as a checked tail. Its authored arrays remain inside the replacement
header. No blanket claim that all inferred spans are unchanged is made.

PR #32 separately adds public editor guards for native text alignment and bounded
width-fit flags. Its source verification reports 628 passed, 9 skipped and two
deselected; the exact-head isolated handoff carries the clean-checkout result.
This PR adds research/documentation only; no executable patching enters the editor.

Runtime visuals, every popup transition, physical PS3 acceptance and gameplay
compatibility remain unverified. Repository rules prohibit emulator launches and
automatic/testing JB builds. The broken earlier result is not relabeled a success;
the owner must test the matching combined set before runtime acceptance.

# Owner-authorized local executable experiment 01

2026-10-19. The owner explicitly authorized separate experimental copies for
modern NCAA three-point distance, native scorebug text and removal of transfer
sit-out assignment. This supersedes the earlier read-only decision **only for
these local experiments**. Originals remain immutable; no patching feature,
dependency, CLI, hook installer or executable writer is added to the editor.
Experimental executables, game artwork, fingerprints and local generators remain
outside Git. No merge or release is included.

## Deliverables and evidence boundary

Five local executable variants were generated: unchanged-code packaging control,
native scorebug names only, new-transfer sit-out removal only, modern three-point
logic only, and the combined prototype. Each has an audit manifest. Local ELF
copies remain available for inspection; the private ZIP includes five EBOOT.BIN
variants, companion overrides, validation summaries and manual test instructions.

These are debug/fake SELF envelopes, not retail-signed executables. The source's
authority/application/version/capability metadata is retained; no signing keys
are distributed. ELF-to-SELF payload/segment round trips pass. Acceptance by a
particular loader or physical PS3 is **not established**. The unchanged-code
control must be tested first to separate packaging failures from code changes.
No emulator/game was launched and no real/testing JB was built.

## Modern NCAA three-point boundary

The current [NCAA court diagram](https://ncaaorg.s3.amazonaws.com/championships/sports/basketball/rules/common/PRXBB_CourtDiagram.pdf)
specifies a 22 ft 1¾ in arc and 21 ft 7⅞ in corners, measured to the outside edge.
The prototype uses those imperial dimensions converted to 675.005 / 660.0825 cm.
It implements the clipped circular shape, including the straight corner segments;
increasing a circle's radius alone would give the wrong corner region.

New tracing establishes the following route in the supplied executable revision:

- `0x534FCC` initializes court dimensions. The path at `0x535054` derives two
  boundary globals at `0x12CAB9A4` / `0x12CAB9A0`, originally clamped together using
  612.1399536132812 cm. This old value is documented as code evidence, not an
  assumed exact correspondence to painted line dimensions.
- `0x3CA128` tests a point against the arc/side boundary with an input margin.
  `0x3CA344` transforms four authored sample points through player matrices and
  requires all four to pass. That four-point sampling remains intact.
- `0x3CB494` calls the four-point predicate; the surrounding decision selects
  3 at `0x3CB378` or 2 at `0x3CB4A0`. This is substantially stronger evidence than
  a matching numeric literal near a resource name.
- `0x3CBE08` computes signed distance to the same old boundary and is used by
  other court/gameplay paths. The prototype updates it alongside the predicate.

The experimental implementation redirects three entry points to small routines
inside verified zero file padding after the first executable LOAD. Its filesz
and memsz expand without moving original addresses, the entry point, imports,
TLS, other program headers or any original initialized data. Added routines use
volatile registers, preserve the existing TOC contract and balance stack/LR around
calls. This is static on-disk code redirection, not runtime memory injection.

The updated initializer retains the small-court width clamp but assigns separate
arc and corner limits. The distance helper evaluates the maximum of the side
distance and the circular distance on the front side of the basket. The point
predicate compares that signed distance to its existing margin. Basket placement,
court length, sampling points and unrelated tuning fields remain unchanged.

Painted textures, floor SCNE line geometry and editor alignment guides are **not
redrawn**. Use matching modern artwork for a meaningful visual test. Actual foot
contact, line-edge tolerance, scoring/statistics, simulation and special modes
remain user-test questions; synthetic geometry does not certify those behaviors.

## Native scorebug names and companion

Two conditional branch sites, `0x4EF9F0` / `0x4EFB08`, now reach the existing
team-name fallback in the experimental variants. The provider and fallback bodies
are unchanged. This is scoped to the supplied revision; it is not a universal
patch. Special tournament/mode behavior and localization remain untested.

The private companion builds on [scorebug PR #32](https://github.com/ZMO34/CHoops-Extractor-Reborn/pull/32)
test05 assets at `e7175a1c6a3a0a5009f06eaa3c5a9dbcb5ce68b0`. It adds two native
home_city/away_city text records beside the logos, retaining the ten original
text records' interpreted styles, enlarged scores/clocks, native title-case
branding, sixth-man label/meter and existing popup configuration. No names are
baked into logos. Only gamedata.iff and the existing companion english.iff are
supplied as overrides; original files are unchanged.

The text table, cloned styles and string references reparse, and the vertex stream
is byte-identical. Every original decoded logical byte remains unchanged; 261
other original record payloads remain as prefixes. **Their inferred spans are not
all identical:** moving the enlarged SCNE makes the preceding msd65d1 span include
44,720 abandoned original bytes. Native acceptance of that span extension and the
two new text records remains unverified. This is explicitly experimental asset
growth, not a certified runtime writer result. The manual sequence tests the
unchanged-code control with and without the companion before changed EBOOT code.
Preparation/build preflight accepts the two archives with no unapplied overrides.

## Transfer sit-out assignment

The transfer-finalization routine at `0x5BC250` removes players through the existing
membership path, updates its count byte, then processes destinations. The path at
`0x5BC314` retains scholarship assignment. After clearing the two redshirt bits
in player-anchor +0x84 (roster row +0x94), the instruction at `0x5BC334` inserts
Transfer code 2, followed by the normal destination-membership call.

The local prototype removes only that insertion instruction. The preceding clear
and following store remain, yielding None instead of Transfer for **new transfers
processed by this path**. Membership, transfer count and scholarship writes are
retained. Ordinary and medical redshirt handling elsewhere is unchanged.
No transfer flags already stored in existing saves are cleared. This is not a
retroactive save conversion or proof of every transfer/eligibility route. Check
lineups, actual participation, season progression and save/reload in a disposable
Legacy save before calling the sit-out rule removed in practice.

## Verification and manual acceptance

- Five variants pass diff allowlists, original-source digest checks, bounded
  branch-target checks and debug SELF/ELF payload round trips. The control ELF is
  identical to the original decoded ELF.
- Only the first LOAD grows for court variants. Other program headers, entry,
  original addresses/data and source files remain unchanged. Added routines are
  independently disassembled; nonvolatile register/TOC/LR contracts are reviewed.
- Synthetic geometry covers 60,000 samples across both directions, equivalence
  with the old equal-radius circle, margins and explicit apex/corner/join cases.
  A case inside the new circle but outside the straight corner catches the
  incomplete radius-only approach.
- 30,000 transfer-mask cases preserve every neighboring bit while removing code
  2 insertion. The actual original source and output code were also inspected.
- Companion reparse/resource preservation and two-archive preparation/preflight
  pass. ZIP integrity and exact private output fingerprints are recorded locally.

These checks do not execute game code. A byte allowlist bounds written bytes, not
all possible runtime effects. Full editor runtime suites are not rerun for this
documentation-only PR update; its public runtime code is unchanged. Exact-head
documentation checks are recorded in TEST_REPORT and the PR.

Manual order: unchanged-code control; control plus companion; names plus companion;
new transfer processing alone; modern arc/corners alone at both baskets; combined
prototype after individual cases. Keep a disposable build/save and restore its
original executable to roll back. No installation into the source game is done
by this work. Boot/gameplay/physical-PS3 acceptance remains entirely unverified.

## Cleanup scope

The local cleanup removed 1,502 generated fixture directories, 99 standalone
synthetic IFF outputs, three disposable test/type/lint caches and two clean,
reproducible review worktrees. Tracked active
regression tests, original games, supplied overrides, saves, user builds, research
evidence and the current experiment are preserved. Source tests are not obsolete
simply because their first commit is old.

Automatic approval review rejected a broader permanent deletion that included
historical release and scorebug packages, citing potentially useful artifacts.
Those historical packages remain pending the owner's specific approval. The
rejection was not bypassed; the completed cleanup was narrowed to verified
generated fixtures/caches and clean review checkouts. No GitHub release, branch,
open feature PR or source feature is deleted by this cleanup.
