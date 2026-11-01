"""First Four on the Tournament Tree (Stage 2, needs the Stage 1 entry).

The tree's NCAA pages already list events 2-4 (state type 3 with games, event order), titled
"NCAA Play-in Game" by Stage 1's record remap. The screen special-cases event 90 in two places:

  SEED  0x65DC28 / 0x65DCA0  play-in pages hide seeds only for event 90 -> also for First Four
        events 2-4 (type 3, two teams)
  TBD   0x65DE88 (Legacy 'TBD') / 0x65DEE0 (blank)  Legacy skips the label branch; the label is
        shown on those paths too
  LABEL 0x65DF24 (box text) / 0x65E7F4 (box style)  a regional first-round slot still waiting for
        a play-in winner reads "PLAY-IN GAME WINNER" only in the game event 90 feeds (East 1-16)
        -> any first-round game of the regional a First Four link (row src 90, or 2-4 while they
        are type-3 two-team events) points at
"""
import first_four_asm as F

EVENT_OF_GAME, GET_GAME, IS_GAME_24 = 0x58BC60, 0x58BF98, 0x65C170

SEED = """
    cmplwi 7, 3, 2
    blt 7, stock
    cmplwi 7, 3, 4
    bgt 7, stock
    lwz 11, {STATES}(2)
    mulli 12, 3, {STATE}
    add 11, 11, 12
    lwz 12, 0(11)
    cmpwi 7, 12, 3
    bne 7, stock
    lhz 12, 0xA8(11)
    cmpwi 7, 12, 2
    bne 7, stock
    cmpw 7, 3, 3
    b out
stock:
    cmpwi 7, 3, 0x5A
out:
"""
SEED_HOOKS = (0x65DC28, 0x65DCA0)

# r3 = 1 if the game (id at 0(GAME)) is a first-round game of a regional fed by a First Four link
FED = """
    stdu 1, -0x90(1)
    std 28, 0x70(1)
    std 29, 0x78(1)
    std 30, 0x80(1)
    std 31, 0x88(1)
    lwz 28, 0({GAME})
    mr 3, 28
    bla {EVENT_OF_GAME}
    mr 29, 3
    li 31, 0
    cmplwi 7, 29, 91
    blt 7, fdone
    cmplwi 7, 29, 94
    bgt 7, fdone
    lwz 9, {LINKS}(2)
    li 10, 21
link:
    lwz 0, 4(9)
    cmpw 7, 0, 29
    bne 7, linknext
    lwz 0, 0(9)
    cmpwi 7, 0, 90
    beq 7, fed
    cmplwi 7, 0, 2
    blt 7, linknext
    cmplwi 7, 0, 4
    bgt 7, linknext
    lwz 11, {STATES}(2)
    mulli 12, 0, {STATE}
    add 11, 11, 12
    lwz 12, 0(11)
    cmpwi 7, 12, 3
    bne 7, linknext
    lhz 12, 0xA8(11)
    cmpwi 7, 12, 2
    beq 7, fed
linknext:
    addi 9, 9, 12
    addi 10, 10, -1
    cmpwi 7, 10, 0
    bne 7, link
    b fdone
fed:
    li 30, 24
firstround:
    mr 3, 29
    mr 4, 30
    bla {GET_GAME}
    cmpw 7, 3, 28
    beq 7, yes
    addi 30, 30, 1
    cmpwi 7, 30, 32
    blt 7, firstround
    b fdone
yes:
    li 31, 1
fdone:
    mr 3, 31
    ld 28, 0x70(1)
    ld 29, 0x78(1)
    ld 30, 0x80(1)
    ld 31, 0x88(1)
    addi 1, 1, 0x90
"""
# box text: second team slot is 0x7FFF; label path 0x65DF58, blank path 0x65DEE0
LABEL_TEXT = FED.replace('{GAME}', '30') + """
    cmpwi 7, 3, 0
    beq 7, blank
    ba 0x65DF58
blank:
    ba 0x65DEE0
"""
LABEL_TEXT_HOOK = 0x65DF24
# In Legacy the game-mode check (0x65DB1C) sends an unknown second team straight to the TBD text at
# 0x65DEE0, so the stock label branch is never reached. This cave on the TBD path shows the label
# for fed play-in slots and otherwise runs the stock TBD code (addi r29,r1,0x78).
TBD = FED.replace('{GAME}', '30') + """
    cmpwi 7, 3, 0
    beq 7, tbd
    lhz 0, 6(30)
    cmpwi 7, 0, 0x7FFF
    bne 7, tbd
    ba 0x65DF58
tbd:
"""
TBD_HOOK = 0x65DEE0
# Legacy really draws the unknown second team from here: game-mode path, team object missing
# (0x65DB38) -> 'TBD' (r17 = loc 0x8806DFAB). Same check, then the stock addi r29,r1,0x78.
TBD2_HOOK = 0x65DE88
# box style: r24 = game entry, r25 = second team id; fed + TBD -> 0x65E848, else the stock checks
LABEL_STYLE = FED.replace('{GAME}', '24') + """
    cmpwi 7, 3, 0
    beq 7, stock
    cmpwi 7, 25, 0x7FFF
    bne 7, stock
    ba 0x65E848
stock:
    mr 3, 24
    bla {IS_GAME_24}
    cmpdi 7, 3, 0
    beq 7, other
    cmpwi 7, 25, 0x7FFF
    bne 7, other
    ba 0x65E824
other:
    ba 0x65E80C
"""
LABEL_STYLE_HOOK = 0x65E7F4


