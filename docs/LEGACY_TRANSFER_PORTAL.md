# Legacy transfers and a recruitable portal: feasibility

Read-only native research, 2026-10-21, on the supplied PS3 College Hoops 2K8
revision. Addresses are revision-specific virtual addresses, not universal file
offsets. Original executable, saves and game archives remain unchanged. No
emulator, gameplay test, executable patch or JB build is supplied. The editor now
provides read-only recruiting diagnostics; it does not implement native transfers.

## Assessment

**Higher transfer activity has concrete native control points. A recruitable
transfer portal is plausible, but is a larger Legacy-system change.** The most
promising initial design extends the game's existing transfer list and destination
selection while retaining existing player objects and the final membership commit.
The owner subsequently selected integration into the ordinary recruiting pool (see
the follow-up below). That route remains less established:
the recruiting record, eligibility, interest, scholarship and calendar contracts
have not been shown compatible with existing college players.

The game does not simply choose a random destination for each transfer. Its
assignment routine scores eligible schools and retains the best candidate. This
provides a specific interception point for user recruitment decisions. Neither a
fully recruitable pool nor increased transfer rates have been implemented here.

## Confirmed transfer pipeline

| Stage | Native entry | Observed behavior |
| --- | --- | --- |
| Generate outgoing queue | `0x5B4E50` | Resets queue, checks Legacy context +0x204, traverses schools and players, applies eligibility/state and chance/value gates, then enqueues candidates. The exact setting name of +0x204 is unresolved. |
| Insert/sort candidate | `0x5BCA74` | Stores a 12-byte row: player pointer, source-school pointer, destination-school pointer initially zero. Orders rows using the position-aware player evaluation at `0x74AA30`. |
| Select destinations | `0x5BCCF4` | Scores candidate schools using capacity/availability, a per-school arrival counter, player/school values, distance and other terms; excludes matching source/destination school identities. Retains the best score rather than a random school index. Full term semantics remain incomplete. |
| Finalize transfer | `0x5BC250` | Removes players from source membership, updates a player count byte, sets scholarship and Transfer sit-out status, then adds destination membership. A zero destination takes a separate removal path; it is not a proven safe uncommitted portal state at finalization. |
| Reconcile school state | `0x5BC990` | Adjusts packed school counters around the queued source/destination records. Precise neighboring counter meanings require further tracing. |
| Save/load queue | `0x5BC660` / `0x5BC854` | Serializes count plus 0x12CC bytes, temporarily rebases the three pointer columns against the roster base, and restores native addresses. The enclosing save-file offset is not established. |

Queue count is held at `0x12EA4C74`; rows begin at `0x12EA39A8`.
The serialized span is **401 twelve-byte records**, while insertion increments
active count only below **400**. The extra row permits insertion/sorting at a full
queue; it is not evidence that the save can safely hold arbitrary extra transfers.
Do not enlarge count independently of all loops, scratch storage and serializers.

The prior sit-out experiment changes only the Transfer-code insertion at
`0x5BC334`. It does not create a portal, increase transfer frequency, change
existing saves' eligibility, or make destination selection interactive.

## Transfer frequency controls

At `0x5B4F0C..0x5B4FA4`, the candidate generator extracts
`state = (player_anchor_word_0x88 >> 3) & 7`, skips zero, and computes:

```
chance = clamp((state - 1) / 3.0, 0.0, 1.0)
queue_candidate only if random_value < chance
                  and secondary_player_value < 0.66 * position_evaluation
```

The random helper `0x7C5430` constructs a float in [0, 1) from PRNG bits. The
chance formula is confirmed by the instructions and constants, not an inferred
menu label. For state values 1, 2, 3 and 4+, the chance gate is respectively 0,
about 33%, about 67% and 100%. **These are conditional gate probabilities, not the
percentage of all players who transfer.** Other filters and the second gate still
apply. The exact meaning and writers of this three-bit state are not established;
calling it a proven dissatisfaction or transfer-demand field would be premature.

The second gate uses `0x74AA30` (position-aware weighted player evaluation) and
`0x744C40` (player +0x70 byte converted through `0x742BD0`). The latter's precise
localized meaning is unconfirmed. Constants are 3.0 at `0xA61340` and approximately
0.66 at `0xA6133C` in this revision. Candidate filters also inspect the upper nibble
of player anchor +0x84 and bit 0x20 at anchor +0x0A. Do not remove these as if they
were redundant probability checks.

Possible scoped changes, still proposals:

