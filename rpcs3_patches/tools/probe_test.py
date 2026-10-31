"""Run a TTY probe in the interpreter: message text, register/LR/CR preservation."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import probe_asm as P
from rank_interp import CPU, Mem, STACK

BASE = 0x31000000
NUL2 = bytes(2)
NL = chr(10)


def run(tag, addr, lr, text=None, index=None):
    m = Mem(); code = P.build(tag, addr, BASE, text=text is not None, index=index is not None); m.write(BASE, code)
    if text is not None:
        m.write(0x40000000, text.encode('utf-16-be') + NUL2)
    cpu = CPU(m, None); out = []
    def sc(pc):
        r = cpu.r
        if r[11] != 403 or r[3] != 0: raise RuntimeError('bad syscall regs')
        out.append(m.read(r[4], r[5]).decode()); m.w(r[6], 4, r[5]); r[3] = 0
        for v in (0, 4, 5, 6, 7, 8, 9, 10, 11, 12): r[v] = 0xBAD
        return pc + 4
    cpu.syscall = sc
    for n in range(32): cpu.r[n] = 0x1000 + n
    if text is not None: cpu.r[4] = 0x40000000
    if index is not None: cpu.r[3] = index
    cpu.r[1] = STACK; cpu.lr = lr; cpu.cr = [2, 4, 8, 0, 2, 4, 8, 1]
    before = (list(cpu.r), cpu.lr, list(cpu.cr))
    pc, end = BASE, BASE + len(code) - 4          # stop before the copied first instruction
    while pc != end: pc = cpu.step(pc)
    errs = [f'r{n}' for n in range(32) if cpu.r[n] != before[0][n]]
    if cpu.lr != before[1]: errs.append('lr')
    if cpu.cr != before[2]: errs.append('cr')
    return out, errs, int.from_bytes(code[-4:], 'big')


if __name__ == '__main__':
    out, errs, first = run('GSHT', 0x738F90, 0x0070FD80)
    print(out, errs or 'all preserved', hex(first))
    ok = out == ['GSHT 0070fd80' + NL] and not errs and first == 0xf821ff71
    for txt, want in (('San Jose St.', 'San Jose St.'), ('A very long school name here', 'A very long scho'),
                      ('Caf' + chr(0xE9), 'Caf?'), ('', '')):
        o, e, _ = run('SFRM', 0x738F90, 0x8D284, txt)
        exp = 'SFRM 0008d284 ' + want + NL
        print(o, e or 'all preserved'); ok &= o == [exp] and not e
    o, e, _ = run('GTEA', 0x1BBB58, 0x1BF3A0, index=0x5F)
    print(o, e or 'all preserved'); ok &= o == ['GTEA 001bf3a0 005f' + NL] and not e
    sys.exit(0 if ok else 1)
