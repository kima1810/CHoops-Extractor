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


def build_label_style(base=0x30000000):
    assert F.original(LABEL_STYLE_HOOK) == 0x7F03C378   # mr r3,r24
    return F.assemble(fmt(LABEL_STYLE), base)


def blocks():
    out = [(PLAYIN_BOX_HOOK, build_playin_box(), 'play-in box shows the open First Four page game'),
           (CURSOR_HOOK, build_cursor(), 'cursor to the play-in box on a new First Four page')]
    out += [(h, build_nav(h), 'LT/RT step from the First Four page') for h in NAV_HOOKS]
    out += [(h, build_seed(h), 'no seeds on First Four pages') for h in SEED_HOOKS]
    out.append((LABEL_TEXT_HOOK, build_label_text(), 'PLAY-IN GAME WINNER text in every fed regional slot'))
    out.append((TBD_HOOK, build_tbd(), 'PLAY-IN GAME WINNER on the blank-team path'))
    out.append((TBD2_HOOK, build_tbd2(), 'PLAY-IN GAME WINNER instead of TBD (Legacy path)'))
    out.append((LABEL_STYLE_HOOK, build_label_style(), 'PLAY-IN GAME WINNER box style in every fed regional slot'))
    return out


if __name__ == '__main__':
    for h, code, what in blocks():
        print(f'{h:#x} {len(code) // 4:4d} words  {what}')