# NCAA pages draw the whole bracket. Boxes 63-66 are one play-in box per region (k = box - 63, region
# event = [TOC-0x2D0][k] + 0x5B); stock fills only the box of the region event 90 feeds (East), with
# getGame(90, 0). The boxes share one screen spot, and the cursor only moves onto drawn boxes, so the
# single East box is kept: on a First Four page (UI state [TOC-0x2D8] +0x18 = 2-4 while it is a
# type-3 two-team event) it shows that page's game, otherwise event 90's.
PAGE = '''    li 12, 90
    lwz 11, -0x2D8(2)
    lwz 11, 0x18(11)
    cmplwi 7, 11, 2
    blt 7, {L}done
    cmplwi 7, 11, 4
    bgt 7, {L}done
    lwz 8, {{STATES}}(2)
    mulli 10, 11, {{STATE}}
    add 8, 8, 10
    lwz 10, 0(8)
    cmpwi 7, 10, 3
    bne 7, {L}done
    lhz 10, 0xA8(8)
    cmpwi 7, 10, 2
    bne 7, {L}done
    mr 12, 11
{L}done:
'''
EAST_BOX = '''    lwz 9, {{LINKS}}(2)
    li 10, 21
    li 8, -1
{L}row:
    lwz 0, 0(9)
    cmpwi 7, 0, 90
    bne 7, {L}next
    lwz 8, 4(9)
    b {L}found
{L}next:
    addi 9, 9, 12
    addi 10, 10, -1
    cmpwi 7, 10, 0
    bne 7, {L}row
{L}found:
    lwz 11, -0x2D0(2)
    li 3, -1
    li 10, 0
{L}k:
    slwi 0, 10, 2
    lwzx 9, 11, 0
    addi 9, 9, 0x5B
    cmpw 7, 9, 8
    bne 7, {L}knext
    addi 3, 10, 63
    b {L}kdone
{L}knext:
    addi 10, 10, 1
    cmpwi 7, 10, 4
    blt 7, {L}k
{L}kdone:
'''
PLAYIN_BOX = ('''
    lwz 11, -0x2D0(2)
    slwi 0, 30, 2
    lwzx 9, 11, 0
    addi 9, 9, 0x5B
    lwz 11, {LINKS}(2)
    li 10, 21
row:
    lwz 0, 0(11)
    cmpwi 7, 0, 90
    bne 7, rownext
    lwz 0, 4(11)
    cmpw 7, 0, 9
    beq 7, east
rownext:
    addi 11, 11, 12
    addi 10, 10, -1
    cmpwi 7, 10, 0
    bne 7, row
    ba 0x65A570
east:
''' + PAGE.format(L='p') + '''    mr 3, 12
    li 4, 0
    bla {GET_GAME}
    ba 0x65A3B4
''')
PLAYIN_BOX_HOOK = 0x65A548   # li r3,0x5A (r30 = box - 63)
# LT/RT step from eventOf(cursor game); on a First Four page they step from the page instead
# (hooks on the nop after the eventOf call; r3 = event).
NAV = '''
    mr 9, 3
''' + PAGE.format(L='n') + '''    mr 3, 9
    lwz 11, -0x2D8(2)
    lwz 11, 0x18(11)
    cmpw 7, 12, 11
    bne 7, out
    mr 3, 12
out:
'''
NAV_HOOKS = (0x65FD60, 0x65FE98)
# After a page change the cursor is moved to the box holding the page's first game (0x65A23C); a new
# First Four page's game is not drawn yet, so when that search fails on a First Four page the cursor
# goes to the East play-in box. The cursor is often already there, and the zoomed view only redraws
# when it moves, so the bracket is first redrawn for the new page (0x65D8F8(event), as the unzoomed
# page change does). r30/r31 are free here (restored by the function's epilogue at 0x65A298).
# Replaces the loop's 'beq- cr7, 0x65A298' (not found).
CURSOR = '''
    bne 7, more
''' + PAGE.format(L='c') + '''    lwz 11, -0x2D8(2)
    lwz 11, 0x18(11)
    cmpw 7, 12, 11
    bne 7, give_up
''' + EAST_BOX.format(L='e') + '''    cmpwi 7, 3, 0
    blt 7, give_up
    mr 31, 3
    mr 3, 12
    bla {REDRAW}
    mr 3, 31
    bla {SET_CURSOR}
    li 3, 0
    bla {SET_CURSOR_SUB}
give_up:
    ba 0x65A298
more:
    ba 0x65A268
'''
CURSOR_HOOK = 0x65A264
SET_CURSOR, SET_CURSOR_SUB, REDRAW = 0x6F7B00, 0x6F7B30, 0x65D8F8
SET_VISIBLE, SET_BOX_GAME = 0x6F930C, 0x6F7A7C   # (v1.5 hide cave, no longer used)
PLAYIN_BOX_HOOK = 0x65A548   # li r3,0x5A (r30 = box - 63)