- Add an explicit transfer-intensity multiplier to this chance calculation.
  Multiplication alone cannot create candidates in states whose base chance is
  zero; broadening that population needs a deliberate additional rule.
- Raise the 0.66 threshold to allow more otherwise-eligible players past the
  secondary gate. This changes which players qualify, not just randomness.
- Retain eligibility filters, queue capacity, ranking and scholarship checks;
  trace state generation before promising a particular annual transfer count.

Do not globally replace shared float constants. Any future experiment should
scope changes to this consumer, match the executable revision and preserve an
immutable original. A visible intensity setting is not yet exposed by the tool.

## Portal implementation options

**Preferred initial route: a separate transfer-recruiting list backed by existing
college-player identities.** The executable already registers
`PlayerTransferListMenu`, `PlayerTransferTeamMenu` and `PlayerIncomingTransferMenu`.
Source/destination text providers at `0x69F298` / `0x69F42C` query the queue through
`0x5BC4F4` / `0x5BC5A0`. The incoming-menu callback at `0x69F1B4` can, after a
positive confirmation result, call `0x5BC398` to clear a player's destination.
This proves an existing menu-to-assignment mutation route; it does not establish
an offer, signing action or user-selected destination setter.

A portal could expose this list before automatic assignment/finalization, let
users pursue candidates, reserve eligible scholarship spots, retain CPU decisions
for unclaimed candidates, then use the existing finalizer once. The exact calendar
window, cancellation semantics, commitment locking and reentrant/save-resume
behavior must be established first. Leaving zero destinations until the existing
finalizer runs is unsafe: its zero branch is not an offer-waiting state.

**Ordinary recruiting integration:** `RecruitCard_ABLMenu` resolves separate card
callbacks, including `0x6A4534`, with its own selection/context state and paths
through `0x5E05B0`, `0x5E0838` and `0x5E07B8`. That is a concrete starting point,
not proof that appending a player pointer makes a valid recruit. A transfer must
retain identity, class, remaining eligibility, statistics, appearance and history;
copying it into a freshman record risks duplication, resets and broken links.

The existing Legacy save adapter edits only the recognized embedded roster and
preserves outer mode state. It does not expose the serialized transfer queue or
recruiting contracts, so CSV or roster reassignment alone is not native portal
recruiting.

## Remaining work and acceptance gates

1. Trace callers/state transitions for generation, destination selection, counter
   reconciliation and finalization; identify the user-interactive window.
2. Trace the three-bit state writers and both player-value consumers to named
   fields; measure candidate counts on user-supplied season snapshots.
3. Establish transfer/recruit list ownership, filters and scholarship reservation;
   choose a dedicated list or prove an adapter for ordinary recruiting.
4. Locate enclosing save sections and prove save/load, cancellation and season
   resume without duplicate identities or double membership commits.
5. Prepare a separate revision-guarded experiment only after those contracts are
   understood. Runtime acceptance remains owner-run: CPU/user teams, full rosters,
   no eligible destination, queue saturation, class/eligibility, save/reload and
   multi-season progression. No compatibility certification is claimed.

## Verification

Ghidra focused tracing produced 17 function reports across two passes, cross-checked
against original PowerPC disassembly and literal constants. A private read-only
audit verifies source digest and byte equality, the exact subtraction instruction,
frequency constants, all eight state-gate values and 401-record span arithmetic.
This checks static interpretation, not runtime distribution or save compatibility.
No proprietary listings, source bytes, game assets, local paths or fingerprints
are published. The public change is documentation only.

## Transfer recruits and three-priority policy — follow-up

The owner clarified that transfers must appear in the **offseason recruiting
pool**, beside existing HS and JUCO prospects, with labels such as `TR SO (RS)`.
Each transfer receives one randomly chosen primary motivation: more playing time,
proximity to hometown, or team ranking. Existing HS/JUCO recruiting must remain
intact. This supersedes a separate transfer screen as the intended final product;
a dedicated queue adapter remains a possible implementation detail.

### Native HS/JUCO labels are confirmed

Recruit formatter `0x7582F4` builds a nine-entry localization table:

| Recruit class code | Current output |
| --- | --- |
| 0..3 | HS FR, HS SO, HS JR, HS SR |
| 4..5 | JC FR, JC SO |
| 6..8 | Placeholder text (`bogus`), not implemented transfer classes |

