"""68-team NCAA field with a four-game First Four (RPCS3 calloc caves).

Stock game: 65 teams, one play-in (event 90, the two lowest automatic bids, winner to
East slot 16). These caves make it four play-in games:

  event 90  P2 vs P3 (two lowest autos)      Tuesday    -> East    (91) slot 16 (stock link)
  event 2   P0 vs P1 (next two lowest autos) Tuesday    -> South   (92) slot 16
  event 3   L0 vs E0 (last at-large in, 1st out) Wed.   -> Midwest (93) slot 11
  event 4   E1 vs E2 (2nd and 3rd out)       Wednesday  -> West    (94) slot 11

Events 2-4 are the 2K Sports Classic first-round events, finished by March. The field
array stays at 65 entries; E0-E2 are the best candidates left out of both the field
and the NIT (the NIT fill skips them).

Caves:
  MARK  selection 0x5C1D30 / projection 0x5BFCDC: four lowest autos become play-in (type 2)
  NIT   0x5C2124: NIT fill skips the first three candidates outside field and NIT
  BUILD 0x590084: whole bracket builder replaced (falls back to the stock builder if the
        field does not look as expected)
  REC   record reads 0x58C270, 0x58F234, 0x58F600, 0x58F700, 0x58F8A4: events 2-4 use the
        event 90 record (name, config) while they hold a 2-team NCAA play-in (state type 3)
  APPS  0x5C19E0: NCAA appearance credit from the built events (regional slot = seed,
        play-in teams get the seed of the slot their game feeds)
"""
import struct

import keystone

from rank_asm import BRANCH_BO_BI

EBOOT = r'D:/RPCS3 2026/dev_hdd0/game/BLUS30078/USRDIR/EBOOT.elf'

# game functions (main module)
EVENT_BUILD, EVENT_RESET = 0x58F74C, 0x58B9B8
SELECTION_DATE, NEXT_DAY, WEEKDAY = 0x5A0CEC, 0x4A3044, 0x4A3754
TEAM_ID, YEAR = 0x4A10E4, 0x49F664
REGIONAL_SITE, FINAL_FOUR_SITE = 0x58C968, 0x58C9C8
# main TOC offsets
T_FIELD, T_NIT, T_CANDIDATES = -0x34E0, -0x34DC, -0x33F0
T_RECORDS, T_STATES, T_LINKS, T_PLAYIN_SITE = -0x3C34, -0x3C4C, -0x3C44, -0x3C18
T_LOW_SCORE = -0x3428
STATE, RECORD = 0xAC, 0x88


def original(addr):
    with open(EBOOT, 'rb') as f:
        f.seek(addr - 0x10000)
        return struct.unpack('>I', f.read(4))[0]


def assemble(src, base):
    """Like rank_hook_asm.assemble, plus absolute `ba`."""
    ks = keystone.Ks(keystone.KS_ARCH_PPC, keystone.KS_MODE_PPC64 | keystone.KS_MODE_BIG_ENDIAN)
    lines = [l.split('#')[0].strip() for l in src.strip().splitlines()]
    lines = [l for l in lines if l]
    local, pc = {}, base
    for l in lines:
        if l.endswith(':'):
            assert l[:-1] not in local, l
            local[l[:-1]] = pc
        else:
            pc += 4
    out, pc = b'', base
    for l in lines:
        if l.endswith(':'):
            continue
        mn, _, rest = l.partition(' ')
        args = [a.strip() for a in rest.split(',')] if rest else []
        if mn in ('bla', 'ba'):
            t = int(args[0], 0)
            assert 0 <= t < (1 << 25) and t % 4 == 0
            word = (18 << 26) | t | (3 if mn == 'bla' else 2)
        elif mn in ('b', 'bl') or mn in BRANCH_BO_BI:
            off = local[args[-1]] - pc
            if mn in ('b', 'bl'):
                assert -(1 << 25) <= off < (1 << 25)
                word = (18 << 26) | (off & 0x3FFFFFC) | (mn == 'bl')
            else:
                assert -(1 << 15) <= off < (1 << 15)
                bo, bit = BRANCH_BO_BI[mn]
                field = int(args[0]) if len(args) == 2 else 0
                word = (16 << 26) | (bo << 21) | ((field * 4 + bit) << 16) | (off & 0xFFFC)
        else:
            enc, _ = ks.asm(l, pc)
            assert enc and len(enc) == 4, l
            word = int.from_bytes(bytes(enc), 'big')
        out += word.to_bytes(4, 'big')
        pc += 4
    return out