# Selection Sunday Show: a team's region (0x5E89BC) is searched in events 91-94 and 90 (East) only,
# so a team in First Four events 2-4 got no region. At the function entry: if the team (r3) is in
# one of them (type-3 two-team event), return the region its link row feeds; otherwise run the
# stock function. The seed lookup (0x5E932C) is left alone: play-in teams have no seed there,
# as in the stock game.
SHOW_REGION = """
    cmpdi 7, 3, 0
    beq 7, stock
    lhz 12, 0x15E(3)
    lwz 9, {STATES}(2)
    li 10, 2
event:
    mulli 11, 10, {STATE}
    add 11, 11, 9
    lwz 0, 0(11)
    cmpwi 7, 0, 3
    bne 7, nextevent
    lhz 0, 0xA8(11)
    cmpwi 7, 0, 2
    bne 7, nextevent
    lhz 0, 0x88(11)
    cmpw 7, 0, 12
    beq 7, member
    lhz 0, 0x8A(11)
    cmpw 7, 0, 12
    beq 7, member
nextevent:
    addi 10, 10, 1
    cmpwi 7, 10, 5
    blt 7, event
    b stock
member:
    lwz 11, {LINKS}(2)
    li 8, 21
row:
    lwz 0, 0(11)
    cmpw 7, 0, 10
    beq 7, region
    addi 11, 11, 12
    addi 8, 8, -1
    cmpwi 7, 8, 0
    bne 7, row
    b stock
region:
    lwz 3, 4(11)
    blr
stock:
"""
SHOW_REGION_HOOK = 0x5E89BC   # stdu r1,-0x90(r1): first instruction of the region lookup
# Game presentation seed (0x5F9A08, used by the upset/importance ratings): stock returns 16 + slot
# for event 90 teams and -1 for anyone outside 91-94/90. A team in First Four events 2-4 gets the
# seed of the slot its game feeds (link row +8: 16 or 11). Same entry check as SHOW_REGION.
SHOW_SEED = SHOW_REGION.replace('    lwz 3, 4(11)', '    lwz 3, 8(11)')
SHOW_SEED_HOOK = 0x5F9A08     # stdu r1,-0x90(r1)
# Selection Show data step (0x5EC04C): an empty regional slot (team r29-event, slot r30) is filled
# with event 90's two teams as its play-in pair (li r3,0x5A before getTeam at 0x5EC420/0x5EC43C).
# This picks the First Four event whose link row feeds that region and slot (slot = r30 + 1), else
# 90. Keeps r0, r4, r11 and cr0 (live at both sites).
SHOW_PAIR = """
    li 3, 90
    lwz 5, {LINKS}(2)
    li 6, 21
    addi 12, 30, 1
row:
    lwz 7, 4(5)
    cmpw 7, 7, 29
    bne 7, next
    lwz 7, 8(5)
    cmpw 7, 7, 12
    bne 7, next
    lwz 7, 0(5)
    cmpwi 7, 7, 90
    beq 7, take
    cmplwi 7, 7, 2
    blt 7, next
    cmplwi 7, 7, 4
    bgt 7, next
    lwz 8, {STATES}(2)
    mulli 10, 7, {STATE}
    add 8, 8, 10
    lwz 10, 0(8)
    cmpwi 7, 10, 3
    bne 7, next
    lhz 10, 0xA8(8)
    cmpwi 7, 10, 2
    bne 7, next
take:
    mr 3, 7
    b done
next:
    addi 5, 5, 12
    addi 6, 6, -1
    cmpwi 7, 6, 0
    bne 7, row
done:
"""
SHOW_PAIR_HOOKS = (0x5EC420, 0x5EC43C)   # li r3,0x5A
# The two play-in teams are stored as slot 15 and an extra slot 16 of the region's slot list (r20 =
# r1+0x138), since stock's empty slot is always the 16 seed. For an empty 11-seed slot (r30 = 10)
# the first team goes into that slot instead (it would otherwise stay empty and the real 16 seed would
# overwrite the store), and the extra slot, which pairs with slot 15, is left alone.
PAIR_STORE_A = """
    cmpwi 7, 30, 15
    beq 7, stock
    slwi 12, 30, 2
    stwx 3, 20, 12
    b done
stock:
    stw 3, 0x174(1)
done:
"""
PAIR_STORE_B = """
    cmpwi 7, 30, 15
    bne 7, done
    stw 3, 0x178(1)
done:
"""
PAIR_STORE_HOOKS = (0x5EC438, 0x5EC44C)   # stw r3,0x174(r1) / stw r3,0x178(r1)
# Selection Show "First Round Games": a matchup whose second team is not decided yet reads
# "Play-in Winner" (0x5E6034, widget text r31+0x10). This names the play-in game instead,
# "Team A vs. Team B" (template 0x0018C1FB "{0} vs. {1}"): team 1 of the show's current game
# ([TOC-0x2CE8] +0x10, converted by 0x4A2D44) is found in a regional, its opponent slot is
# 17 - seed, and the First Four event whose link row feeds that slot supplies the two teams
# (getTeam 0x58C0D4). Names come from team +0 via STR_FROM, formatted with the game's formatter.
# Anything missing -> the stock "Play-in Winner".
PLAYIN_NAMES = """
    stdu 1, -0x100(1)
    std 26, 0xD0(1)
    std 27, 0xD8(1)
    std 28, 0xE0(1)
    std 29, 0xE8(1)
    std 30, 0xF0(1)
    lwz 9, -0x2CE8(2)
    lwz 3, 0x10(9)
    cmpdi 7, 3, 0
    beq 7, stock
    bla {TEAM_OF}
    ld 2, 0x28(1)
    cmpdi 7, 3, 0
    beq 7, stock
    lhz 12, 0x15E(3)
    lwz 9, {STATES}(2)
    li 30, 91
region:
    mulli 11, 30, {STATE}
    add 11, 11, 9
    addi 11, 11, 0x88
    li 29, 0
slot:
    lhz 0, 0(11)
    cmpw 7, 0, 12
    beq 7, seeded
    addi 11, 11, 2
    addi 29, 29, 1
    cmpwi 7, 29, 16
    blt 7, slot
    addi 30, 30, 1
    cmpwi 7, 30, 95
    blt 7, region
    b stock
seeded:
    subfic 29, 29, 16
    lwz 11, {LINKS}(2)
    li 10, 21
row:
    lwz 0, 4(11)
    cmpw 7, 0, 30
    bne 7, rownext
    lwz 0, 8(11)
    cmpw 7, 0, 29
    bne 7, rownext
    lwz 28, 0(11)
    cmpwi 7, 28, 90
    beq 7, found
    cmplwi 7, 28, 2
    blt 7, rownext
    cmplwi 7, 28, 4
    bgt 7, rownext
    lwz 8, {STATES}(2)
    mulli 12, 28, {STATE}
    add 8, 8, 12
    lwz 12, 0(8)
    cmpwi 7, 12, 3
    bne 7, rownext
    lhz 12, 0xA8(8)
    cmpwi 7, 12, 2
    beq 7, found
rownext:
    addi 11, 11, 12
    addi 10, 10, -1
    cmpwi 7, 10, 0
    bne 7, row
    b stock
found:
    mr 3, 28
    li 4, 0
    bla {GET_TEAM}
    mr 27, 3
    mr 3, 28
    li 4, 1
    bla {GET_TEAM}
    mr 26, 3
    cmpdi 7, 27, 0
    beq 7, stock
    cmpdi 7, 26, 0
    beq 7, stock
    li 0, 0
    stw 0, 0x70(1)
    stw 0, 0x74(1)
    stw 0, 0x78(1)
    stw 0, 0x7C(1)
    addi 3, 1, 0x70
    lwz 4, 0(27)
    li 5, -1
    bla {STR_FROM}
    ld 2, 0x28(1)
    addi 3, 1, 0x78
    lwz 4, 0(26)
    li 5, -1
    bla {STR_FROM}
    ld 2, 0x28(1)
    lis 0, 0x18
    ori 0, 0, 0xC1FB
    stw 0, 0x80(1)
    li 0, 0
    stw 0, 0x88(1)
    stw 0, 0x90(1)
    stw 0, 0x9C(1)
    li 0, 2
    stw 0, 0x8C(1)
    addi 0, 1, 0x70
    stw 0, 0x94(1)
    lwz 9, {STR_T}(2)
    stw 9, 0x98(1)
    addi 0, 1, 0x78
    stw 0, 0xA0(1)
    stw 9, 0xA4(1)
    addi 3, 31, 0x10
    addi 4, 1, 0x80
    addi 5, 1, 0x88
    li 6, 0
    bla {FORMAT}
    ld 2, 0x28(1)
    addi 3, 1, 0x70
    bla {STR_FREE}
    ld 2, 0x28(1)
    addi 3, 1, 0x78
    bla {STR_FREE}
    ld 2, 0x28(1)
    ld 26, 0xD0(1)
    ld 27, 0xD8(1)
    ld 28, 0xE0(1)
    ld 29, 0xE8(1)
    ld 30, 0xF0(1)
    addi 1, 1, 0x100
    ba 0x5E5530
stock:
    ld 26, 0xD0(1)
    ld 27, 0xD8(1)
    ld 28, 0xE0(1)
    ld 29, 0xE8(1)
    ld 30, 0xF0(1)
    addi 1, 1, 0x100
"""
PLAYIN_NAMES_HOOK = 0x5E6034   # addi r29,r1,0xFC (start of the "Play-in Winner" text branch)
TEAM_OF, GET_TEAM = 0x4A2D44, 0x58C0D4
# Selection Show commentary: speech value functions ask for the featured team (0x5E928C) and read
# its fields. In a bracket-games segment the featured team can be the undecided opponent of a
# First Four slot (null), and e.g. the conference lookup (0x5EA374) then crashed in the Midwest
# 6-11 game. When the featured team comes back null, this returns the first team of the First Four
# game feeding that slot: team 1 of the current segment game (0x5E9184), its regional slot j, the
# link row with slot 16 - j, getTeam(P, 0). Otherwise null stays null. Hook after the lookup.
FEATURED = """
    cmpdi 7, 3, 0
    bne 7, done
    stdu 1, -0x80(1)
    std 30, 0x70(1)
    std 31, 0x78(1)
    bla {SEG_TEAM1}
    cmpdi 7, 3, 0
    beq 7, none
    lhz 12, 0x15E(3)
    lwz 9, {STATES}(2)
    li 30, 91
region:
    mulli 11, 30, {STATE}
    add 11, 11, 9
    addi 11, 11, 0x88
    li 31, 0
slot:
    lhz 0, 0(11)
    cmpw 7, 0, 12
    beq 7, seeded
    addi 11, 11, 2
    addi 31, 31, 1
    cmpwi 7, 31, 16
    blt 7, slot
    addi 30, 30, 1
    cmpwi 7, 30, 95
    blt 7, region
    b none
seeded:
    subfic 31, 31, 16
    lwz 11, {LINKS}(2)
    li 10, 21
row:
    lwz 0, 4(11)
    cmpw 7, 0, 30
    bne 7, rownext
    lwz 0, 8(11)
    cmpw 7, 0, 31
    bne 7, rownext
    lwz 3, 0(11)
    cmpwi 7, 3, 90
    beq 7, found
    cmplwi 7, 3, 2
    blt 7, rownext
    cmplwi 7, 3, 4
    bgt 7, rownext
    lwz 8, {STATES}(2)
    mulli 12, 3, {STATE}
    add 8, 8, 12
    lwz 12, 0(8)
    cmpwi 7, 12, 3
    bne 7, rownext
    lhz 12, 0xA8(8)
    cmpwi 7, 12, 2
    beq 7, found
rownext:
    addi 11, 11, 12
    addi 10, 10, -1
    cmpwi 7, 10, 0
    bne 7, row
none:
    li 3, 0
    b out
found:
    li 4, 0
    bla {GET_TEAM}
out:
    ld 30, 0x70(1)
    ld 31, 0x78(1)
    addi 1, 1, 0x80
done:
"""
FEATURED_HOOK = 0x5E92A8   # ld r0,0x80(r1) right after the featured team lookup (bl 0x564D28) in 0x5E928C
SEG_TEAM1 = 0x5E9184
# Selection Show play-in teams (speech variables 0x7E/0x7F and their widgets): stock always uses
# event 90 (li r3,0x5A at 0x5E925C / 0x5E9274, then li r4,0 and the team1/team2 getter). This picks
# the First Four event feeding the current segment game's opposing slot (team 1 via 0x5E9184, its
# regional slot j, link row slot 16 - j). Outside a bracket game it stays 90 (stock); for a bracket
# game with no First Four game feeding it, it returns no team (r3 = 0, straight back to the caller),
# so the director skips play-in lines there. Replaces the li r3,0x5A.
PLAYIN_PAIR = """
    mflr 0
    stdu 1, -0x80(1)
    std 0, 0x90(1)
    std 30, 0x70(1)
    std 31, 0x78(1)
    li 31, 90
    bla {SEG_TEAM1}
    cmpdi 7, 3, 0
    beq 7, out
    li 31, 0
    lhz 12, 0x15E(3)
    lwz 9, {STATES}(2)
    li 30, 91
region:
    mulli 11, 30, {STATE}
    add 11, 11, 9
    addi 11, 11, 0x88
    li 10, 0
slot:
    lhz 0, 0(11)
    cmpw 7, 0, 12
    beq 7, seeded
    addi 11, 11, 2
    addi 10, 10, 1
    cmpwi 7, 10, 16
    blt 7, slot
    addi 30, 30, 1
    cmpwi 7, 30, 95
    blt 7, region
    b out
seeded:
    subfic 10, 10, 16
    lwz 11, {LINKS}(2)
    li 7, 21
row:
    lwz 0, 4(11)
    cmpw 7, 0, 30
    bne 7, rownext
    lwz 0, 8(11)
    cmpw 7, 0, 10
    bne 7, rownext
    lwz 3, 0(11)
    cmpwi 7, 3, 90
    beq 7, found
    cmplwi 7, 3, 2
    blt 7, rownext
    cmplwi 7, 3, 4
    bgt 7, rownext
    lwz 8, {STATES}(2)
    mulli 12, 3, {STATE}
    add 8, 8, 12
    lwz 12, 0(8)
    cmpwi 7, 12, 3
    bne 7, rownext
    lhz 12, 0xA8(8)
    cmpwi 7, 12, 2
    beq 7, found
rownext:
    addi 11, 11, 12
    addi 7, 7, -1
    cmpwi 7, 7, 0
    bne 7, row
    b out
found:
    mr 31, 3
out:
    mr 3, 31
    ld 0, 0x90(1)
    mtlr 0
    ld 30, 0x70(1)
    ld 31, 0x78(1)
    addi 1, 1, 0x80
    cmpwi 7, 3, 0
    bne 7, keep
    blr
keep:
"""
PLAYIN_PAIR_HOOKS = (0x5E925C, 0x5E9274)   # li r3,0x5A
# r31 = 1 when the current segment game (team 1 via 0x5E9184) has a First Four game feeding its
# opposing slot, else 0 (same lookup as PLAYIN_PAIR). Needs the main TOC in r2; ends at 'decide'.
FEED_LOOKUP = """
    li 31, 0
    bla {SEG_TEAM1}
    cmpdi 7, 3, 0
    beq 7, decide
    lhz 12, 0x15E(3)
    lwz 9, {STATES}(2)
    li 30, 91
region:
    mulli 11, 30, {STATE}
    add 11, 11, 9
    addi 11, 11, 0x88
    li 10, 0
slot:
    lhz 0, 0(11)
    cmpw 7, 0, 12
    beq 7, seeded
    addi 11, 11, 2
    addi 10, 10, 1
    cmpwi 7, 10, 16
    blt 7, slot
    addi 30, 30, 1
    cmpwi 7, 30, 95
    blt 7, region
    b decide
seeded:
    subfic 10, 10, 16
    lwz 11, {LINKS}(2)
    li 7, 21
row:
    lwz 0, 4(11)
    cmpw 7, 0, 30
    bne 7, rownext
    lwz 0, 8(11)
    cmpw 7, 0, 10
    bne 7, rownext
    lwz 3, 0(11)
    cmpwi 7, 3, 90
    beq 7, found
    cmplwi 7, 3, 2
    blt 7, rownext
    cmplwi 7, 3, 4
    bgt 7, rownext
    lwz 8, {STATES}(2)
    mulli 12, 3, {STATE}
    add 8, 8, 12
    lwz 12, 0(8)
    cmpwi 7, 12, 3
    bne 7, rownext
    lhz 12, 0xA8(8)
    cmpwi 7, 12, 2
    beq 7, found
rownext:
    addi 11, 11, 12
    addi 7, 7, -1
    cmpwi 7, 7, 0
    bne 7, row
    b decide
found:
    li 31, 1
"""
# Selection Show commentary, which line the director may start (canPlay 0x59D30, r4 = node header,
# body at +0xC). Nodes have a repeat setting at +2; the show's are 0 = once, so the play-in line
# (team 2 lines 1-3, body 09 EF7E 29 007E ...) is spent on East, the first fed matchup, and every
# later region gets the seed lines. Group A (the first-round matchup group) is identified by that
# node's body, with its other members at fixed offsets from it:
#   play-in team A  09 EF7E 29   +0       allow
#   play-in team B  29 007F 00   -0x18    allow (anchor = node + 0x18)
#   seed line 3 >30 1B EF88 00   +0x24    block
#   seed line 3     09 EF88 09   +0x38    block
#   seed lines 1-2  09 EF86 29   +0x4C    block
#   seed line 1     54 007D 09   +0x70    block
# For a matchup with a First Four game feeding its slot (same lookup as PLAYIN_PAIR) the play-in
# nodes may play again and the seed nodes may not; for any other matchup the play-in nodes are
# refused and the seed nodes run the stock check. Everything else runs the stock check. The
# director runs on its own TOC, so the main TOC is loaded for the lookup and restored.
NODE_GATE = """
    lwz 0, 0xC(4)
    lis 12, 0x09EF
    ori 12, 12, 0x7E29
    li 10, 1
    li 9, 0
    cmpw 7, 0, 12
    beq 7, member
    lis 11, 0x2900
    ori 11, 11, 0x7F00
    li 9, -0x18
    cmpw 7, 0, 11
    beq 7, member
    li 10, 0
    lis 11, 0x1BEF
    ori 11, 11, 0x8800
    li 9, 0x24
    cmpw 7, 0, 11
    beq 7, member
    lis 11, 0x09EF
    ori 11, 11, 0x8809
    li 9, 0x38
    cmpw 7, 0, 11
    beq 7, member
    lis 11, 0x09EF
    ori 11, 11, 0x8629
    li 9, 0x4C
    cmpw 7, 0, 11
    beq 7, member
    lis 11, 0x5400
    ori 11, 11, 0x7D09
    li 9, 0x70
    cmpw 7, 0, 11
    beq 7, member
    b stock
member:
    subf 11, 9, 4
    lwz 0, 0xC(11)
    cmpw 7, 0, 12
    bne 7, stock
    mflr 0
    stdu 1, -0xA0(1)
    std 0, 0xB0(1)
    std 2, 0x80(1)
    std 30, 0x88(1)
    std 31, 0x90(1)
    std 3, 0x78(1)
    std 4, 0x70(1)
    stw 10, 0x98(1)
    lis 2, {TOC_HI}
    ori 2, 2, {TOC_LO}
{FEED}decide:
    mr 12, 31
    lwz 10, 0x98(1)
    ld 3, 0x78(1)
    ld 4, 0x70(1)
    ld 2, 0x80(1)
    ld 30, 0x88(1)
    ld 31, 0x90(1)
    ld 0, 0xB0(1)
    mtlr 0
    addi 1, 1, 0xA0
    cmpwi 7, 10, 0
    beq 7, blocktype
    mr 3, 12
    blr
blocktype:
    cmpwi 7, 12, 0
    beq 7, stock
    li 3, 0
    blr
stock:
"""
NODE_GATE_HOOK = 0x59D30   # stdu r1,-0x90(r1): first instruction of the director's canPlay(node)
MAIN_TOC_ADDR = 0xA64A94
# The director picks a first-round matchup's line group by features of the matchup's team 1, read
# by expressions "game -> team 1 -> fact" (fact 0 = seed at 0x6EF00, fact 1 = region event at
# 0x6EF3F; byte 19 is the only difference). Only group A (the 1-16 group) has the play-in lines,
# and they sit on its region = 91 (East) branch, because East's 16 slot held stock's only play-in
# game. The condition evaluator (0x5BABC, r5 = expression, r6 = float result) returns seed 1.0 and
# region 91.0 for those two expressions when the current matchup has a First Four game feeding its
# slot, so a fed 1-16 or 6-11 matchup takes that branch. Anything else runs the stock evaluator.
SEED_FEATURE_SIG = bytes.fromhex("0b000100230b000200060b000200000b00020000000b0001")
REGION_FEATURE_SIG = bytes.fromhex("0b000100230b000200060b000200000b00020001000b0001")
REGION_FEATURE = """
    lwz 9, 0(5)
    lis 10, 0xb00
    ori 10, 10, 0x100
    cmpw 7, 9, 10
    bne 7, stock
    lwz 9, 4(5)
    lis 10, 0x230b
    ori 10, 10, 0x2
    cmpw 7, 9, 10
    bne 7, stock
    lwz 9, 8(5)
    lis 10, 0x6
    ori 10, 10, 0xb00
    cmpw 7, 9, 10
    bne 7, stock
    lwz 9, 12(5)
    lis 10, 0x200
    ori 10, 10, 0xb
    cmpw 7, 9, 10
    bne 7, stock
    lwz 9, 20(5)
    lis 10, 0xb
    ori 10, 10, 0x1
    cmpw 7, 9, 10
    bne 7, stock
    lbz 9, 24(5)
    cmpwi 7, 9, 0
    bne 7, stock
    lwz 9, 16(5)
    lis 10, 0x2
    lis 11, 0x3F80
    cmpw 7, 9, 10
    beq 7, feature
    ori 10, 10, 1
    lis 11, 0x42B6
    cmpw 7, 9, 10
    bne 7, stock
feature:
    mflr 0
    stdu 1, -0xA0(1)
    std 0, 0xB0(1)
    std 2, 0x80(1)
    std 30, 0x88(1)
    std 31, 0x90(1)
    std 3, 0x78(1)
    std 4, 0x70(1)
    std 5, 0x68(1)
    std 6, 0x60(1)
    stw 11, 0x98(1)
    lis 2, {TOC_HI}
    ori 2, 2, {TOC_LO}
{FEED}decide:
    mr 12, 31
    lwz 11, 0x98(1)
    ld 3, 0x78(1)
    ld 4, 0x70(1)
    ld 5, 0x68(1)
    ld 6, 0x60(1)
    ld 2, 0x80(1)
    ld 30, 0x88(1)
    ld 31, 0x90(1)
    ld 0, 0xB0(1)
    mtlr 0
    addi 1, 1, 0xA0
    cmpwi 7, 12, 0
    beq 7, stock
    stw 11, 0(6)
    li 3, 1
    blr
stock:
"""
REGION_FEATURE_HOOK = 0x5BABC   # stdu r1,-0xe0(r1): first instruction of the condition evaluator
# The candidate tree also leaves out lines that have played (the gate above never sees node 89 again
# after East), so the play-in lines are not stamped as played: 0x59C6C writes the director clock to
# the chosen node's +4. For group A's play-in team A / team B nodes (same body and anchor checks as
# NODE_GATE) it returns without stamping; the gate still decides where they may play.
STAMP_SKIP = """
    lwz 0, 0xC(4)
    lis 12, 0x09EF
    ori 12, 12, 0x7E29
    mr 11, 4
    cmpw 7, 0, 12
    beq 7, member
    lis 11, 0x2900
    ori 11, 11, 0x7F00
    cmpw 7, 0, 11
    bne 7, stock
    addi 11, 4, 0x18
member:
    lwz 0, 0xC(11)
    cmpw 7, 0, 12
    bne 7, stock
    blr
stock:
"""
STAMP_SKIP_HOOK = 0x59C6C   # stdu r1,-0x90(r1): first instruction of the played-time stamp
STR_FROM, STR_FREE, FORMAT, STR_T = 0x49E1B4, 0x49F3A4, 0x49E0E4, -0x28A4