Getter `0x75315C` extracts a four-bit field at recruit-object +0x40, shifted right
21. This is **a different object/enum from the college player's class at anchor
+0x84**. College code 4 means Freshman; recruit code 4 means JC FR. Blindly passing
a college player to the recruit formatter would mislabel it or read unrelated
fields. Empty/placeholder display entries do not establish safe new recruit types:
all class filters, allocation, progression and commitment consumers must agree.
Four-bit storage by itself is not proof that adding class codes is sufficient.

The new offline `research.transfer_portal.transfer_label()` produces `TR FR`,
`TR SO`, `TR JR`, `TR SR`, optionally suffixed ` (RS)`, from explicit established
college class and historical redshirt-used inputs. It writes no native enum.
Transfer status is independent of redshirt usage and transfer sit-out code 2;
those must not be conflated. The future adapter must supply the class appropriate
to its season phase, avoiding a second class increment at signing or rollover.
Graduate transfer eligibility is unresolved and is not silently invented.

### Existing native motivation routes

Preference formatter `0x757F04` uses five native localization choices:
feeling wanted, being close to home, getting good coaching, playing at a big
program, and getting playing time. Getter `0x753AB4` reads a seven-bit index at
recruit +0x40 shifted right 7. That index selects a **20-byte preference-ranking
row**, not a direct motivation enum. The selected row is searched for the
requested rank before the formatter picks a caption. Writing 0/1/2 as if this
field directly represented our three motivations would be incorrect. The backing
table is initialized runtime data. Follow-up tracing of `0x75B6C0` establishes
96 rows: lexicographic permutations of ranks 0..4 with the first column restricted
to 0..3. It is not all 120 permutations. All five columns are distinct ranks, not
five motivation IDs. Scoring consumer `0x756070` applies weights 1.0, 0.8, 0.6, 0.4
and 0.2, with rank zero strongest; native single-precision values are retained.
The rank-weight table is at `0x10034124` in this revision. The new read-only
`native_preference_profile(index)` reconstructs all 96 established rows and rejects
96..127 even though the field can physically represent those values. The complete
term-to-native-interest and persistence contracts remain unfinished.

`0x75C248` computes geometric separation using two location lookups and coordinate
accessors `0x75BB08` / `0x75BB50`. The transfer selector passes the player's +0x22
location identifier and the school's +0x15A identifier. This supports hometown
proximity as a native input, but its unit conversion and missing/international
location cases need validation before claiming distances in kilometers.

`0x764050` computes five position-specific team-depth values. It begins with 4.0
per position, subtracts full player evaluation for scholarship players and half
for walk-ons who pass the class filter, accounts for pending recruits, then scales
by 0.25. This is useful opportunity evidence, **not projected minutes**. New portal
interest must evaluate the post-departure/post-graduation roster and pending
commitments without counting the prospective transfer twice.

Recruit-card setup `0x5E05B0` calls `0x753E94` (searches an 800-entry ranking list)
and `0x753EE4` (position-relative rank). These concern recruit rankings, not proof
of team poll ranking. Likewise, “playing at a big program” is not automatically
the owner's requested current team ranking. Trace the actual season team-ranking
source rather than substituting player rank or prestige without disclosure.

### Implemented offline policy and remaining native integration

`choops_py/research/transfer_portal.py` now supplies:

- A uniform three-way pseudorandom priority draw keyed by a 32-byte plan seed,
  season identity and stable player identity. Length-framed inputs and rejection
  sampling avoid identity ambiguity/modulo bias. Repeating a screen, input order
  or reload cannot change the draw **provided the integration retains those inputs**.
- Label formatting independent of native record mutation, plus inspection of the
  96 initialized native preference profiles and their float32 weights.
- Explainable school ordering using one chosen priority: projected minutes gained
  over the source school, hometown distance, or lower numeric team rank. Unranked
  schools follow ranked schools. Equal metrics use school identity as a stable
  tie-break. Source school, no scholarship capacity and explicit ineligibility
  are excluded; duplicate school identities and invalid/nonfinite metrics fail.

These are caller-supplied synthetic projections in explicit units. No native
interest percentage, minutes forecast, location decoder, season rank reader,
persistence writer, in-game TR label or recruiting-pool insertion is installed.
School ordering does not reserve scholarships or sign players. An availability
snapshot can become stale when another recruit commits; a future native adapter
must revalidate and reserve at commitment. The policy does not modify the game's
PRNG, ordinary HS/JUCO prospects, native settings or game-data CSV columns.

