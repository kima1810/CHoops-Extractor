"""Replacement scorebug providers that prefix the media-poll rank ("#6 ILL").

Ranked text is produced by the game's own formatter (0x49E0E4 stub), exactly as
native scorebug providers produce text: localized template 0x12BE2A9D "#{0}"
with the rank (int argument), then template 0xDB12E271 "{0} {1}" with that
string and the team name (string arguments) written straight into the slot.
Unranked teams keep the original name-only path (string from name, assign).

Scorebug team objects are per-game copies of the roster team record, so they
are matched to the media poll (0x5BDB44 mode 0, slots 0-24) by the unique team
ID at anchor +0x15E ('team_index_check'); ID 0 is never matched.

Home entry 0x4EF9A4 and away entry 0x4EFABC each have 67 words.
Frame 0x100: handles 0x70 (rank text) / 0x78 (name), format ID 0x80, rank 0x84,
argument block 0x88 (header {0,count} + 12-byte entries {0,&value,type}),
saved r27-r31 at 0xD0-0xF0.
"""
import keystone

HOME, HOME_END = 0x4EF9A4, 0x4EFAB0   # exclusive ends
AWAY, AWAY_END = 0x4EFABC, 0x4EFBC8
GET_HOME, GET_AWAY = 0x57F050, 0x57F064
POLL_ENTRY = 0x5BDB44          # (mode r3, slot r4) -> roster team pointer; mode 0 = media poll
STR_FROM, STR_ASSIGN, STR_FREE, FORMAT = 0x49E1B4, 0x49D604, 0x49F3A4, 0x49E0E4  # main-module stubs
KEY = 0x15E                    # unique team ID in the team record anchor
FMT_RANK, FMT_PAIR = 0x12BE2A9D, 0xDB12E271   # "#{0}", "{0} {1}" in english loc table
TOC_INT_TYPE, TOC_STR_TYPE = -0x6D68, -0x28A4  # argument type descriptors used natively

PROLOGUE = """
    mflr 0
    stdu 1, -0x100(1)
    std 0, 0x110(1)
    std 31, 0xF0(1)
    std 30, 0xE8(1)
    std 29, 0xE0(1)
    std 28, 0xD8(1)
    std 27, 0xD0(1)
    mr. 31, 3
"""

HOME_SRC = PROLOGUE + """
    beq exit
    bl {GET_HOME}
common:
    mr 28, 1
    mr 30, 3
    lhz 27, {KEY}(30)
    cmpwi 7, 27, 0
    beq 7, unranked
    li 29, 0
loop:
    li 3, 0
    mr 4, 29
    bl {POLL_ENTRY}
    cmpwi 7, 3, 0
    beq 7, next
    lhz 0, {KEY}(3)
    cmpw 7, 0, 27
    beq 7, {found}
next:
    addi 29, 29, 1
    cmpwi 7, 29, 25
    blt 7, loop
unranked:
    addi 3, 28, 0x70
    lwz 4, 4(30)
    li 5, -1
    bl {STR_FROM}
    ld 2, 0x28(1)
    mr 3, 31
    addi 4, 28, 0x70
    li 5, 1
    bl {STR_ASSIGN}
    ld 2, 0x28(1)
    addi 3, 28, 0x70
    bl {STR_FREE}
    ld 2, 0x28(1)
exit:
    ld 27, 0xD0(1)
    ld 28, 0xD8(1)
    ld 29, 0xE0(1)
    ld 30, 0xE8(1)
    ld 31, 0xF0(1)
    ld 0, 0x110(1)
    mtlr 0
    addi 1, 1, 0x100
    blr
"""

AWAY_SRC = PROLOGUE + """
    beq {exit}
    bl {GET_AWAY}
    b {common}
found:
    li 10, 0
    stw 10, 0x70(28)
    stw 10, 0x78(28)
    stw 10, 0x88(28)
    stw 10, 0x90(28)
    stw 10, 0x9C(28)
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
    bl {FORMAT}
    ld 2, 0x28(1)
    addi 3, 28, 0x78
    lwz 4, 4(30)
    li 5, -1
    bl {STR_FROM}
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
    bl {FORMAT}
    ld 2, 0x28(1)
    addi 3, 28, 0x70
    bl {STR_FREE}
    ld 2, 0x28(1)
    addi 3, 28, 0x78
    bl {STR_FREE}
    ld 2, 0x28(1)
    b {exit}
"""