def fmt(src):
    return src.format(STATES=F.T_STATES, STATE=F.STATE, LINKS=F.T_LINKS, EVENT_OF_GAME=hex(EVENT_OF_GAME),
                      GET_GAME=hex(GET_GAME), IS_GAME_24=hex(IS_GAME_24), SET_VISIBLE=hex(SET_VISIBLE),
                      SET_BOX_GAME=hex(SET_BOX_GAME), SET_CURSOR=hex(SET_CURSOR), SET_CURSOR_SUB=hex(SET_CURSOR_SUB),
                      REDRAW=hex(REDRAW))


def build_seed(hook, base=0x30000000):
    assert F.original(hook) == 0x2F83005A
    return F.assemble(fmt(SEED), base)


def build_label_text(base=0x30000000):
    assert F.original(LABEL_TEXT_HOOK) == 0x807E0000   # lwz r3,0(r30)
    return F.assemble(fmt(LABEL_TEXT), base)


def build_tbd(base=0x30000000):
    assert F.original(TBD_HOOK) == 0x3BA10078   # addi r29,r1,0x78
    return F.assemble(fmt(TBD), base) + F.original(TBD_HOOK).to_bytes(4, 'big')


def build_tbd2(base=0x30000000):
    assert F.original(TBD2_HOOK) == 0x3BA10078   # addi r29,r1,0x78
    return F.assemble(fmt(TBD), base) + F.original(TBD2_HOOK).to_bytes(4, 'big')