The requested final integration must persist each transfer's identity, class,
redshirt history, offseason priority and recruiting state; expose it through the
existing pool/list/card/search paths; allow CPU/user recruiting; and commit through
one validated membership path before season rollover. It must not finalize or
delete uncommitted zero-destination queue entries while recruiting remains open.
This work is a testable policy foundation and stronger format evidence, **not a
playable portal**. Original EBOOT, assets, roster and saves remain unchanged.

## Native pool, saved component and rollover — continuation

### Confirmed pool structure

The native accessors behind `0x4A3834` / `0x4A25E4` resolve to `0x1BC7A4` /
`0x1BC7C4`. They read roster-header count +0x48 and base +0x4C, with an exact
**0xD8-byte recruit stride**. The stock decoded roster reserves 2,000 records
(432,000 bytes); all are zero before Legacy initialization in the inspected input.
This is allocated storage, not evidence of 2,000 active prospects or permission
to overwrite records later. The continuation below traces annual regeneration;
transfer-specific reservation and safe proxy reuse remain unresolved.

`inspect-recruit-pool` now audits that directory through existing roster adapters,
including recognized Legacy wrappers. It reports nonzero-record class, preference,
flags, location identifier and linked-interest head, plus record/source hashes.
Unknown enum/profile/head values are diagnosed rather than relabeled as transfers.
Known-table overlap and other directory targets inside the pool are rejected.
All-zero rows are reported as blank without certifying them reusable. Unknown
bytes remain untouched; no new editable roster table or CSV columns are added.

### Linked interest nodes and ownership

`0x5C3044` bounds node indices to 0..15999. `0x5C3064` initializes an eight-byte
node with school sentinel 0x7FFF, next -1, score zero and two zero bytes. Live
nodes contain signed school +0, signed next +2, signed score +4, raw bytes +6/+7.
`0x5C3144` pops the free head, `0x5C31C8` returns an initialized node to that list,
`0x5C3220` detaches a school node, and `0x5C3350` inserts by descending score.
The two trailing bytes have consumers but are not given speculative full meanings.

The native ownership auditor `0x5CA108` traverses recruit lists only when record
flags +0x2D have bit 0x04. The new graph audit follows that filter when used through
the CLI/component reader. It rejects cycles, shared ownership between recruits or
the free list, duplicate schools and invalid indices/school bounds. Unowned nodes
are counted; without established complete ownership they are **not called leaks**.
A separately supplied raw interest block must be exactly 16,000 x 8 bytes.

A second independent 16,000-node pool links school +0x260 queues to recruit
pointers: `0x5C3580` finds a recruit in that school's list; `0x5C34F0` clears a
node's pointer, next +4 and remaining word +6. Its ownership must be preserved as
well as the first pool. The current reader reports relative-reference bounds but
explicitly does not certify complete second-pool ownership or all queue semantics.

### Exact native recruiting serialization component

Size getter `0x5C5450` returns **0x415A4**. Serializer `0x5C5468` and loader
`0x5C57B0` agree on these component-relative regions:

| Offset | Size | Established structure |
| --- | --- | --- |
| +0x0 / +0x4 | 4 bytes each | First and second free-list heads |
| +0x8 | 0x10 | Four queue counts |
| +0x18 | 0x10 | Four additional raw counters |
| +0x28 | 0x1F400 | First interest-node pool |
| +0x1F428 | 0x1F400 | Second pointer-bearing node pool |
| +0x3E828 | 0x2800 | Four 0xA00 queue blocks; active entries use 20-byte records |
| +0x41028 | 4 | Additional raw word |
| +0x4102C | 0x578 | Preserved tail; complete semantics unresolved |

The second pool's pointer words are rebased against the roster base for saving.
Active queue records similarly rebase three pointer fields at +4/+8/+0xC. The
reader retains record/tail hashes and reports bounds; a pointer being inside the
roster does not prove its referent type or authorize changing it. Each queue block
physically holds at most 128 records; larger declared counts are rejected.

The enclosing `0x595D64` / `0x595FB0` aggregate places recruiting after components
of size 0xC9F8, zero, 0x4228 and 0x7F8: **aggregate-relative offset 0x11418**.
That is not a certified USERDATA file offset. The outer save also serializes a
roster length/payload and mode context, and offsets depend on that envelope.
The owner has no offseason save available. Consequently the new reader accepts
an **explicitly identified component** through `--recruiting-state`; it does not
scan for magic values, guess its USERDATA location or add a Legacy-mode writer.
The existing Legacy roster wrapper/preservation behavior remains intact.

### Signing and rollover require a transfer-specific path

