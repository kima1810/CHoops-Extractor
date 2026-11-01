"""Rank-prefix code caves at the two STR_FROM call sites found with the TTY probe.

Team Select (0x6E3FE4): STR_FROM at 0x6E42D8 makes the short name (team +0,
loaded into r4 just before) into handle r3. A second path (0x6E4724) jumps in
just before this call with some other text, so the cave replaces the call itself
and finds the team by matching r4 against each poll team's short-name pointer;
text that is not a poll team's short name is left alone.
Pregame matchup card (0x70EE00): STR_FROM at 0x70EEEC makes the mascot string
(team +0xC) of the team in r28 into handle r3 (= r29).
  The cave replaces that call and makes it itself.

Either way, if the team is in the media poll (ID match at +0x15E) the handle is
rewritten as "#N <text>"; the main TOC is left in the caller's TOC slot for the
caller's own `ld r2,0x28(r1)`.
"""
import rank_hook_asm as H
from rank_asm import (FMT_PAIR, FMT_RANK, FORMAT, KEY, POLL_ENTRY, STR_ASSIGN, STR_FREE,
                      TOC_INT_TYPE, TOC_STR_TYPE)

STR_FROM = 0x49E1B4
SITES = {
    # name: (hook address, original word, nop address or None, setup lines, match by name pointer)
    'teamselect': (0x6E42D8, 0x4BDB9EDD, None, ['mr 31, 3', 'mr 30, 4'], True),
    'matchup': (0x70EEEC, 0x4BD8F2C9, None, ['mr 31, 3', 'mr 30, 28'], False),
}

SAVE = """
    stdu 1, -0x100(1)
    std 31, 0xF0(1)
    std 30, 0xE8(1)
    std 29, 0xE0(1)
    std 28, 0xD8(1)
    std 27, 0xD0(1)
    std 2, 0xC8(1)
"""
TAIL = """
done:
    ld 2, 0xC8(1)
    ld 27, 0xD0(1)
    ld 28, 0xD8(1)
    ld 29, 0xE0(1)
    ld 30, 0xE8(1)
    ld 31, 0xF0(1)
    addi 1, 1, 0x100
    std 2, 0x28(1)
"""


def build(site, base=0x30000000, debug=False):
    _, _, _, setup, by_ptr = SITES[site]
    body = H.SRC[H.SRC.index('    mr 28, 1'):H.SRC.index('done:')]
    if by_ptr:                      # r30 holds the text pointer; compare with team +0
        body = body.replace('    lhz 27, {KEY}(30)\n', '    mr 27, 30\n').replace('    lhz 0, {KEY}(3)\n', '    lwz 0, 0(3)\n')
        assert 'lhz' not in body
    hi = lambda v: hex((v >> 16) & 0xFFFF)
    lo = lambda v: hex(v & 0xFFFF)
    src = SAVE + ''.join(f'    {l}\n' for l in setup) + f'    bla {hex(STR_FROM)}\n    ld 2, 0x28(1)\n'
    src += body.format(POLL_ENTRY=hex(POLL_ENTRY), KEY=hex(KEY), STR_ASSIGN=hex(STR_ASSIGN),
                       STR_FREE=hex(STR_FREE), FORMAT=hex(FORMAT), INT_T=hex(TOC_INT_TYPE),
                       STR_T=hex(TOC_STR_TYPE), RANK_HI=hi(FMT_RANK), RANK_LO=lo(FMT_RANK),
                       PAIR_HI=hi(FMT_PAIR), PAIR_LO=lo(FMT_PAIR))
    src += TAIL
    return H.assemble(H.debugify(src) if debug else src, base)


if __name__ == '__main__':
    import struct
    E = open(r'D:/RPCS3 2026/dev_hdd0/game/BLUS30078/USRDIR/EBOOT.elf', 'rb').read()
    W = lambda a: struct.unpack_from('>I', E, a - 0x10000)[0]
    for name, (addr, orig, nop, _, _) in SITES.items():
        code = build(name)
        assert code == build(name, 0x40010000)
        assert W(addr) == orig, (name, hex(W(addr)))
        if nop: assert W(nop) == 0x4BDB9EDD, hex(W(nop))  # bl 0x49E1B4
        print(name, 'words', len(code) // 4, 'orig ok', 'nop at', hex(nop) if nop else '-', hex(W(nop)) if nop else '')