def build_playin_box(base=0x30000000):
    assert F.original(PLAYIN_BOX_HOOK) == 0x3860005A
    return F.assemble(fmt(PLAYIN_BOX), base)


def build_nav(hook, base=0x30000000):
    assert F.original(hook) == 0x60000000          # nop after bl eventOf
    return F.assemble(fmt(NAV), base)


def build_cursor(base=0x30000000):
    assert F.original(CURSOR_HOOK) == 0x41DE0034   # beq- cr7, 0x65A298
    return F.assemble(fmt(CURSOR), base)


def build_show_region(base=0x30000000):
    assert F.original(SHOW_REGION_HOOK) == 0xF821FF71   # stdu r1,-0x90(r1)
    return F.assemble(fmt(SHOW_REGION), base) + F.original(SHOW_REGION_HOOK).to_bytes(4, 'big')


def build_show_seed(base=0x30000000):
    assert F.original(SHOW_SEED_HOOK) == 0xF821FF71   # stdu r1,-0x90(r1)
    return F.assemble(fmt(SHOW_SEED), base) + F.original(SHOW_SEED_HOOK).to_bytes(4, 'big')


def build_show_pair(hook, base=0x30000000):
    assert F.original(hook) == 0x3860005A
    return F.assemble(fmt(SHOW_PAIR), base)