Rollover `0x5B61D8` processes flags &0x04 recruits with class greater than 2,
increments their recruit class through `0x752A34`, resolves the committed school,
allocates a college-player slot with `0x744298`, calls **0x7570EC**, sets scholarship
and adds membership through `0x764548`.

Converter `0x7570EC` zeroes a 308-byte destination object while retaining its newly
allocated identifier, then fills names, ratings, appearance and other fields from
the recruit. It writes the advanced recruit class to player anchor +0x84 and
clears eligibility-related bits near its tail. This is appropriate to creating a
new freshman/JUCO player, **not preserving an existing transfer's identity/history**.
It also shows why placeholder recruit class slots cannot simply become transfers:
class advancement and conversion would apply the wrong semantics.

The portal needs an established proxy-to-existing-player binding and a branch
before normal class advancement/allocation/conversion. Signing must validate and
reuse the original player, preserve career/redshirt/eligibility data, update
reciprocal membership once, reconcile scholarships and reclaim both recruiting
node families after the commitment is complete. The original transfer finalizer's
zero-destination removal path must not run while a portal candidate is uncommitted.
No such native branch, binding persistence or executable patch is installed yet.

### Verification and next action

Synthetic targeted pool/policy/CLI/Legacy suite: **88 passed**. Covers complete
16,000-node free chains, alias/cycle/duplicate-school rejection, unknown metadata,
section/queue bounds, source/dependency output protection, native flag filtering,
legacy wrapper preservation and unchanged opaque data. Private read-only audit
checks all 2,000 blank stock records, exact source equality, and independently folds
native size getters to verify 0x415A4 / 0x11418. Ghidra and raw PowerPC agree on the
serialization and rollover routes. No actual offseason save roundtrip, native
pool insertion, executable alteration, emulator run or testing JB was performed.

Next establish transfer-specific slot reservation and binding lifetime, then
trace the calendar dispatcher that must hold transfers open through offseason
recruiting. A native writer must wait for complete allocation, dual-list,
proxy-identity and save-envelope contracts. The new audit is available now; the
requested playable transfer portal remains unfinished.

## Native-only portal and continuity requirement — continuation

The owner explicitly requires transfers to enter recruiting and sign **inside
Legacy mode**, with no external save-editing or editor-applied transfer workflow.
Players must keep statistics and team history through both transitions. The
existing offline policy is research support, not an alternative implementation.
The Legacy editor integration is read-only diagnostics only; normal roster-editing
features remain separate and do not become a portal.

### Annual recruit generation and native commitment

`0x75B0D0`, called from `0x5A5190` at `0x5A5ABC`, traverses the entire declared
recruit table rather than allocating individual records from a demonstrated free
list. It initializes recruiting state through `0x5C6500`. In its noninitial
branch, records lacking flags &0x04 or having class greater than 2 pass through
`0x5C5FF8` and are regenerated by **0x7599E8**. Younger flagged prospects instead
advance class and refresh selected fields. The other branch regenerates every
record. This is evidence of annual slot replacement, **not a safe spare-slot
allocator for transfers**; a proxy must not overwrite a live HS/JUCO prospect.
`0x1BC8D0` is a previous-record iterator, not an allocator.

`0x7599E8` creates recruit attributes and selects preference index `random % 96`
through setter `0x752AE0`. That setter replaces only word +0x40 bits 7..13. The
generator initializes commitment/status and the interest head. It does not bind a
recruit to an existing college player. `0x5C5FF8` releases the recruit's first-pool
interest chain and removes its links from school lists through the second pool.
Its use before regeneration establishes cleanup on that path; it is not sufficient
proof of correct proxy cancellation or persistent binding cleanup.

**0x5C8CD8 is a commitment routine, not a recruit generator.** It sets committed
through `0x752B08`, decrements the school +0x2A8 bits 24..27 counter, releases the
old interest chain, obtains a first-pool node with `0x5C3144` and inserts the
selected school with score 0x7FFF. It also handles school-side queues/messages.
Its caller at `0x5C9ED4` is in `0x5C9974`. Reusing this routine still requires
native proxy typing, sufficient node capacity, scholarship reservation and an
identity-preserving rollover branch. Calling it alone does not complete a transfer.

### Existing player-to-recruit conversion is not a transfer binding

`0x749184(player, recruit)` already copies names, appearance and rating-related
fields from a college player into a recruit. The menu callback at `0x6A5B24`
calls it at `0x6A5B7C` and then sets recruit flags &0x04. The converter writes
the college-player class nibble directly through recruit setter `0x752A34`
(call at `0x7491F0`). College FR..SR codes 4..7 conflict with recruit HS/JC codes:
this copier **cannot be used unchanged for portal display or rollover**.