# ---- MARK: the four lowest automatic bids become play-in teams ---------------------------
MARK = """
    lfs 0, {LOW}(2)
    addi 9, {N}, -4
    cmpwi 7, 9, 0
    bge 7, start
    li 9, 0
start:
    cmpw 7, 9, {N}
    bge 7, done
    lwz 11, {FIELD}(2)
    mulli 0, 9, 12
    add 11, 11, 0
    li 10, 2
mark:
    stfs 0, 8(11)
    stw 10, 4(11)
    addi 11, 11, 12
    addi 9, 9, 1
    cmpw 7, 9, {N}
    blt 7, mark
done:
    cmpwi 7, {CMP}, 0
    ba {RET}
"""
MARK_SITES = {  # hook: (autos-count register, register the stock code compares next, resume)
    0x5C1D30: (25, 27, 0x5C1D80),   # Selection Sunday (0x5C1B44)
    0x5BFCDC: (26, 25, 0x5BFD2C),   # bracket projection screen (0x5BFAE0)
}


def build_mark(hook, base=0x30000000):
    n, cmp, ret = MARK_SITES[hook]
    return assemble(MARK.format(LOW=T_LOW_SCORE, N=n, FIELD=T_FIELD, CMP=cmp, RET=hex(ret)), base)


# ---- NIT: leave the first three candidates outside the field and the NIT for the First Four -
NIT = """
    li 12, 0
    li 11, 0
    lwz 10, {CAND}(2)
cand:
    cmpw 7, 11, 30
    bge 7, counted
    lwz 8, 0(10)
    lwz 9, {FIELD}(2)
    li 7, 65
infield:
    lwz 0, 0(9)
    cmpw 7, 0, 8
    beq 7, nextcand
    addi 9, 9, 12
    addi 7, 7, -1
    cmpwi 7, 7, 0
    bne 7, infield
    lwz 9, {NIT}(2)
    mr 7, 26
innit:
    cmpwi 7, 7, 0
    beq 7, outside
    lwz 0, 0(9)
    cmpw 7, 0, 8
    beq 7, nextcand
    addi 9, 9, 12
    addi 7, 7, -1
    b innit
outside:
    addi 12, 12, 1
nextcand:
    addi 10, 10, 12
    addi 11, 11, 1
    b cand
counted:
    cmpwi 7, 12, 3
    bge 7, insert
    ba 0x5C20FC
insert:
"""
NIT_HOOK = 0x5C2124   # slwi r0,r30,2 (start of "insert candidate r30 into the NIT"); r26 = NIT count


def build_nit(base=0x30000000):
    return assemble(NIT.format(CAND=T_CANDIDATES, FIELD=T_FIELD, NIT=T_NIT), base) + original(NIT_HOOK).to_bytes(4, 'big')


# ---- REC: events 2-4 read the event 90 record while they hold a First Four game --------
REC = """
    stdu 1, -0x60(1)
    std {S0}, 0x30(1)
    std {S1}, 0x38(1)
    std {S2}, 0x40(1)
    mfcr {S0}
    stw {S0}, 0x48(1)
    mr {S2}, {X}
    lwz {B}, {RECORDS}(2)
    cmplwi 7, {S2}, 2
    blt 7, out
    cmplwi 7, {S2}, 4
    bgt 7, out
    lwz {S0}, {STATES}(2)
    mulli {S1}, {S2}, {STATE}
    add {S0}, {S0}, {S1}
    lwz {S1}, 0({S0})
    cmpwi 7, {S1}, 3
    bne 7, out
    lhz {S1}, 0xA8({S0})
    cmpwi 7, {S1}, 2
    bne 7, out
    subfic {S1}, {S2}, 90
    mulli {S1}, {S1}, {RECORD}
    add {B}, {B}, {S1}
out:
{EXTRA}    lwz {S0}, 0x48(1)
    mtcrf 0xff, {S0}
    ld {S0}, 0x30(1)
    ld {S1}, 0x38(1)
    ld {S2}, 0x40(1)
    addi 1, 1, 0x60
{TAIL}"""
REC_SITES = {  # hook (lwz B,-0x3C34(r2)): (index register, base register, second base register, resume)
    0x58C270: (3, 11, None, None),       # record +8 getter
    0x58F234: (30, 11, None, None),      # game finished: record +4 (holiday advance flag)
    0x58F600: (4, 4, None, None),        # event name
    0x58F700: (31, 9, None, None),       # event name (site variant)
    0x58F8A4: (31, 0, 10, 0x58F8AC),     # eventBuild: record +4 and +8 (two loads)
}


