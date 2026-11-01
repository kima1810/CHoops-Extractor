# RPCS3 game patches (College Hoops 2K8, BLUS30078)

`BLUS30078_imported_patch.yml` is an RPCS3 patch file for the 2026-27
year-patched EBOOT (V4.2 base build, PPU hash
`cd3a6cffbf5c1930053d0873658d0f3c46e19c8b`). Copy it to
`<RPCS3>/patches/imported_patch.yml` (or import it from Manage > Game Patches)
and enable the entries you want. These are emulator patches only; the editor
does not patch executables.

| Group | Entries |
| --- | --- |
| Frame rate | 60 FPS (all screens): also set Vblank Rate 60 in the game's custom config |
| Poll rank | Scorebug (`#5 DUKE`), Legacy Team Select (`#6 ILLINOIS`), pregame matchup card (`#6 Fighting Illini (13-0)`) |
| Recruits | Taller centers, taller guards/wings, skilled PF/C, international tiers |
| Transfers | Frequency levels, unhappiness levels, no sit-out |
| Quick Game | LT/RT team cycling in conference member order (alphabetical once the roster's member lists are sorted) |
| Rules | 30-second shot clock (was 35) |
| NCAA Tournament | 68 teams with a four-game First Four (Stage 1, plus a DEBUG copy that logs the bracket build); First Four on the Tournament Tree (Stage 2) |

Each entry's `Notes` field describes what it changes and which entries it must not
be combined with.

## Poll-rank code caves

The Team Select and matchup entries are RPCS3 `calloc` blocks at the game's own
STR_FROM call sites (Team Select 0x6E42D8, matchup mascot 0x70EEEC). They make the
original call, look the team up in the media poll (0x5BDB44, slots 0-24), and when
ranked rewrite the text with the game's formatter and English templates `#{0}` and
`{0} {1}`. The scorebug entry replaces the two scorebug name providers in place.

Do not turn the Team Select STR_FROM call into a nop: another path (0x6E4724)
branches in just before it, and doing so crashed the game.

## Quick Game team cycling

LT/RT normally steps through a conference in team-table order, so teams moved in by
realignment appear after the conference's original schools. The entry places
`calloc` blocks at the library walkers nthTeamInConference (0x1BF690),
nextTeamInConference (0x1BF93C) and prevTeamInConference (0x1BF82C). For every
conference except 32 (the all-D1 list) they walk the conference member list
(roster conference +0x6E0, count +0x870) with the game's own team filter.

Do not try to get this order by moving team records in the roster: the game keys
something outside the roster on table position, and a reordered table crashed it.

## Shot clock

The reset value is the float 35.0 at library TOC +0x6714 (0xA5B1DC), read only by
the shot-clock reset code (0x3C80B4, 0x3C8568, 0x3C8580), which stores it as the
live, reset and maximum shot clock (game state +0x280/+0x284/+0x288). The entry
writes 30.0 there.

## NCAA First Four (68 teams)

The stock field is 65 teams with one play-in game (event 90: the two lowest automatic
bids, winner to East 16). Stage 1 turns this into a four-game First Four without
changing the save layout, so it can be enabled in an existing Legacy before Selection
Sunday:

| Game | Teams | Day | Winner to |
| --- | --- | --- | --- |
| event 90 | two lowest automatic bids | Tuesday | East 16 |
| event 2 | next two lowest automatic bids | Tuesday | South 16 |
| event 3 | last at-large team in vs first team out | Wednesday | Midwest 11 |
| event 4 | second and third teams out | Wednesday | West 11 |

Events 2-4 are the 2K Sports Classic first-round events, which are finished by March.

- Selection (0x5C1D30; also the projection screen 0x5BFCDC) marks the four lowest
  automatic bids as play-in teams. The NIT fill (0x5C2124) leaves out the three best
  teams outside the field, which become the extra at-large play-in teams.
- The bracket builder (0x590084) is replaced. It points link-table rows 0-2 at the
  regionals, and falls back to the stock builder if the field does not have four
  play-in teams. The real selection stores automatic bids as type 0 and at-large as
  type 1, so the builder reads the at-large type from the best candidate.
- While events 2-4 hold a play-in game (state type 3, two teams), the five readers of
  the event record table (0x58C270, 0x58F234, 0x58F600, 0x58F700, 0x58F8A4) use event
  90's record, giving the "NCAA Play-in Game" name and schedule config.
- NCAA appearances (0x5C19E0) are credited from the built bracket, so all 68 teams
  count; play-in teams get the seed of the slot their game feeds.
- The season reset does not restore link rows, so eventBuild (0x58F848) and game finish
  (0x58F310) put the Classic rows back to (e, 6, e-1) whenever events 2-4 are built or
  finish as holiday events.

Stage 2 (needs Stage 1) covers the Tournament Tree. Its NCAA pages are every type-3
event with games in event order, so events 2-4 already appear before event 90. The
NCAA tree is one bracket with a single play-in box; the entry makes that box show the
open First Four page's game (0x65A548), makes LT/RT step from the page on First Four
pages (0x65FD60, 0x65FE98), and redraws the bracket and places the cursor on the box
when a new First Four page's game is not on screen yet (0x65A264). It also hides seeds
on those pages (0x65DC28, 0x65DCA0) and shows "PLAY-IN GAME WINNER" in every regional
slot a First Four game feeds (0x65DF24, 0x65DE88, 0x65DEE0, 0x65E7F4; in Legacy the
unknown team is drawn from 0x65DE88). The Selection Sunday Show finds a team's region
(0x5E89BC) only in events 91-94 and 90; Stage 2 also gives teams in events 2-4 the region
their game feeds. Its seed lookup is unchanged, so play-in teams show no seed, as in stock. The show's data step
fills each regional's empty slot with the teams of the First Four game feeding it (0x5EC420,
0x5EC43C; an 11-seed slot gets the first team, 0x5EC438/0x5EC44C), and the game presentation
seed (0x5F9A08) gives First Four teams 16 or 11. Its First Round Games boxes name each
play-in matchup ("Team A vs. Team B", template 0x0018C1FB) instead of "Play-in Winner"
(0x5E6034). Stage 1's undecided 11-seed slots crashed the show's commentary (a line
reads the opponent's conference, 0x5EA374); Stage 2 gives the commentary the first team of the
feeding First Four game whenever its featured team is empty (0x5E92A8). The show's play-in team
values (speech variables 0x7E/0x7F, 0x5E925C/0x5E9274) name the First Four game feeding the
current matchup, or no team for a matchup without one.

### Selection Show commentary

The announcer's lines come from the `director` record in Director.iff, run on the game's
script VM (0x77D2C0, one native call per step; opcodes map through the record's import
table). The show only raises a generic event (0xD9); the dispatcher (0x592C0) builds
candidates with a compiled line tree (0x60310), whose conditions are value expressions
evaluated by 0x5BABC (facts via 0x77F670 and 0x77F798), then tries them in order through
the line check 0x59D30 and starts the first that passes. Three things kept the play-in
line to East:

- The 1-16 line group is the only one with play-in lines, and its tree reaches them only
  when the matchup's team 1 is in region 91 (East), where stock's single play-in game went.
- Every show line has repeat setting 0 (once per show), and 0x59C6C stamps a line when it
  plays, so East used it up.
- The group's seed lines are always available as alternatives.

Stage 2 adds three caves. 0x5BABC returns team 1's seed as 1 and its region as 91 for the
group's two feature expressions whenever a First Four game feeds the current matchup, so
fed 1-16 and 6-11 matchups take that branch. 0x59D30 lets the play-in lines (team A, then
team B) play for fed matchups, refuses them elsewhere, and holds back that group's seed
lines for fed matchups. 0x59C6C does not stamp the two play-in lines. The group's nodes are
recognised by their bytecode, so Director.iff stays stock. A school with no recorded
name clip (for example one that joined Division I after 2007) is not spoken.

## Tools

`tools/` holds the generators and offline checks (Python, `keystone-engine` and
`capstone`; paths to the decrypted EBOOT and the RPCS3 patch file are set at the
top of each script):

- `rank_asm.py`: scorebug providers; `rank_interp.py` runs them in a small PPC64
  interpreter with modeled game calls (Unicorn's PPC64 is not usable here).
- `rank_hook_asm.py`: shared assembler (hand-encoded branches, position
  independent) and the poll-lookup body.
- `rank_site_asm.py`, `rank_site_test.py`, `rank_site_write.py`: Team Select and
  matchup caves, their tests, and the writer that updates the patch file.
- `probe_asm.py`, `probe_test.py`, `probe_patch_write.py`: diagnostic probes that
  write `TAG caller-address [text]` to `log/TTY.log` through sys_tty_write. This is
  how the real name call sites and the team cycler were found; leave them out of
  normal play. Besides text and an index, a probe can log the stack back chain
  (`bt_test.py`) or dump six words from a register or computed address.
- `show_probe_write.py`: the Selection Show commentary probe entry (variables, tokens,
  director facts and their values, speech stream lookups; not shipped).
- `cycler_asm.py`, `cycler_test.py`, `cycler_step_test.py`: Quick Game cycling
  caves and their tests.
- `first_four_asm.py`, `first_four_test.py`, `ff_debug_test.py`: First Four Stage 1
  caves (and the DEBUG builder report) and their tests.
- `first_four_tree_asm.py`, `first_four_tree_test.py`: Stage 2 Tournament Tree and
  Selection Show caves and their tests. The commentary tests read a locally extracted
  `director` record from Director.iff (game data, not included; path at the top).
- `ff_patch_write.py`: writes the three NCAA Tournament entries into the patch file.
- `tree_probe_write.py`: diagnostic Tournament Tree navigation probes (not shipped).

These checks only model the game. Confirmed in-game: all three poll-rank entries
(scorebug, Team Select, matchup card), the transfer entries, Quick Game cycling, the
30-second shot clock, and both NCAA Tournament stages (four play-in games, winners in
East 16 / South 16 / Midwest 11 / West 11, appearance credit, the next season's 2K
Sports Classic, the four play-in pages on the Tournament Tree, and the Selection Show
naming every First Four matchup on screen and in the commentary: East and South 1-16,
Midwest and West 6-11).