It also does not retain a persistent reference to the original player or copy
career-history state. A recruit may be used as a presentation/recruiting proxy
only after reservation, initialization, class-label dispatch and a durable
original-player binding are established. The original college player remains the
authoritative identity; a new player created from this proxy would fail continuity.

### Player lifetime and membership hazards

The original transfer finalizer `0x5BC250` removes source membership first and
increments runtime player +0x2A4. Its zero-destination branch calls `0x74410C`.
That wrapper resolves through `0x49FF74 -> 0x1BC014` to a player pointer pool and
through `0x49D684 -> 0x1AE8D4` to **append that player to the reusable pool**, with
an observed 2,500-entry limit. It must never run for a still-recruitable portal
player. This trace does not imply that this routine immediately clears all stats;
the risk is later reuse of the retained player identity.

The opposite route `0x744298` retrieves a pool entry through `0x744250 ->
0x49DEC4 -> 0x1AE744` and removes it from that pool via `0x744154 -> 0x49C8C4 ->
0x1AE9F4`. These are pointer-pool operations, not a demonstrated fresh heap
allocation. Ordinary recruit conversion `0x7570EC` then zeroes/rebuilds the
destination core. Transfers must bypass both reusable-slot selection and that
conversion, retaining their own original player instead.

Source removal `0x7644B8` finds the player's slot and tail-calls indexed removal
`0x764260`; this updates the roster count, scholarship counters, roster list and
lineup references. Destination add `0x764548` can return without adding a player
or evict a walk-on when an 18-player team is full. It also assigns a jersey number
and school equipment bits. Therefore a portal commit cannot blindly remove the
source and assume the destination accepted the player. Validate both teams and
reserved scholarship/roster capacity before mutation, verify the outcome, and
make repeated signing/finalization idempotent. Do not claim those native routines
are side-effect-free or sufficient to preserve all historical associations.

### Statistics and team history acceptance contract

These are requirements for the future native implementation, not claims of
completed field mapping or tested behavior:

1. Preserve the original stable player identity and authoritative record. Neither
   portal entry, commitment nor signing may recreate it, return it to the reusable
   pool, reset career totals, or run freshman/JUCO initialization on it.
2. Preserve prior season statistics, awards and historical school associations.
   Changing current membership must not retroactively attribute old seasons to
   the new school. Retain the old team's records; append the new affiliation at
   the correct season boundary rather than replacing the past.
3. Keep class, redshirt usage and eligibility history distinct. Advance eligibility
   only through the established annual progression point, once. Portal entry or
   a repeated signing callback must not consume a season or double-increment a
   transfer counter.
4. While unsigned, preserve the player and binding through calendar transitions
   and ordinary in-game save/load. On commitment, distinguish an interest decision
   from completed membership change; on cancellation or failed capacity checks,
   leave player/history intact and release only owned recruiting resources.
5. Verify continuity before entry, while recruiting, after commitment, after native
   signing, after in-game save/load and next-season rollover. Include CPU/user
   signing, full destinations, repeat callbacks and unsigned/cancelled transfers.

Native player statistics menu/provider registration is now located through
`PlayerCardMenu_StatsMenu` and callbacks including `0x68C8C0`, which passes the
selected player into the menu binding path. This is a starting point for tracing
stat/history consumers, **not proof of complete career-stat or historical-team
storage semantics**. Those storage/link owners, proxy persistence and the exact
calendar interception window remain unresolved. Keeping an ID alone cannot
certify history preservation. No native patch or playable portal is installed.

### Legacy editor diagnostics

Open a College Hoops roster or supported Legacy save, then select **Recruiting
diagnostics…**. A resizable read-only view lists recruit slots, HS/JC class codes,
commitment, native traversal flag, location ID, preference profile and metadata
issues. Select a row to inspect ordered preference weights and raw interest head.
Unknown profiles/classes remain unresolved. Search and sorting never mutate data.
Blank records are reported as reserved blank storage, not available portal slots.
Malformed or absent tables give a local unavailable message without breaking the
ordinary roster editor. NBA rosters do not expose this College Hoops view.

Inspection uses an immutable snapshot in the normal worker. Results from a changed
source are discarded, and roster reloads close old diagnostics. There are no
apply-transfer, sign, recruit allocation, savedata-edit or save-plan actions here.
Full interest chains and history continuity still require separate native work;
this view must not be treated as evidence that the portal runs in game.