def build_rec(hook, base=0x30000000):
    x, b, b2, ret = REC_SITES[hook]
    s = [k for k in range(5, 13) if k not in (x, b, b2)][:3]
    assert original(hook) == (32 << 26) | (b << 21) | (2 << 16) | (T_RECORDS & 0xFFFF), hex(hook)
    if b2 is not None:
        assert original(hook + 4) == (32 << 26) | (b2 << 21) | (2 << 16) | (T_RECORDS & 0xFFFF)
    src = REC.format(S0=s[0], S1=s[1], S2=s[2], X=x, B=b, RECORDS=T_RECORDS, STATES=T_STATES,
                     STATE=STATE, RECORD=RECORD,
                     EXTRA=f'    mr {b2}, {b}\n' if b2 is not None else '',
                     TAIL=f'    ba {ret:#x}\n' if ret else '')
    return assemble(src, base)


# ---- APPS: NCAA appearance credit from the tournament events ---------------------------
APPS = """
    mr 31, 3
    lwz 10, {STATES}(2)
    addi 9, 10, {E91}
    lwz 0, 0(9)
    cmpwi 7, 0, 3
    bne 7, stock
    lhz 0, 0xA8(9)
    cmpwi 7, 0, 16
    bne 7, stock
    bla {TEAM_ID}
    ld 2, 0x28(1)
    clrlwi 3, 3, 16
    lwz 10, {STATES}(2)
    li 8, 91
region:
    mulli 9, 8, {STATE}
    add 9, 9, 10
    addi 9, 9, 0x88
    li 7, 0
slot:
    lhz 0, 0(9)
    cmpw 7, 0, 3
    beq 7, seeded
    addi 9, 9, 2
    addi 7, 7, 1
    cmpwi 7, 7, 16
    blt 7, slot
    addi 8, 8, 1
    cmpwi 7, 8, 95
    blt 7, region
    li 8, 90
playin:
    mulli 9, 8, {STATE}
    add 9, 9, 10
    lwz 0, 0(9)
    cmpwi 7, 0, 3
    bne 7, nextplayin
    lhz 0, 0xA8(9)
    cmpwi 7, 0, 2
    bne 7, nextplayin
    lhz 0, 0x88(9)
    cmpw 7, 0, 3
    beq 7, linked
    lhz 0, 0x8A(9)
    cmpw 7, 0, 3
    beq 7, linked
nextplayin:
    cmpwi 7, 8, 90
    bne 7, step
    li 8, 1
step:
    addi 8, 8, 1
    cmpwi 7, 8, 5
    blt 7, playin
    ba 0x5C1ACC
linked:
    lwz 9, {LINKS}(2)
    li 6, 21
link:
    lwz 0, 0(9)
    cmpw 7, 0, 8
    beq 7, haslink
    addi 9, 9, 12
    addi 6, 6, -1
    cmpwi 7, 6, 0
    bne 7, link
    li 7, 15
    b seeded
haslink:
    lwz 7, 8(9)
    addi 7, 7, -1
seeded:
    slwi 30, 7, 2
    ba 0x5C1A14
stock:
    li 0, 0x41
    ba 0x5C19E4
"""
APPS_HOOK = 0x5C19E0   # li r0,0x41 after team r3 = team(r29); stock code searches the 65-team field


def build_apps(base=0x30000000):
    assert original(APPS_HOOK) == 0x38000041
    return assemble(APPS.format(STATES=T_STATES, E91=91 * STATE, STATE=STATE, TEAM_ID=hex(TEAM_ID),
                                LINKS=T_LINKS), base)


