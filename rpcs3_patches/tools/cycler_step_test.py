"""Test next/previous-in-conference caves in the interpreter."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cycler_asm as Q
from rank_interp import CPU, Mem, MAIN_TOC, LIB_TOC, STACK, DATA

CAVE = 0x31000000; RET = 0x50000000; CONF = DATA + 0x10000


def run(direction, team, conf_id, members, passing):
    m = Mem(); code = Q.build_step(direction, CAVE); m.write(CAVE, code)
    m.w(CONF + 0x870, 2, len(members))
    for j, t in enumerate(members): m.w(CONF + 0x6e0 + 4 * j, 4, t)
    cpu = CPU(m, None)
    for k in range(32): cpu.r[k] = 0x3333000000000000 + k
    cpu.r[1], cpu.r[2], cpu.r[3], cpu.r[4], cpu.r[5], cpu.lr = STACK, LIB_TOC, team, conf_id, 0xF17, RET
    keep = {k: cpu.r[k] for k in range(13, 32)}
    err = []; pc = CAVE; end = CAVE + len(code); steps = 0
    while True:
        steps += 1
        if steps > 50000: err.append('runaway'); break
        if pc == end: return 'ORIGINAL', err
        if pc == RET: break
        if pc == Q.GET_CONFERENCE:
            cpu.r[3] = CONF if cpu.r[3] == conf_id and conf_id < 39 else 0
            for v in (0, 4, 5, 9, 10, 11, 12): cpu.r[v] = 0xBAD
            pc = cpu.lr; continue
        if pc == Q.FILTER_STUB:
            if cpu.r[2] != LIB_TOC or cpu.r[4] != 0xF17: err.append('bad filter call')
            m.w(cpu.r[1] + 0x28, 8, cpu.r[2]); cpu.r[2] = MAIN_TOC
            cpu.r[3] = 1 if cpu.r[3] in passing else 0
            for v in (0, 4, 5, 9, 10, 11, 12): cpu.r[v] = 0xBAD
            pc = cpu.lr; continue
        if not CAVE <= pc < end: err.append(f'left cave {pc:#x}'); break
        pc = cpu.step(pc)
    for k, v in keep.items():
        if cpu.r[k] != v: err.append(f'r{k} clobbered')
    if cpu.r[2] != LIB_TOC: err.append('lib TOC not restored')
    return cpu.r[3], err


if __name__ == '__main__':
    A, B, C, D, X = (DATA + 0x100 * k for k in range(1, 6))
    L = [A, B, C, D]; allp = set(L); ok = True
    cases = [('next', B, 7, L, allp, C), ('next wraps', D, 7, L, allp, A), ('next skips filtered', A, 7, L, {A, C, D}, C),
             ('next from outsider', X, 7, L, allp, A), ('next null slot', A, 7, [A, 0, B], {A, B}, B),
             ('prev', C, 7, L, allp, B), ('prev wraps', A, 7, L, allp, D), ('prev skips filtered', D, 7, L, {A, B, D}, B),
             ('prev from outsider', X, 7, L, allp, D), ('none pass -> keep', B, 7, L, set(), B),
             ('unknown conference -> keep', B, 60, L, allp, B)]
    for name, team, cid, mem, passing, want in cases:
        direction = name.split()[0] if name.split()[0] in ('next', 'prev') else 'next'
        got, err = run(direction, team, cid, mem, passing)
        good = got == want and not err; ok &= good
        print(f"{'PASS' if good else 'FAIL'} {name:26s} -> {got:#x}", err or '')
    for d in ('next', 'prev'):
        got, err = run(d, A, 0x20, L, allp); good = got == 'ORIGINAL' and not err; ok &= good
        print(f"{'PASS' if good else 'FAIL'} {d} conference 32 -> original", err or '')
    sys.exit(0 if ok else 1)