def build_pair_store(hook, base=0x30000000):
    want = {0x5EC438: 0x90610174, 0x5EC44C: 0x90610178}[hook]
    assert F.original(hook) == want
    return F.assemble(PAIR_STORE_A if hook == 0x5EC438 else PAIR_STORE_B, base)


def build_playin_names(base=0x30000000):
    assert F.original(PLAYIN_NAMES_HOOK) == 0x3BA100FC   # addi r29,r1,0xFC
    src = PLAYIN_NAMES.format(STATES=F.T_STATES, STATE=F.STATE, LINKS=F.T_LINKS, TEAM_OF=hex(TEAM_OF),
                              GET_TEAM=hex(GET_TEAM), STR_FROM=hex(STR_FROM), STR_FREE=hex(STR_FREE),
                              FORMAT=hex(FORMAT), STR_T=STR_T)
    return F.assemble(src, base) + F.original(PLAYIN_NAMES_HOOK).to_bytes(4, 'big')


def build_featured(base=0x30000000):
    assert F.original(FEATURED_HOOK) == 0xE8010080   # ld r0,0x80(r1)
    src = FEATURED.format(STATES=F.T_STATES, STATE=F.STATE, LINKS=F.T_LINKS, SEG_TEAM1=hex(SEG_TEAM1), GET_TEAM=hex(GET_TEAM))
    return F.assemble(src, base) + F.original(FEATURED_HOOK).to_bytes(4, 'big')