# ---- LINKS: put the 2K Sports Classic rows (0-2: 2/3/4 -> 6, slot 1-3) back -----------------
# The season reset does not restore link rows, so the rows the builder points at the regionals
# would send next season's Classic pod winners into South 16 / Midwest 11 / West 11. Both caves
# rewrite row e-2 to (e, 6, e-1) for events 2-4 that are not NCAA (type 3) events.
LINK_BUILD = """
    cmplwi 7, 31, 2
    blt 7, done
    cmplwi 7, 31, 4
    bgt 7, done
    cmpwi 7, 8, 3
    beq 7, done
    lwz 11, {LINKS}(2)
    addi 12, 31, -2
    mulli 12, 12, 12
    add 11, 11, 12
    stw 31, 0(11)
    li 0, 6
    stw 0, 4(11)
    addi 0, 31, -1
    stw 0, 8(11)
done:
"""
LINK_BUILD_HOOK = 0x58F848    # eventBuild: stw r8,0(r24) (type into state; event r31; r9 live)
LINK_FINISH = """
    cmplwi 7, 28, 2
    blt 7, done
    cmplwi 7, 28, 4
    bgt 7, done
    lwz 9, {STATES}(2)
    mulli 0, 28, {STATE}
    add 9, 9, 0
    lwz 0, 0(9)
    cmpwi 7, 0, 3
    beq 7, done
    lwz 9, {LINKS}(2)
    addi 0, 28, -2
    mulli 0, 0, 12
    add 9, 9, 0
    stw 28, 0(9)
    li 0, 6
    stw 0, 4(9)
    addi 0, 28, -1
    stw 0, 8(9)
done:
"""
LINK_FINISH_HOOK = 0x58F310   # game finished, event r28 done: li r0,0x15 before the link-table scan


def build_link_build(base=0x30000000):
    assert original(LINK_BUILD_HOOK) == 0x91180000
    return assemble(LINK_BUILD.format(LINKS=T_LINKS), base) + original(LINK_BUILD_HOOK).to_bytes(4, 'big')


def build_link_finish(base=0x30000000):
    assert original(LINK_FINISH_HOOK) == 0x38000015
    return assemble(LINK_FINISH.format(LINKS=T_LINKS, STATES=T_STATES, STATE=STATE), base) + original(LINK_FINISH_HOOK).to_bytes(4, 'big')


# ---- BUILD: bracket builder with four play-in games ------------------------------------
# frame: 0x70 ids[16] (u16) | 0x90 regions[4][16] | 0x190 pos[64] | 0x290 P[4], 0x2A0 E[3], 0x2AC L0
#        0x2B0.. r20-r31 | LR at 0x330 (caller frame)
SAVED = range(20, 32)


def _save(op):
    return ''.join(f'    {op} {r}, {0x2B0 + 8 * (r - 20):#x}(1)\n' for r in SAVED)


def _ids(a, b):   # ids[0..1] = team ids of two teams at r1-relative slots
    return f"""
    lwz 3, {a:#x}(1)
    bla {TEAM_ID:#x}
    ld 2, 0x28(1)
    sth 3, 0x70(1)
    lwz 3, {b:#x}(1)
    bla {TEAM_ID:#x}
    ld 2, 0x28(1)
    sth 3, 0x72(1)
"""


def _playin(event, a, b, date, link, dst, slot):
    s = ''
    if event != 90:
        s += f"""
    li 3, {event}
    bla {EVENT_RESET:#x}
    lwz 9, {T_LINKS}(2)
    li 0, {event}
    stw 0, {12 * link}(9)
    li 0, {dst}
    stw 0, {12 * link + 4}(9)
    li 0, {slot}
    stw 0, {12 * link + 8}(9)
"""
    s += _ids(a, b) + f"""
    li 3, {event}
    li 4, 2
    addi 5, 1, 0x70
    lwz 6, {T_PLAYIN_SITE}(2)
    mr 7, {date}
    li 8, 3
    bla {EVENT_BUILD:#x}
"""
    return s


