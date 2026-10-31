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
  normal play.
- `cycler_asm.py`, `cycler_test.py`, `cycler_step_test.py`: Quick Game cycling
  caves and their tests.

These checks only model the game. Confirmed in-game: all three poll-rank entries
(scorebug, Team Select, matchup card), the transfer entries, Quick Game cycling and
the 30-second shot clock.
