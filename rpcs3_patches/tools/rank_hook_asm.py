"""Code-cave hook (RPCS3 `calloc`) that prefixes a team's media-poll rank.

RPCS3 replaces the instruction at the hook address with a branch into a new
code block, runs these instructions, then branches back to hook+4. The block's
address is unknown in advance, so external calls use absolute `bla`; internal
branches are relative.

At the hook the original instruction is a call to a lib->main stub that fills a
text handle (r3) for a team (r4) -- e.g. the mascot getter on the pregame
matchup card. The block makes that call itself, then, if the team is ranked,
rewrites the handle as "#N <text>" with the game's formatter and English
templates "#{0}" / "{0} {1}". The caller's library TOC is restored at the end.
"""
import keystone

from rank_asm import (BRANCH_BO_BI, FMT_PAIR, FMT_RANK, FORMAT, KEY, POLL_ENTRY,
                      STR_ASSIGN, STR_FREE, TOC_INT_TYPE, TOC_STR_TYPE)

SRC = """
    stdu 1, -0x100(1)
    std 31, 0xF0(1)
    std 30, 0xE8(1)
    std 29, 0xE0(1)
    std 28, 0xD8(1)
    std 27, 0xD0(1)
    std 2, 0xC8(1)
    mr 31, 3
    mr 30, 4
    bla {ORIG}
    mr 28, 1
    lhz 27, {KEY}(30)
    cmpwi 7, 27, 0
    beq 7, done
    li 29, 0
loop:
    li 3, 0
    mr 4, 29
    bla {POLL_ENTRY}
    cmpwi 7, 3, 0
    beq 7, next
    lhz 0, {KEY}(3)
    cmpw 7, 0, 27
    beq 7, found
next:
    addi 29, 29, 1
    cmpwi 7, 29, 25
    blt 7, loop
    b done
found:
    li 10, 0
    stw 10, 0x70(28)
    stw 10, 0x78(28)
    stw 10, 0x88(28)
    stw 10, 0x90(28)
    stw 10, 0x9C(28)
    addi 3, 28, 0x78
    mr 4, 31
    li 5, 1
    bla {STR_ASSIGN}
    ld 2, 0x28(1)
    addi 11, 29, 1
    stw 11, 0x84(28)
    lis 0, {RANK_HI}
    ori 0, 0, {RANK_LO}
    stw 0, 0x80(28)
    li 0, 1
    stw 0, 0x8C(28)
    addi 0, 28, 0x84
    stw 0, 0x94(28)
    lwz 0, {INT_T}(2)
    stw 0, 0x98(28)
    addi 3, 28, 0x70
    addi 4, 28, 0x80
    addi 5, 28, 0x88
    li 6, 0
    bla {FORMAT}
    ld 2, 0x28(1)
    lis 0, {PAIR_HI}
    ori 0, 0, {PAIR_LO}
    stw 0, 0x80(28)
    li 0, 2
    stw 0, 0x8C(28)
    addi 0, 28, 0x70
    stw 0, 0x94(28)
    lwz 9, {STR_T}(2)
    stw 9, 0x98(28)
    addi 0, 28, 0x78
    stw 0, 0xA0(28)
    stw 9, 0xA4(28)
    mr 3, 31
    addi 4, 28, 0x80
    addi 5, 28, 0x88
    li 6, 0
    bla {FORMAT}
    ld 2, 0x28(1)
    addi 3, 28, 0x70
    bla {STR_FREE}
    ld 2, 0x28(1)
    addi 3, 28, 0x78
    bla {STR_FREE}
    ld 2, 0x28(1)
done:
    ld 2, 0xC8(1)
    ld 27, 0xD0(1)
    ld 28, 0xD8(1)
    ld 29, 0xE0(1)
    ld 30, 0xE8(1)
    ld 31, 0xF0(1)
    addi 1, 1, 0x100
"""


def assemble(src, base):
    """Relative internal branches, absolute bla for external calls (position independent)."""
    ks = keystone.Ks(keystone.KS_ARCH_PPC, keystone.KS_MODE_PPC64 | keystone.KS_MODE_BIG_ENDIAN)
    lines = [l.strip() for l in src.strip().splitlines() if l.strip()]
    local, pc = {}, base
    for l in lines:
        if l.endswith(':'):
            local[l[:-1]] = pc
        else:
            pc += 4
    out, pc = b'', base
    for l in lines:
        if l.endswith(':'):
            continue
        mn, _, rest = l.partition(' ')
        args = [a.strip() for a in rest.split(',')] if rest else []
        if mn == 'bla':
            t = int(args[0], 0)
            assert 0 <= t < (1 << 25) and t % 4 == 0
            word = (18 << 26) | t | 3
        elif mn == 'b' or mn in BRANCH_BO_BI:
            off = local[args[-1]] - pc
            if mn == 'b':
                word = (18 << 26) | (off & 0x3FFFFFC)
            else:
                bo, bit = BRANCH_BO_BI[mn]
                field = int(args[0]) if len(args) == 2 else 0
                word = (16 << 26) | (bo << 21) | ((field * 4 + bit) << 16) | (off & 0xFFFC)
        else:
            enc, _ = ks.asm(l, pc)
            assert len(enc) == 4, l
            word = int.from_bytes(bytes(enc), 'big')
        out += word.to_bytes(4, 'big')
        pc += 4
    return out


def debugify(src):
    """Diagnostic variant: a team not found in the poll shows 1000 + its team ID."""
    out = src.replace('    cmpwi 7, 27, 0\n    beq 7, done\n', '').replace('    b done\nfound:', '    addi 29, 27, 999\nfound:')
    assert out != src and 'addi 29, 27, 999' in out
    return out


def build(orig_call, base=0x30000000, debug=False):
    hi = lambda v: hex((v >> 16) & 0xFFFF)
    lo = lambda v: hex(v & 0xFFFF)
    src = SRC.format(ORIG=hex(orig_call), POLL_ENTRY=hex(POLL_ENTRY), KEY=hex(KEY),
                     STR_ASSIGN=hex(STR_ASSIGN), STR_FREE=hex(STR_FREE), FORMAT=hex(FORMAT),
                     INT_T=hex(TOC_INT_TYPE), STR_T=hex(TOC_STR_TYPE),
                     RANK_HI=hi(FMT_RANK), RANK_LO=lo(FMT_RANK), PAIR_HI=hi(FMT_PAIR), PAIR_LO=lo(FMT_PAIR))
    return assemble(debugify(src) if debug else src, base)


if __name__ == '__main__':
    code = build(0x118B0)
    print('cave words', len(code) // 4)
    # Position independence: identical bytes at two different bases.
    assert code == build(0x118B0, base=0x40010000), 'not position independent'
    print('position independent: yes')