HOLES = (42, 43, 62, 63)   # bracket positions filled by play-in winners (two 11 seeds, two 16 seeds)
P, E, L0 = 0x290, 0x2A0, 0x2AC

# The at-large type is read from the best candidate's field entry (the real selection 0x5C1B44 stores
# autos as 0 and at-large as 1; the projection screen differs), so L0 is the last at-large in.
BUILD = ("""
    stdu 1, -0x320(1)
    mflr 0
    std 0, 0x330(1)
""" + _save('std') + f"""
    lwz 31, {T_FIELD}(2)
    lwz 10, {T_CANDIDATES}(2)
    lwz 8, 0(10)
    mr 10, 31
    li 9, 65
attype:
    lwz 0, 0(10)
    cmpw 7, 0, 8
    beq 7, atfound
    addi 10, 10, 12
    addi 9, 9, -1
    cmpwi 7, 9, 0
    bne 7, attype
    b fallback
atfound:
    lwz 7, 4(10)
    cmpwi 7, 7, 2
    beq 7, fallback
    li 22, -1
    li 9, 0
    mr 10, 31
lastat:
    lwz 0, 4(10)
    cmpw 7, 0, 7
    bne 7, lastnext
    mr 22, 9
lastnext:
    addi 10, 10, 12
    addi 9, 9, 1
    cmpwi 7, 9, 65
    blt 7, lastat
    cmpwi 7, 22, 0
    blt 7, fallback
    li 9, 0
    li 21, 0
    li 20, 0
    li 27, 0
    mr 10, 31
entry:
    lwz 11, 0(10)
    cmpwi 7, 11, 0
    beq 7, fallback
    lwz 0, 4(10)
    cmpwi 7, 0, 2
    bne 7, normal
    cmpwi 7, 21, 4
    bge 7, fallback
    slwi 0, 21, 2
    add 12, 1, 0
    stw 11, {P}(12)
    addi 21, 21, 1
    b entrynext
normal:
    cmpw 7, 9, 22
    bne 7, direct
    stw 11, {L0}(1)
    b entrynext
direct:
    cmpwi 7, 20, {HOLES[0]}
    beq 7, hole
    cmpwi 7, 20, {HOLES[1]}
    beq 7, hole
    cmpwi 7, 20, {HOLES[2]}
    beq 7, hole
    cmpwi 7, 20, {HOLES[3]}
    beq 7, hole
    cmpwi 7, 20, 64
    bge 7, fallback
    slwi 0, 20, 2
    add 12, 1, 0
    stw 11, 0x190(12)
    addi 20, 20, 1
    addi 27, 27, 1
    b entrynext
hole:
    slwi 0, 20, 2
    add 12, 1, 0
    li 8, 0
    stw 8, 0x190(12)
    addi 20, 20, 1
    b direct
entrynext:
    addi 10, 10, 12
    addi 9, 9, 1
    cmpwi 7, 9, 65
    blt 7, entry
    cmpwi 7, 21, 4
    bne 7, fallback
    cmpwi 7, 27, 60
    bne 7, fallback
    li 8, 0
    stw 8, {0x190 + 4 * 62:#x}(1)
    stw 8, {0x190 + 4 * 63:#x}(1)
    li 21, 0
    li 9, 0
    lwz 10, {T_CANDIDATES}(2)
extra:
    cmpwi 7, 9, 66
    bge 7, fallback
    lwz 11, 0(10)
    cmpwi 7, 11, 0
    beq 7, fallback
    mr 12, 31
    li 7, 65
exfield:
    lwz 0, 0(12)
    cmpw 7, 0, 11
    beq 7, extranext
    addi 12, 12, 12
    addi 7, 7, -1
    cmpwi 7, 7, 0
    bne 7, exfield
    lwz 12, {T_NIT}(2)
    li 7, 32
exnit:
    lwz 0, 0(12)
    cmpw 7, 0, 11
    beq 7, extranext
    addi 12, 12, 12
    addi 7, 7, -1
    cmpwi 7, 7, 0
    bne 7, exnit
    slwi 0, 21, 2
    add 12, 1, 0
    stw 11, {E}(12)
    addi 21, 21, 1
    cmpwi 7, 21, 3
    bge 7, extrasdone
extranext:
    addi 10, 10, 12
    addi 9, 9, 1
    b extra
extrasdone:
    li 27, 0
seedline:
    li 9, 0
region:
    slwi 0, 27, 3
    add 10, 0, 9
    subfic 11, 9, 7
    add 11, 11, 0
    slwi 10, 10, 2
    add 10, 10, 1
    lwz 10, 0x190(10)
    slwi 11, 11, 2
    add 11, 11, 1
    lwz 11, 0x190(11)
    slwi 12, 9, 6
    add 12, 12, 1
    add 12, 12, 0
    stw 10, 0x90(12)
    stw 11, 0x94(12)
    addi 9, 9, 1
    cmpwi 7, 9, 4
    blt 7, region
    addi 27, 27, 1
    cmpwi 7, 27, 8
    blt 7, seedline
    bla {SELECTION_DATE:#x}
    mr 30, 3
tuesday:
    mr 3, 30
    bla {WEEKDAY:#x}
    ld 2, 0x28(1)
    cmpwi 7, 3, 2
    beq 7, gottuesday
    mr 3, 30
    bla {NEXT_DAY:#x}
    ld 2, 0x28(1)
    mr 30, 3
    b tuesday
gottuesday:
    mr 3, 30
    bla {NEXT_DAY:#x}
    ld 2, 0x28(1)
    mr 29, 3
"""
    + _playin(90, P + 8, P + 12, 30, None, None, None)
    + _playin(2, P + 0, P + 4, 30, 0, 92, 16)
    + _playin(3, L0, E + 0, 29, 1, 93, 11)
    + _playin(4, E + 4, E + 8, 29, 2, 94, 11)
    + f"""
    mr 30, 29
thursday:
    mr 3, 30
    bla {WEEKDAY:#x}
    ld 2, 0x28(1)
    cmpwi 7, 3, 4
    beq 7, gotthursday
    mr 3, 30
    bla {NEXT_DAY:#x}
    ld 2, 0x28(1)
    mr 30, 3
    b thursday
gotthursday:
    bla {YEAR:#x}
    ld 2, 0x28(1)
    addi 3, 3, -0x7D8
    extsw 25, 3
    li 27, 0
regional:
    li 20, 0
regionalid:
    slwi 0, 27, 6
    add 12, 0, 1
    slwi 0, 20, 2
    add 12, 12, 0
    lwz 3, 0x90(12)
    bla {TEAM_ID:#x}
    ld 2, 0x28(1)
    slwi 0, 20, 1
    add 12, 1, 0
    sth 3, 0x70(12)
    addi 20, 20, 1
    cmpwi 7, 20, 16
    blt 7, regionalid
    mr 3, 25
    mr 4, 27
    bla {REGIONAL_SITE:#x}
    mr 6, 3
    addi 3, 27, 91
    li 4, 16
    addi 5, 1, 0x70
    mr 7, 30
    li 8, 3
    bla {EVENT_BUILD:#x}
    addi 27, 27, 1
    cmpwi 7, 27, 4
    blt 7, regional
    bla {SELECTION_DATE:#x}
    mr 31, 3
    li 29, 20
finalday:
    mr 3, 31
    bla {NEXT_DAY:#x}
    ld 2, 0x28(1)
    mr 31, 3
    addi 29, 29, -1
    cmpwi 7, 29, 0
    bne 7, finalday
    li 0, 0x7FFF
    sth 0, 0x70(1)
    sth 0, 0x72(1)
    sth 0, 0x74(1)
    sth 0, 0x76(1)
    mr 3, 25
    bla {FINAL_FOUR_SITE:#x}
    mr 6, 3
    li 3, 95
    li 4, 4
    addi 5, 1, 0x70
    mr 7, 31
    li 8, 3
    bla {EVENT_BUILD:#x}
""" + _save('ld') + """
    ld 0, 0x330(1)
    mtlr 0
    addi 1, 1, 0x320
    blr
fallback:
""" + _save('ld') + """
    ld 0, 0x330(1)
    mtlr 0
    addi 1, 1, 0x320
""")
BUILD_HOOK = 0x590084   # stdu r1,-0x1D0(r1): first instruction of the stock builder