def build_playin_pair(hook, base=0x30000000):
    assert F.original(hook) == 0x3860005A
    src = PLAYIN_PAIR.format(STATES=F.T_STATES, STATE=F.STATE, LINKS=F.T_LINKS, SEG_TEAM1=hex(SEG_TEAM1))
    return F.assemble(src, base)


def build_node_gate(base=0x30000000):
    assert F.original(NODE_GATE_HOOK) == 0xF821FF71   # stdu r1,-0x90(r1)
    src = NODE_GATE.replace('{FEED}', FEED_LOOKUP).format(STATES=F.T_STATES, STATE=F.STATE, LINKS=F.T_LINKS, SEG_TEAM1=hex(SEG_TEAM1),
                           TOC_HI=hex(MAIN_TOC_ADDR >> 16), TOC_LO=hex(MAIN_TOC_ADDR & 0xFFFF))
    return F.assemble(src, base) + F.original(NODE_GATE_HOOK).to_bytes(4, 'big')


def build_stamp_skip(base=0x30000000):
    assert F.original(STAMP_SKIP_HOOK) == 0xF821FF71   # stdu r1,-0x90(r1)
    return F.assemble(STAMP_SKIP, base) + F.original(STAMP_SKIP_HOOK).to_bytes(4, 'big')