def labels(src, addr):
    out, pc = {}, addr
    for line in src.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if line.endswith(':'):
            out[line[:-1]] = pc
        else:
            pc += 4  # fixed-width PowerPC instructions
    return out


BRANCH_BO_BI = {'beq': (12, 2), 'bne': (4, 2), 'blt': (12, 0), 'bge': (4, 0), 'ble': (4, 1), 'bgt': (12, 1)}  # (BO, CR bit in field)


def encode_branch(mn, args, pc, local):
    """Hand-encode b/bl/bcc; Keystone mis-encodes some absolute branch targets."""
    target = local[args[-1]] if args[-1] in local else int(args[-1], 0)
    off = target - pc
    if mn in ('b', 'bl'):
        assert -(1 << 25) <= off < (1 << 25) and off % 4 == 0, (mn, hex(target))
        return (18 << 26) | (off & 0x3FFFFFC) | (1 if mn == 'bl' else 0)
    bo, bit = BRANCH_BO_BI[mn]
    field = int(args[0]) if len(args) == 2 else 0
    assert -(1 << 15) <= off < (1 << 15) and off % 4 == 0, (mn, hex(target))
    return (16 << 26) | (bo << 21) | ((field * 4 + bit) << 16) | (off & 0xFFFC)


def assemble(src, addr):
    ks = keystone.Ks(keystone.KS_ARCH_PPC, keystone.KS_MODE_PPC64 | keystone.KS_MODE_BIG_ENDIAN)
    local = labels(src, addr)
    out, pc = b'', addr
    for line in src.strip().splitlines():
        line = line.strip()
        if not line or line.endswith(':'):
            continue
        mn, _, rest = line.partition(' ')
        args = [a.strip() for a in rest.split(',')] if rest else []
        if mn in ('b', 'bl') or mn in BRANCH_BO_BI:
            out += encode_branch(mn, args, pc, local).to_bytes(4, 'big')
        else:
            enc, _ = ks.asm(line, pc)
            assert len(enc) == 4, line
            out += bytes(enc)
        pc += 4
    return out


def build():
    hi = lambda v: hex((v >> 16) & 0xFFFF)
    lo = lambda v: hex(v & 0xFFFF)
    consts = dict(GET_HOME=hex(GET_HOME), GET_AWAY=hex(GET_AWAY), POLL_ENTRY=hex(POLL_ENTRY),
                  STR_FROM=hex(STR_FROM), STR_ASSIGN=hex(STR_ASSIGN), STR_FREE=hex(STR_FREE),
                  FORMAT=hex(FORMAT), KEY=hex(KEY), INT_T=hex(TOC_INT_TYPE), STR_T=hex(TOC_STR_TYPE),
                  RANK_HI=hi(FMT_RANK), RANK_LO=lo(FMT_RANK), PAIR_HI=hi(FMT_PAIR), PAIR_LO=lo(FMT_PAIR))
    zero = dict(found='0', exit='0', common='0')
    home_lab = labels(HOME_SRC.format(**consts, **zero), HOME)
    away_lab = labels(AWAY_SRC.format(**consts, **zero), AWAY)
    home = assemble(HOME_SRC.format(**consts, found=hex(away_lab['found'])), HOME)
    away = assemble(AWAY_SRC.format(**consts, exit=hex(home_lab['exit']), common=hex(home_lab['common'])), AWAY)
    assert HOME + len(home) <= HOME_END, ('home overflow', hex(HOME + len(home)))
    assert AWAY + len(away) <= AWAY_END, ('away overflow', hex(AWAY + len(away)))
    return home, away, home_lab, away_lab


if __name__ == '__main__':
    home, away, hl, al = build()
    print('home words', len(home) // 4, 'of', (HOME_END - HOME) // 4,
          '| away words', len(away) // 4, 'of', (AWAY_END - AWAY) // 4)
    print('home labels', {k: hex(v) for k, v in hl.items()})
    print('away labels', {k: hex(v) for k, v in al.items()})