def _hex2(reg, n):
    return f"""
    rlwinm 12, {reg}, 28, 28, 31
    cmpwi 7, 12, 9
    ble 7, hi{n}
    addi 12, 12, 39
hi{n}:
    addi 12, 12, 48
    stb 12, 0(10)
    andi. 12, {reg}, 15
    cmpwi 7, 12, 9
    ble 7, lo{n}
    addi 12, 12, 39
lo{n}:
    addi 12, 12, 48
    stb 12, 1(10)
    li 0, 0x20
    stb 0, 2(10)
    addi 10, 10, 3
"""


# DEBUG report: one TTY.log line 'FF4 <stage> <r21> <r27> <r22> <r9> <65 field types>' (stage EE = success;
# 01-08 = which fallback check failed). r21/r27/r22 = play-in count / direct count / last at-large index
# (r21 = extras found in stage 07/08).
REPORT = """
report:
    stdu 1, -0x100(1)
    mflr 0
    std 0, 0x110(1)
    lis 0, 0x4646
    ori 0, 0, 0x3420
    stw 0, 0x70(1)
    addi 10, 1, 0x74
""" + _hex2(3, 1) + _hex2(21, 2) + _hex2(27, 3) + _hex2(22, 4) + _hex2(9, 5) + f"""
    lwz 9, {T_FIELD}(2)
    li 8, 65
types:
    lwz 12, 4(9)
    andi. 12, 12, 15
    addi 12, 12, 48
    stb 12, 0(10)
    addi 10, 10, 1
    addi 9, 9, 12
    addi 8, 8, -1
    cmpwi 7, 8, 0
    bne 7, types
    li 0, 10
    stb 0, 0(10)
    addi 10, 10, 1
    li 3, 0
    addi 4, 1, 0x70
    subf 5, 4, 10
    addi 6, 1, 0xF0
    li 11, 403
    sc
    ld 0, 0x110(1)
    mtlr 0
    addi 1, 1, 0x100
    blr
"""