def build_region_feature(base=0x30000000):
    assert F.original(REGION_FEATURE_HOOK) == 0xF821FF21   # stdu r1,-0xe0(r1)
    src = REGION_FEATURE.replace('{FEED}', FEED_LOOKUP).format(STATES=F.T_STATES, STATE=F.STATE, LINKS=F.T_LINKS,
                                                               SEG_TEAM1=hex(SEG_TEAM1), TOC_HI=hex(MAIN_TOC_ADDR >> 16),
                                                               TOC_LO=hex(MAIN_TOC_ADDR & 0xFFFF))
    return F.assemble(src, base) + F.original(REGION_FEATURE_HOOK).to_bytes(4, 'big')


def build_label_style(base=0x30000000):
    assert F.original(LABEL_STYLE_HOOK) == 0x7F03C378   # mr r3,r24
    return F.assemble(fmt(LABEL_STYLE), base)


def blocks():
    out = [(PLAYIN_BOX_HOOK, build_playin_box(), 'play-in box shows the open First Four page game'),
           (CURSOR_HOOK, build_cursor(), 'cursor to the play-in box on a new First Four page')]
    out += [(h, build_nav(h), 'LT/RT step from the First Four page') for h in NAV_HOOKS]
    out.append((SHOW_REGION_HOOK, build_show_region(), 'Selection Show: First Four teams get their region'))
    out += [(h, build_show_pair(h), 'Selection Show: play-in pair of each region') for h in SHOW_PAIR_HOOKS]
    out += [(h, build_pair_store(h), 'Selection Show: 11-seed play-in team fills its slot') for h in PAIR_STORE_HOOKS]
    out.append((SHOW_SEED_HOOK, build_show_seed(), 'presentation seed for First Four teams'))
    out.append((PLAYIN_NAMES_HOOK, build_playin_names(), 'Selection Show: name the play-in matchup'))
    out.append((FEATURED_HOOK, build_featured(), 'Selection Show commentary: no empty featured team'))
    out += [(h, build_playin_pair(h), 'Selection Show: play-in teams of the current region') for h in PLAYIN_PAIR_HOOKS]
    out.append((NODE_GATE_HOOK, build_node_gate(), 'Selection Show commentary: play-in line for every fed matchup'))
    out.append((STAMP_SKIP_HOOK, build_stamp_skip(), 'Selection Show commentary: play-in lines never spent'))
    out.append((REGION_FEATURE_HOOK, build_region_feature(), 'Selection Show commentary: fed 1-16 and 6-11 matchups take the play-in branch'))
    out += [(h, build_seed(h), 'no seeds on First Four pages') for h in SEED_HOOKS]
    out.append((LABEL_TEXT_HOOK, build_label_text(), 'PLAY-IN GAME WINNER text in every fed regional slot'))
    out.append((TBD_HOOK, build_tbd(), 'PLAY-IN GAME WINNER on the blank-team path'))
    out.append((TBD2_HOOK, build_tbd2(), 'PLAY-IN GAME WINNER instead of TBD (Legacy path)'))
    out.append((LABEL_STYLE_HOOK, build_label_style(), 'PLAY-IN GAME WINNER box style in every fed regional slot'))
    return out


if __name__ == '__main__':
    for h, code, what in blocks():
        print(f'{h:#x} {len(code) // 4:4d} words  {what}')
