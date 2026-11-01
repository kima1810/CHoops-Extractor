"""Run the cycler cave in the interpreter with a modeled conference and filter."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cycler_asm as Q
from rank_interp import CPU, Mem, MAIN_TOC, LIB_TOC, STACK, DATA

CAVE = 0x31000000; RET = 0x50000000
CONF = DATA + 0x10000


def run(conf_id, n, members, passing, caller_regs=True):
    m = Mem(); code = Q.build(CAVE); m.write(CAVE, code)
    m.w(CONF + 0x870, 2, len(members))
    for j, t in enumerate(members): m.w(CONF + 0x6e0 + 4 * j, 4, t)
    cpu = CPU(m, None)
    for k in range(32): cpu.r[k] = 0x3333000000000000 + k
    cpu.r[1], cpu.r[2], cpu.r[3], cpu.r[4], cpu.r[5], cpu.lr = STACK, LIB_TOC, conf_id, n, 0xF17, RET
    keep = {k: cpu.r[k] for k in range(13, 32)}; keep[1] = STACK
    err = []; pc = CAVE; end = CAVE + len(code); steps = 0
    while True:
        steps += 1
        if steps > 50000: err.append('runaway'); break
        if pc == end: return 'ORIGINAL', err, cpu.cr[7]
        if pc == RET: break
        if pc == Q.GET_CONFERENCE:
            if cpu.r[2] != LIB_TOC: err.append('getConference without lib TOC')
            cpu.r[3] = CONF if cpu.r[3] == conf_id and conf_id < 39 else 0
            for v in (0, 4, 5, 9, 10, 11, 12): cpu.r[v] = 0xBAD
            pc = cpu.lr; continue
        if pc == Q.FILTER_STUB:              # lib->main stub: saves r2, switches TOC
            if cpu.r[2] != LIB_TOC: err.append('filter called without lib TOC')
            if cpu.r[4] != 0xF17: err.append('wrong filter argument')
            m.w(cpu.r[1] + 0x28, 8, cpu.r[2]); cpu.r[2] = MAIN_TOC
            cpu.r[3] = 1 if cpu.r[3] in passing else 0
            for v in (0, 4, 5, 9, 10, 11, 12): cpu.r[v] = 0xBAD
            pc = cpu.lr; continue
        if not CAVE <= pc < end: err.append(f'left cave {pc:#x}'); break
        pc = cpu.step(pc)
    for k, v in keep.items():
        if cpu.r[k] != v: err.append(f'r{k} clobbered')
    if cpu.r[2] != LIB_TOC: err.append('lib TOC not restored')
    return cpu.r[3], err, None


if __name__ == '__main__':
    A, B, C, D, X = DATA + 0x100, DATA + 0x400, DATA + 0x700, DATA + 0xA00, DATA + 0xD00
    members = [A, B, C, D]; ok = True
    cases = [('first', 7, 0, members, {A, B, C, D}, A), ('third', 7, 2, members, {A, B, C, D}, C),
             ('skips filtered', 7, 1, members, {A, C, D}, C), ('past end -> 0', 7, 4, members, {A, B, C, D}, 0),
             ('null slot skipped', 7, 1, [A, 0, B], {A, B}, B), ('unknown conference -> 0', 50, 0, members, {A}, 0)]
    for name, cid, n, mem, passing, want in cases:
        got, err, _ = run(cid, n, mem, passing)
        good = got == want and not err; ok &= good
        print(f"{'PASS' if good else 'FAIL'} {name:24s} -> {got:#x}" if isinstance(got, int) else got, err or '')
    got, err, cr7 = run(0x20, 3, members, {A})
    good = got == 'ORIGINAL' and cr7 == 2 and not err; ok &= good
    print(f"{'PASS' if good else 'FAIL'} conference 32 -> original code, cr7 EQ", err or '')
    sys.exit(0 if ok else 1)