def builder_source(debug=False):
    """Stock-shaped builder; debug adds a TTY report at success and at each fallback check."""
    if not debug:
        return BUILD
    lines, stubs, k = [], '', 0
    for l in BUILD.splitlines():
        if l.strip().endswith('fallback') and l.strip() != 'fallback:':
            k += 1
            lines.append(l.replace('fallback', f'fb{k}'))
            stubs += f'fb{k}:\n    li 0, {k}\n    stw 0, 0x8C(1)\n    b fallback\n'
        else:
            lines.append(l)
    src = '\n'.join(lines) + '\n'
    tail = src.rindex('    blr\nfallback:\n')
    head, rest = src[:tail], src[tail + len('    blr\nfallback:\n'):]
    cut = head.rindex('    ld 20, ')
    head = head[:cut] + '    li 3, 0xEE\n    bl report\n' + head[cut:]
    return head + '    blr\n' + REPORT + stubs + 'fallback:\n    lwz 3, 0x8C(1)\n    bl report\n' + rest


def build_builder(base=0x30000000, debug=False):
    # fallback ends with the stock first instruction; the calloc's branch back resumes the stock builder
    return assemble(builder_source(debug), base) + original(BUILD_HOOK).to_bytes(4, 'big')


def blocks(debug=False):
    """(hook address, words, comment) for every cave, in patch-file order."""
    out = [(h, build_mark(h), 'four lowest autos to play-in') for h in MARK_SITES]
    out.append((NIT_HOOK, build_nit(), 'NIT fill leaves three teams for the First Four'))
    out.append((BUILD_HOOK, build_builder(debug=debug), 'bracket builder, four play-in games' + (' (TTY report)' if debug else '')))
    out += [(h, build_rec(h), 'events 2-4 use the play-in record') for h in REC_SITES]
    out.append((APPS_HOOK, build_apps(), 'NCAA appearances from the events'))
    out.append((LINK_BUILD_HOOK, build_link_build(), 'restore Classic link rows when events 2-4 are built as holiday events'))
    out.append((LINK_FINISH_HOOK, build_link_finish(), 'restore Classic link rows before a holiday event 2-4 advances'))
    return out


if __name__ == '__main__':
    for h, code, what in blocks():
        print(f'{h:#x} {len(code) // 4:4d} words  {what}')
