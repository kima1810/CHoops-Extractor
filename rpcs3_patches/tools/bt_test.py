"""Backtrace probe check: chain walk, stop rules, register preservation."""
import sys
import probe_asm as P
from rank_interp import CPU, Mem, STACK
BASE = 0x31000000


def run(frames, tail=0):
    m = Mem(); code = P.build('BTPH', 0x491AE4, BASE, bt=True); m.write(BASE, code)
    prev = STACK
    for f, lr in frames:
        m.w(prev, 8, f); m.w(f + 0x10, 8, lr); prev = f
    m.w(prev, 8, tail)
    cpu = CPU(m, None); out = []
    def sc(pc):
        r = cpu.r; out.append(m.read(r[4], r[5]).decode()); m.w(r[6], 4, r[5]); r[3] = 0
        for v in (0, 4, 5, 6, 7, 8, 9, 10, 11, 12): r[v] = 0xBAD
        return pc + 4
    cpu.syscall = sc
    for n in range(32): cpu.r[n] = 0x1000 + n
    cpu.r[1] = STACK; cpu.lr = 0x491B14; cpu.cr = [2, 4, 8, 0, 2, 4, 8, 1]
    before = (list(cpu.r), cpu.lr, list(cpu.cr))
    pc, end = BASE, BASE + len(code) - 4
    while pc != end: pc = cpu.step(pc)
    errs = [f'r{n}' for n in range(32) if cpu.r[n] != before[0][n]]
    if cpu.lr != before[1]: errs.append('lr')
    if cpu.cr != before[2]: errs.append('cr')
    return out, errs


cases = [([(STACK + 0x100, 0x48D76C), (STACK + 0x200, 0x5A0001)], 0, 'BTPH 00491b14 0048d76c 005a0001\n'),
         ([(STACK + 0x100 * (i + 1), 0x400000 + i) for i in range(9)], 0,
          'BTPH 00491b14 ' + ' '.join(f'{0x400000 + i:08x}' for i in range(6)) + '\n'),
         ([], 0, 'BTPH 00491b14\n'),
         ([(STACK + 0x100, 0x111111)], STACK - 0x10, 'BTPH 00491b14 00111111\n'),       # chain goes down: stop
         ([(STACK + 0x100, 0x111111)], STACK + 0x100 + 0x9000, 'BTPH 00491b14 00111111\n')]  # jump too far: stop
ok = True
for fr, tail, want in cases:
    o, e = run(fr, tail); good = o == [want] and not e; ok &= good
    print('ok ' if good else 'BAD', repr(o), e or 'all preserved')
sys.exit(0 if ok else 1)
