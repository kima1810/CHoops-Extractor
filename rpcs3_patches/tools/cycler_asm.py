"""Quick Game team cycling in conference member-list order (RPCS3 calloc cave).

Library nthTeamInConference(conf r3, n r4, filter r5) at 0x1BF690 normally scans the
team table by index, so realigned teams appear after the conference's original
schools. For conferences other than 32 (the all-D1 list) the cave walks the
conference's member list (+0x6E0, count +0x870) instead, returning the nth member
that passes the same filter (main 0x5D6D88 via stub 0x13C20). Conference 32 runs the
original code (the block ends with RPCS3's branch back to 0x1BF694).
"""
import rank_hook_asm as H

HOOK = 0x1BF690                    # cmpwi cr7, r3, 0x20
ORIGINAL = 0x2F830020
GET_CONFERENCE, FILTER_STUB = 0x1BD9E0, 0x13C20

SRC = """
    cmpwi 7, 3, 0x20
    beq 7, orig
    mflr 0
    stdu 1, -0xa0(1)
    std 0, 0xb0(1)
    std 31, 0x98(1)
    std 30, 0x90(1)
    std 29, 0x88(1)
    std 28, 0x80(1)
    std 27, 0x78(1)
    std 26, 0x70(1)
    std 25, 0x68(1)
    mr 29, 4
    mr 28, 5
    bla {GETCONF}
    mr. 31, 3
    beq 0, none
    lhz 27, 0x870(31)
    li 30, 0
    li 26, 0
loop:
    cmpw 7, 30, 27
    bge 7, none
    slwi 9, 30, 2
    addi 9, 9, 0x6e0
    lwzx 3, 31, 9
    addi 30, 30, 1
    cmpwi 7, 3, 0
    beq 7, loop
    mr 25, 3
    mr 4, 28
    bla {FILTER}
    ld 2, 0x28(1)
    cmpwi 7, 3, 1
    bne 7, loop
    cmpw 7, 26, 29
    addi 26, 26, 1
    bne 7, loop
    mr 3, 25
    b ret
none:
    li 3, 0
ret:
    ld 25, 0x68(1)
    ld 26, 0x70(1)
    ld 27, 0x78(1)
    ld 28, 0x80(1)
    ld 29, 0x88(1)
    ld 30, 0x90(1)
    ld 31, 0x98(1)
    ld 0, 0xb0(1)
    mtlr 0
    addi 1, 1, 0xa0
    blr
orig:
"""


def build(base=0x30000000):
    return H.assemble(SRC.format(GETCONF=hex(GET_CONFERENCE), FILTER=hex(FILTER_STUB)), base)


if __name__ == '__main__':
    import struct
    E = open(r'D:/RPCS3 2026/dev_hdd0/game/BLUS30078/USRDIR/EBOOT.elf', 'rb').read()
    assert struct.unpack_from('>I', E, HOOK - 0x10000)[0] == ORIGINAL
    code = build(); assert code == build(0x40010000)
    print('words', len(code) // 4)


# next/previous team in conference (team r3, conf r4, filter r5); entries start with
# cmpwi cr7, r4, 0x20 (0x2F840020). Conference 32 runs the original code.
NEXT_HOOK, PREV_HOOK, STEP_ORIGINAL = 0x1BF93C, 0x1BF82C, 0x2F840020

STEP_SRC = """
    cmpwi 7, 4, 0x20
    beq 7, orig
    mflr 0
    stdu 1, -0xa0(1)
    std 0, 0xb0(1)
    std 31, 0x98(1)
    std 30, 0x90(1)
    std 29, 0x88(1)
    std 28, 0x80(1)
    std 27, 0x78(1)
    std 26, 0x70(1)
    std 25, 0x68(1)
    mr 31, 3
    mr 28, 5
    mr 3, 4
    bla {GETCONF}
    mr. 30, 3
    beq 0, keep
    lhz 27, 0x870(30)
    cmpwi 7, 27, 0
    beq 7, keep
    li 29, -1
    li 26, 0
find:
    cmpw 7, 26, 27
    bge 7, located
    slwi 9, 26, 2
    addi 9, 9, 0x6e0
    lwzx 0, 30, 9
    cmplw 7, 0, 31
    beq 7, here
    addi 26, 26, 1
    b find
here:
    mr 29, 26
located:
{START}
    li 26, 1
step:
    cmpw 7, 26, 27
    bgt 7, keep
{INDEX}
    slwi 9, 9, 2
    addi 9, 9, 0x6e0
    lwzx 3, 30, 9
    addi 26, 26, 1
    cmpwi 7, 3, 0
    beq 7, step
    mr 25, 3
    mr 4, 28
    bla {FILTER}
    ld 2, 0x28(1)
    cmpwi 7, 3, 0
    beq 7, step
    mr 3, 25
    b ret
keep:
    mr 3, 31
ret:
    ld 25, 0x68(1)
    ld 26, 0x70(1)
    ld 27, 0x78(1)
    ld 28, 0x80(1)
    ld 29, 0x88(1)
    ld 30, 0x90(1)
    ld 31, 0x98(1)
    ld 0, 0xb0(1)
    mtlr 0
    addi 1, 1, 0xa0
    blr
orig:
"""
NEXT_START = ""                                   # not found: p = -1, first candidate is slot 0
NEXT_INDEX = """
    add 9, 29, 26
    cmpw 7, 9, 27
    blt 7, ok_{n}
    subf 9, 27, 9
ok_{n}:
"""
PREV_START = """
    cmpwi 7, 29, -1
    bne 7, have_p
    mr 29, 27
have_p:
"""                                               # not found: p = count, first candidate is the last slot
PREV_INDEX = """
    subf 9, 26, 29
    cmpwi 7, 9, 0
    bge 7, ok_{n}
    add 9, 9, 27
ok_{n}:
"""


def build_step(direction, base=0x30000000):
    start, index = (NEXT_START, NEXT_INDEX) if direction == 'next' else (PREV_START, PREV_INDEX)
    src = STEP_SRC.format(GETCONF=hex(GET_CONFERENCE), FILTER=hex(FILTER_STUB), START=start, INDEX=index.format(n=0))
    return H.assemble(src, base)
