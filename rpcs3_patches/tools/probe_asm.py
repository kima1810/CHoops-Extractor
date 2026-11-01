"""TTY probes: an RPCS3 calloc block at a function's first instruction that prints
'<TAG> <caller return address>' through sys_tty_write (syscall 403) to TTY.log,
then runs the original first instruction and returns to the function.

Every volatile register, LR and CR are preserved, so the probed function behaves
exactly as before. Only used for finding which code a screen runs.
"""
import struct

import keystone

import rank_hook_asm as H

EBOOT = r'D:/RPCS3 2026/dev_hdd0/game/BLUS30078/USRDIR/EBOOT.elf'

SRC = """
    stdu 1, -0x140(1)
    std 0, 0x70(1)
    mflr 0
    std 0, 0x78(1)
    mfcr 0
    stw 0, 0x80(1)
    std 3, 0x88(1)
    std 4, 0x90(1)
    std 5, 0x98(1)
    std 6, 0xA0(1)
    std 7, 0xA8(1)
    std 8, 0xB0(1)
    std 9, 0xB8(1)
    std 10, 0xC0(1)
    std 11, 0xC8(1)
    std 12, 0xD0(1)
    lis 0, {TAG_HI}
    ori 0, 0, {TAG_LO}
    stw 0, 0xE0(1)
    li 0, 0x20
    stb 0, 0xE4(1)
    li 0, 10
    stb 0, 0xED(1)
    ld 8, 0x78(1)
    li 9, 8
    addi 10, 1, 0xEC
hex:
    andi. 12, 8, 15
    addi 12, 12, 48
    cmpwi 7, 12, 57
    ble 7, digit
    addi 12, 12, 39
digit:
    stb 12, 0(10)
    addi 10, 10, -1
    srdi 8, 8, 4
    addi 9, 9, -1
    cmpwi 7, 9, 0
    bne 7, hex
{TEXT}    li 3, 0
    addi 4, 1, 0xE0
    addi 6, 1, 0x130
    li 11, 403
    sc
    lwz 0, 0x80(1)
    mtcrf 0xff, 0
    ld 0, 0x78(1)
    mtlr 0
    ld 0, 0x70(1)
    ld 3, 0x88(1)
    ld 4, 0x90(1)
    ld 5, 0x98(1)
    ld 6, 0xA0(1)
    ld 7, 0xA8(1)
    ld 8, 0xB0(1)
    ld 9, 0xB8(1)
    ld 10, 0xC0(1)
    ld 11, 0xC8(1)
    ld 12, 0xD0(1)
    addi 1, 1, 0x140
"""


# Default tail: just the newline. TEXT_SRC appends up to 16 UTF-16 chars from the
# function's saved r4 (low byte, '?' for non-ASCII); pointers below 0x10000 are skipped.
PLAIN = """
    li 5, 14
"""
TEXT_SRC = """
    li 0, 0x20
    stb 0, 0xED(1)
    addi 10, 1, 0xEE
    li 5, 14
    ld 8, 0x90(1)
    cmplwi 7, 8, 0xffff
    ble 7, fin
    li 9, 16
chars:
    lhz 12, 0(8)
    cmpwi 7, 12, 0
    beq 7, fin
    cmpwi 7, 12, 0x7f
    ble 7, ascii
    li 12, 0x3f
ascii:
    stb 12, 0(10)
    addi 10, 10, 1
    addi 8, 8, 2
    addi 5, 5, 1
    addi 9, 9, -1
    cmpwi 7, 9, 0
    bne 7, chars
fin:
    li 0, 10
    stb 0, 0(10)
    addi 5, 5, 1
"""


# IDX_SRC appends the low 16 bits of the saved r3 (an index argument) as 4 hex digits.
IDX_SRC = """
    li 0, 0x20
    stb 0, 0xED(1)
    ld 8, 0x88(1)
    li 9, 4
    addi 10, 1, 0xF1
idx:
    andi. 12, 8, 15
    addi 12, 12, 48
    cmpwi 7, 12, 57
    ble 7, idxd
    addi 12, 12, 39
idxd:
    stb 12, 0(10)
    addi 10, 10, -1
    srdi 8, 8, 4
    addi 9, 9, -1
    cmpwi 7, 9, 0
    bne 7, idx
    li 0, 10
    stb 0, 0xF2(1)
    li 5, 19
"""


# BT_SRC appends up to 6 more return addresses from the stack back chain (each frame's
# saved LR at 0x10 of its caller's frame); it stops when the chain stops going up the stack.
BT_SRC = """
    addi 7, 1, 0x140
    addi 10, 1, 0xED
    li 11, 6
bt:
    mr 4, 7
    ld 7, 0(7)
    cmpld 7, 7, 4
    ble 7, btend
    subf 0, 4, 7
    cmpldi 7, 0, 0x8000
    bge 7, btend
    ld 8, 0x10(7)
    li 0, 0x20
    stb 0, 0(10)
    addi 10, 10, 8
    li 9, 8
bh:
    andi. 12, 8, 15
    addi 12, 12, 48
    cmpwi 7, 12, 57
    ble 7, bd
    addi 12, 12, 39
bd:
    stb 12, 0(10)
    addi 10, 10, -1
    srdi 8, 8, 4
    addi 9, 9, -1
    cmpwi 7, 9, 0
    bne 7, bh
    addi 10, 10, 9
    addi 11, 11, -1
    cmpwi 7, 11, 0
    bne 7, bt
btend:
    li 0, 10
    stb 0, 0(10)
    subf 5, 1, 10
    addi 5, 5, -0xDF
"""


DUMP_PRE = "    ld 7, 0x88(1)" + chr(10)
# DUMP_SRC appends the first six words at the saved r3 (a record pointer); pointers
# below 0x10000 print nothing.
DUMP_SRC = """
{PRE}    addi 10, 1, 0xED
    cmplwi 7, 7, 0xffff
    ble 7, dend
    li 11, 6
dw:
    lwz 8, 0(7)
    addi 7, 7, 4
    li 0, 0x20
    stb 0, 0(10)
    addi 10, 10, 8
    li 9, 8
dh:
    andi. 12, 8, 15
    addi 12, 12, 48
    cmpwi 7, 12, 57
    ble 7, dd
    addi 12, 12, 39
dd:
    stb 12, 0(10)
    addi 10, 10, -1
    srdi 8, 8, 4
    addi 9, 9, -1
    cmpwi 7, 9, 0
    bne 7, dh
    addi 10, 10, 9
    addi 11, 11, -1
    cmpwi 7, 11, 0
    bne 7, dw
dend:
    li 0, 10
    stb 0, 0(10)
    subf 5, 1, 10
    addi 5, 5, -0xDF
"""


def original(addr):
    with open(EBOOT, 'rb') as f:
        f.seek(addr - 0x10000)
        return struct.unpack('>I', f.read(4))[0]


def build(tag, addr, base=0x30000000, text=False, index=False, bt=False, dump=False, pre=None):
    assert len(tag) == 4 and tag.isascii()
    t = int.from_bytes(tag.encode(), 'big')
    code = H.assemble(SRC.format(TAG_HI=hex(t >> 16), TAG_LO=hex(t & 0xFFFF), TEXT=DUMP_SRC.replace('{PRE}', pre or DUMP_PRE) if dump else BT_SRC if bt else IDX_SRC if index else TEXT_SRC if text else PLAIN), base)
    first = original(addr)
    assert first >> 26 not in (16, 18, 19), f'{addr:#x}: first instruction is a branch'
    return code + first.to_bytes(4, 'big')
