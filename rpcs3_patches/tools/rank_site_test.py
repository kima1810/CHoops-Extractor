"""Run the call-site caves with modeled game calls (entry registers as at each site)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rank_asm as R
import rank_site_asm as S
from rank_interp import CPU, Mem, MAIN_TOC, LIB_TOC, STACK, HEAP, DATA

CAVE = 0x31000000
T, RT = DATA + 0x100, DATA + 0x4000
INT_T, STR_T = 0xA18CA0, 0xA18CD8


def run(site, poll, team, keys, text, debug=False, other=None):
    m = Mem(); code = S.build(site, CAVE, debug); m.write(CAVE, code)
    m.w(MAIN_TOC + R.TOC_INT_TYPE, 4, INT_T); m.w(MAIN_TOC + R.TOC_STR_TYPE, 4, STR_T)
    for p, k in keys.items(): m.w(p + R.KEY, 2, k)
    name_ptr = DATA + 0x7000
    sp = STACK; handle = sp + 0xB0
    m.w(sp + 0x28, 8, 0xDEAD)
    cpu = CPU(m, None)
    for n in range(32): cpu.r[n] = 0x2222000000000000 + n
    cpu.r[1], cpu.r[2] = sp, MAIN_TOC
    if site == 'teamselect':          # at the call: r3 handle, r4 = team's short-name pointer
        m.w(team, 4, name_ptr); m.w(RT, 4, name_ptr)
        cpu.r[3], cpu.r[4], cpu.r[5], cpu.r[29] = handle, other or name_ptr, (1 << 64) - 1, handle
        if other: name_ptr = other
    else:
        m.w(team + 0xC, 4, name_ptr); cpu.r[3], cpu.r[4], cpu.r[5], cpu.r[28], cpu.r[29] = handle, name_ptr, (1 << 64) - 1, team, handle
    keep = {n: cpu.r[n] for n in range(14, 32)}
    nodes, st = {}, {'next': HEAP, 'err': []}
    def new_node(t): n = st['next']; st['next'] += 0x10; nodes[n] = t; return n
    def stub(name):
        if cpu.r[2] != MAIN_TOC: st['err'].append(f'{name} entered with r2={cpu.r[2]:#x}')
        m.w(cpu.r[1] + 0x28, 8, cpu.r[2]); cpu.r[2] = LIB_TOC
    templates = {R.FMT_RANK: '#{0}', R.FMT_PAIR: '{0} {1}'}
    pc, steps, end = CAVE, 0, CAVE + len(code)
    while pc != end:
        steps += 1
        if steps > 20000: st['err'].append('runaway'); break
        r3, r4 = cpu.r[3] & 0xFFFFFFFF, cpu.r[4] & 0xFFFFFFFF
        if pc == S.STR_FROM:
            stub('STR_FROM')
            if r3 != handle or r4 != name_ptr or cpu.r[5] & 0xFFFFFFFF != 0xFFFFFFFF: st['err'].append('bad STR_FROM args')
            m.w(r3, 4, new_node(text)); pc = cpu.lr; continue
        if pc == R.POLL_ENTRY:
            cpu.r[3] = poll[r4] if r4 < len(poll) else 0
            for v in (0, 4, 5, 6, 7, 8, 9, 10, 11, 12): cpu.r[v] = 0xBAD0 + v
            pc = cpu.lr; continue
        if pc == R.STR_ASSIGN: stub('ASSIGN'); m.w(r3, 4, m.u(r4, 4)); pc = cpu.lr; continue
        if pc == R.FORMAT:
            stub('FORMAT'); hdr = cpu.r[5] & 0xFFFFFFFF; vals = []
            for i in range(m.u(hdr + 4, 4)):
                e = hdr + 8 + 12 * i; ptr, typ = m.u(e + 4, 4), m.u(e + 8, 4)
                vals.append(str(m.u(ptr, 4)) if typ == INT_T else nodes[m.u(ptr, 4)] if typ == STR_T else '?')
            m.w(r3, 4, new_node(templates[m.u(r4, 4)].format(*vals))); pc = cpu.lr; continue
        if pc == R.STR_FREE: stub('FREE'); pc = cpu.lr; continue
        if not CAVE <= pc < end: st['err'].append(f'left the cave to {pc:#x}'); break
        pc = cpu.step(pc)
    for n, v in keep.items():
        if cpu.r[n] != v: st['err'].append(f'r{n} clobbered')
    if cpu.r[1] != sp: st['err'].append('r1 not restored')
    if cpu.r[2] != MAIN_TOC: st['err'].append('main TOC not restored')
    if m.u(sp + 0x28, 8) != MAIN_TOC: st['err'].append('caller TOC slot not main TOC')
    st['out'] = nodes.get(m.u(handle, 4))
    return st


if __name__ == '__main__':
    base = [DATA + 0x800 + 0x200 * i for i in range(25)]
    keys = {T: 216, RT: 216, **{b: 1000 + i for i, b in enumerate(base)}}
    base[3] = 0
    ok = True
    for site, text in (('teamselect', 'Illinois'), ('matchup', 'Fighting Illini')):
        cases = [('ranked #6', base[:5] + [RT] + base[6:], keys, f'#6 {text}'),
                 ('ranked #25', base[:24] + [RT], keys, f'#25 {text}'),
                 ('unranked', base, keys, text),
                 ('ID 0', base[:2] + [DATA + 0x6000] + base[3:], {**keys, T: 0, DATA + 0x6000: 0}, text)]
        for name, poll, k, want in cases:
            st = run(site, poll, T, k, text)
            good = st['out'] == want and not st['err']; ok &= good
            print(f"{'PASS' if good else 'FAIL'} {site:10s} {name:10s} -> {st['out']!r}", st['err'] or '')
    # second path into the Team Select call: unrelated text must pass through untouched
    st = run('teamselect', base[:5] + [RT] + base[6:], T, keys, 'Some label', other=DATA + 0x7800)
    good = st['out'] == 'Some label' and not st['err']; ok &= good
    print(f"{'PASS' if good else 'FAIL'} teamselect other text -> {st['out']!r}", st['err'] or '')
    sys.exit(0 if ok else 1)
