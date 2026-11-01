"""Run the First Four caves in the PPC interpreter against modeled game data and calls."""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import first_four_asm as F
from rank_interp import CPU, Mem, MAIN_TOC, LIB_TOC, STACK, DATA, M64, md, sx

CAVE = 0x31000000
FIELD, NIT, CAND = DATA + 0x10000, DATA + 0x11000, DATA + 0x12000
STATES, LINKS, RECORDS, TEAMS = DATA + 0x20000, DATA + 0x28000, DATA + 0x30000, DATA + 0x100000
SITE = 0x12652A86
MAIN_FUNCS = {F.EVENT_BUILD, F.EVENT_RESET, F.SELECTION_DATE, F.REGIONAL_SITE, F.FINAL_FOUR_SITE}
STUBS = {F.NEXT_DAY, F.WEEKDAY, F.TEAM_ID, F.YEAR}
VOLATILE = (0, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)


class CPU2(CPU):
    def __init__(self, mem):
        super().__init__(mem, None); self.f = [0] * 32

    def step(self, pc):
        ins = next(md.disasm(self.m.read(pc, 4), pc), None)
        if ins is None:
            raise RuntimeError(f'undecodable at {pc:#x}')
        mn, ops = ins.mnemonic, [o.strip() for o in ins.op_str.split(',')] if ins.op_str else []
        R_ = lambda s: int(s.lstrip('rf'))
        r = self.r
        def mem(s):
            m = re.match(r'(-?(?:0x)?[0-9a-f]+)\(r(\d+)\)', s); return (r[int(m.group(2))] + int(m.group(1), 0)) & M64
        if mn == 'mulli': r[R_(ops[0])] = (sx(r[R_(ops[1])], 64) * int(ops[2], 0)) & M64
        elif mn == 'subfic': r[R_(ops[0])] = (int(ops[2], 0) - sx(r[R_(ops[1])], 64)) & M64
        elif mn == 'extsw': r[R_(ops[0])] = sx(r[R_(ops[1])], 32) & M64
        elif mn == 'clrlwi': r[R_(ops[0])] = r[R_(ops[1])] & ((1 << (32 - int(ops[2], 0))) - 1)
        elif mn == 'lfs': self.f[R_(ops[0])] = self.m.u(mem(ops[1]), 4)
        elif mn == 'stfs': self.m.w(mem(ops[1]), 4, self.f[R_(ops[0])])
        elif mn == 'ba': return int(ops[0], 0)
        elif mn == 'cmpdi':
            f = int(ops[0].replace('cr', '')) if len(ops) == 3 else 0
            self.setcr(f, sx(r[R_(ops[-2])], 64), int(ops[-1], 0))
        elif mn == 'rlwinm':
            v, sh, mb, me = r[R_(ops[1])] & 0xFFFFFFFF, int(ops[2], 0), int(ops[3], 0), int(ops[4], 0)
            v = ((v << sh) | (v >> (32 - sh))) & 0xFFFFFFFF if sh else v
            mask = sum(1 << (31 - b) for b in range(mb, me + 1))
            r[R_(ops[0])] = v & mask
        elif mn == 'blt' and len(ops) == 2 and False: pass
        else: return super().step(pc)
        return pc + 4


def team(i): return TEAMS + 0x400 * i
def tid(t): return 0x7FFF if t == 0 else 100 + (t - TEAMS) // 0x400


class World:
    def __init__(self):
        self.m = Mem(); self.calls = []
        for off, v in ((F.T_FIELD, FIELD), (F.T_NIT, NIT), (F.T_CANDIDATES, CAND), (F.T_STATES, STATES),
                       (F.T_LINKS, LINKS), (F.T_RECORDS, RECORDS), (F.T_PLAYIN_SITE, SITE), (F.T_LOW_SCORE, 0xC61C4000)):
            self.m.w(MAIN_TOC + off, 4, v)

    def field(self, entries):
        for i, (t, typ, score) in enumerate(entries):
            self.m.w(FIELD + 12 * i, 4, t); self.m.w(FIELD + 12 * i + 4, 4, typ); self.m.w(FIELD + 12 * i + 8, 4, score)

    def table(self, base, teams):
        for i, t in enumerate(teams): self.m.w(base + 12 * i, 4, t)

    def state(self, e, typ, ids):
        s = STATES + F.STATE * e; self.m.w(s, 4, typ); self.m.w(s + 0xA8, 2, len(ids))
        for j in range(16): self.m.w(s + 0x88 + 2 * j, 2, ids[j] if j < len(ids) else 0x7FFF)

    def links(self, rows):
        for k, row in enumerate(rows):
            for j, v in enumerate(row): self.m.w(LINKS + 12 * k + 4 * j, 4, v)

    def run(self, code, regs=None, stop=(), lr=0x50000000):
        m = self.m; m.write(CAVE, code); cpu = CPU2(m)
        for k in range(32): cpu.r[k] = 0x3333000000000000 + k
        cpu.r[1], cpu.r[2], cpu.lr = STACK, MAIN_TOC, lr
        for k, v in (regs or {}).items(): cpu.r[k] = v
        cpu.cr = [1, 2, 4, 8, 2, 4, 8, 1]
        start = list(cpu.r); err = []; pc = CAVE; end = CAVE + len(code); steps = 0
        while True:
            steps += 1
            if steps > 400000: err.append('runaway'); break
            if pc == end: how = 'END'; break
            if pc in stop or pc == lr: how = pc; break
            if pc in MAIN_FUNCS or pc in STUBS:
                if cpu.r[2] != MAIN_TOC: err.append(f'call {pc:#x} with wrong TOC')
                a = cpu.r[3:9]; res = self.call(pc, a, cpu)
                if pc in STUBS:
                    m.w(cpu.r[1] + 0x28, 8, cpu.r[2]); cpu.r[2] = LIB_TOC
                for v in VOLATILE: cpu.r[v] = 0xBAD0000 + v
                cpu.r[3] = res & M64; pc = cpu.lr; continue
            if not CAVE <= pc < end: err.append(f'left cave at {pc:#x}'); break
            pc = cpu.step(pc)
        return how, cpu, start, err

    def call(self, pc, a, cpu):
        if pc == F.TEAM_ID: return tid(a[0] & 0xFFFFFFFF)
        if pc == F.WEEKDAY: return a[0] % 7
        if pc == F.NEXT_DAY: return a[0] + 1
        if pc == F.SELECTION_DATE: return 98          # a Sunday (98 % 7 == 0)
        if pc == F.YEAR: return 2026
        if pc == F.REGIONAL_SITE: return 0x5000 + 0x10 * a[0] + a[1]
        if pc == F.FINAL_FOUR_SITE: return 0x6000 + a[0]
        if pc == F.EVENT_RESET:
            self.calls.append(('reset', a[0])); return 0
        if pc == F.EVENT_BUILD:
            e, n, ids = a[0], a[1], a[2]
            self.calls.append(('build', e, n, [self.m.u(ids + 2 * j, 2) for j in range(n)], a[3] & 0xFFFFFFFF, a[4], a[5]))
            return 1
        raise AssertionError(hex(pc))


def nonvolatile_ok(cpu, start, err, sp=STACK):
    for k in range(13, 32):
        if cpu.r[k] != start[k]: err.append(f'r{k} clobbered')
    if cpu.r[1] != sp: err.append(f'r1 {cpu.r[1]:#x}')
    if cpu.r[2] != MAIN_TOC: err.append('TOC not restored')


results = []
def check(name, ok, err=()):
    ok = ok and not err; results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'} {name}", list(err) if err else '')


# ---------------- MARK ----------------
def test_mark():
    for hook, (n, cmp, ret) in F.MARK_SITES.items():
        for autos in (31, 4, 2):
            w = World(); w.field([(team(i), 1, 1000 - i) for i in range(autos)] + [(0, 0, 0)] * (65 - autos))
            how, cpu, start, err = w.run(F.build_mark(hook), {n: autos, cmp: 7}, stop=(ret,))
            types = [w.m.u(FIELD + 12 * i + 4, 4) for i in range(autos)]
            scores = [w.m.u(FIELD + 12 * i + 8, 4) for i in range(autos)]
            k = min(4, autos)
            want_t = [1] * (autos - k) + [2] * k
            want_s = [1000 - i for i in range(autos - k)] + [0xC61C4000] * k
            ok = how == ret and types == want_t and scores == want_s and cpu.cr[7] == 4
            for r_ in range(13, 32):
                if cpu.r[r_] != start[r_]: err.append(f'r{r_}')
            check(f'mark {hook:#x} autos={autos}', ok, err)
    w = World(); w.field([(team(i), 1, 5) for i in range(10)])
    how, cpu, _, err = w.run(F.build_mark(0x5C1D30), {25: 10, 27: 0}, stop=(0x5C1D80,))
    check('mark: cr7 EQ when candidate count is 0', how == 0x5C1D80 and cpu.cr[7] == 2, err)


# ---------------- NIT ----------------
def test_nit():
    w = World()
    field_teams = [team(i) for i in range(65)]
    w.field([(t, 1, 0) for t in field_teams])
    cands = [team(i) for i in range(31, 65)] + [team(200 + k) for k in range(60)]   # 34 at-large then outsiders
    w.table(CAND, cands)
    nit = [team(203)]                      # an automatic NIT team (regular-season champion)
    w.table(NIT, nit + [0] * 31)
    skipped = []; code = F.build_nit()
    r30 = 34
    while len(nit) < 32:
        how, cpu, start, err = w.run(code, {30: r30, 26: len(nit), 31: CAND + 12 * r30}, stop=(0x5C20FC,))
        t = cands[r30]
        if t in nit:
            r30 += 1; continue
        if err: check('nit run', False, err); return
        if how == 'END':
            if cpu.r[0] != (r30 << 2) & 0xFFFFFFFF: check('nit: original slwi', False); return
            nit.append(t); w.table(NIT, nit + [0] * (32 - len(nit)))
        else:
            skipped.append(t)
        for r_ in range(13, 32):
            if cpu.r[r_] != start[r_]: check('nit regs', False, [f'r{r_}']); return
        r30 += 1
    want_skip = [team(200), team(201), team(202)]
    check('nit: skips first three outsiders, keeps auto NIT team', skipped == want_skip and nit[1] == team(204) and team(203) in nit)
    return want_skip, nit


# ---------------- BUILD ----------------
def expected_bracket(n_auto_low_after_last_at=2):
    pass


def test_build(at=0, auto=1):
    w = World()
    # field order: 59 normal (mixed), last at-large at 58, autos at 59, 60, play-in autos 61-64
    types = [at if (i % 3) else auto for i in range(59)] + [auto, auto, 2, 2, 2, 2]
    types[58] = at
    w.field([(team(i), types[i], 900 - i) for i in range(65)])
    outsiders = [team(200 + k) for k in range(60)]
    w.table(CAND, [team(i) for i in range(65) if types[i] == at] + outsiders)
    w.table(NIT, [team(201)] + [team(210 + k) for k in range(31)])
    w.links([(2, 6, 1), (3, 6, 2), (4, 6, 3)])
    how, cpu, start, err = w.run(F.build_builder(), regs={})
    nonvolatile_ok(cpu, start, err)
    # expected
    direct = [team(i) for i in range(61) if i != 58]
    pos, it = [], iter(direct)
    for p in range(64): pos.append(0 if p in F.HOLES else next(it))
    regions = [[0] * 16 for _ in range(4)]
    for k in range(8):
        for r in range(4):
            regions[r][2 * k], regions[r][2 * k + 1] = pos[8 * k + r], pos[8 * k + 7 - r]
    want = [('build', 90, 2, [tid(team(63)), tid(team(64))], SITE, 100, 3),
            ('reset', 2), ('build', 2, 2, [tid(team(61)), tid(team(62))], SITE, 100, 3),
            ('reset', 3), ('build', 3, 2, [tid(team(58)), tid(team(200))], SITE, 101, 3),
            ('reset', 4), ('build', 4, 2, [tid(team(202)), tid(team(203))], SITE, 101, 3)]
    want += [('build', 91 + k, 16, [tid(t) for t in regions[k]], 0x5000 + 0x10 * 18 + k, 102, 3) for k in range(4)]
    want += [('build', 95, 4, [0x7FFF] * 4, 0x6000 + 18, 118, 3)]
    got = w.calls
    for g, x in zip(got, want):
        if g != x: err.append(f'call {g} != {x}')
    if len(got) != len(want): err.append(f'{len(got)} calls, want {len(want)}')
    links = [tuple(w.m.u(LINKS + 12 * k + 4 * j, 4) for j in range(3)) for k in range(3)]
    if links != [(2, 92, 16), (3, 93, 11), (4, 94, 11)]: err.append(f'links {links}')
    check(f'build (at-large type {at}): 4 play-ins, 60 direct, holes at 11/16 seeds, regionals, final four', how == 0x50000000, err)
    # seeds: the hole slots
    holes = [(r, j) for r in range(4) for j in range(16) if regions[r][j] == 0]
    check('build: holes are East 16, South 16, Midwest 11, West 11', holes == [(0, 15), (1, 15), (2, 10), (3, 10)])
    # every team exactly once across the 68
    allt = [t for reg in regions for t in reg if t] + [team(i) for i in (58, 61, 62, 63, 64)] + [team(200), team(202), team(203)]
    check('build: 68 distinct teams', len(allt) == 68 and len(set(allt)) == 68)


def test_build_fallback():
    w = World()
    w.field([(team(i), 0 if i < 63 else 2, 900 - i) for i in range(65)])   # stock-style: two play-in teams
    w.table(CAND, [team(200 + k) for k in range(10)])
    how, cpu, start, err = w.run(F.build_builder())
    for k in range(13, 32):
        if cpu.r[k] != start[k]: err.append(f'r{k}')
    check('build: two play-in teams -> stock builder (first instruction re-run)',
          how == 'END' and cpu.r[1] == STACK - 0x1D0 and not w.calls and cpu.lr == 0x50000000, err)


# ---------------- REC ----------------
def test_rec():
    for hook, (x, b, b2, ret) in F.REC_SITES.items():
        for e, typ, n, remap in ((2, 3, 2, True), (3, 3, 2, True), (4, 3, 2, True), (4, 3, 16, False),
                                 (2, 0, 2, False), (5, 3, 2, False), (90, 3, 2, False), (1, 3, 2, False), (91, 3, 16, False)):
            w = World(); w.state(e, typ, [0] * n)
            how, cpu, start, err = w.run(F.build_rec(hook), {x: e}, stop=(ret,) if ret else ())
            want = RECORDS + ((90 - e) * F.RECORD if remap else 0)
            if cpu.r[b] != want: err.append(f'r{b}={cpu.r[b]:#x} want {want:#x}')
            if b2 is not None and cpu.r[b2] != want: err.append(f'r{b2}')
            for k in range(32):
                if k not in (b, b2) and cpu.r[k] != start[k]: err.append(f'r{k} changed')
            if cpu.cr != [1, 2, 4, 8, 2, 4, 8, 1]: err.append('cr changed')
            check(f'rec {hook:#x} event {e} type {typ} n {n} -> {"90" if remap else "own"}',
                  how == (ret if ret else 'END'), err)


# ---------------- APPS ----------------
def test_apps():
    w = World()
    regions = [[team(16 * r + j) for j in range(16)] for r in range(4)]
    regions[0][15] = regions[1][15] = regions[2][10] = regions[3][10] = 0
    for r in range(4): w.state(91 + r, 3, [tid(t) for t in regions[r]])
    w.state(90, 3, [tid(team(300)), tid(team(301))])
    w.state(2, 3, [tid(team(302)), tid(team(303))])
    w.state(3, 3, [tid(team(304)), tid(team(305))])
    w.state(4, 3, [tid(team(306)), tid(team(307))])
    rows = [(2, 92, 16), (3, 93, 11), (4, 94, 11), (5, 6, 4)] + [(0, 0, 0)] * 12 + [(90, 91, 16)]
    w.links(rows)
    cases = [(team(0), 1), (team(17), 2), (team(16 * 2 + 9), 10), (team(16 * 3 + 14), 15),
             (team(300), 16), (team(301), 16), (team(303), 16), (team(304), 11), (team(307), 11), (team(999), None)]
    code = F.build_apps()
    for t, seed in cases:
        how, cpu, start, err = w.run(code, {3: t, 29: 5, 30: 0}, stop=(0x5C1A14, 0x5C1ACC, 0x5C19E4))
        if cpu.r[31] != t: err.append('r31 != team')
        for k in range(13, 30):
            if cpu.r[k] != start[k]: err.append(f'r{k}')
        if cpu.r[1] != STACK or cpu.r[2] != MAIN_TOC: err.append('r1/r2')
        if seed is None: ok = how == 0x5C1ACC
        else: ok = how == 0x5C1A14 and cpu.r[30] == 4 * (seed - 1)
        check(f'apps team {tid(t)} -> seed {seed}', ok, err)
    # play-in events from a finished holiday tournament (type 0) are ignored
    w.state(3, 0, [tid(team(304)), tid(team(305))])
    how, cpu, _, err = w.run(code, {3: team(304), 30: 0}, stop=(0x5C1A14, 0x5C1ACC, 0x5C19E4))
    check('apps: holiday event 3 (type 0) not counted', how == 0x5C1ACC, err)
    w2 = World(); w2.state(91, 0, [])
    how, cpu, _, err = w2.run(code, {3: team(5), 30: 0}, stop=(0x5C1A14, 0x5C1ACC, 0x5C19E4))
    check('apps: no bracket built -> stock field search', how == 0x5C19E4 and cpu.r[0] == 0x41 and cpu.r[31] == team(5), err)


def test_links():
    for name, code, regs, typ, stop in (('build', F.build_link_build(), lambda e, ty: {31: e, 8: ty, 9: 0x1234, 24: STATES + F.STATE * e}, None, None),
                                         ('finish', F.build_link_finish(), lambda e, ty: {28: e}, None, None)):
        for e, ty, fix in ((2, 0, True), (3, 1, True), (4, 0, True), (2, 3, False), (5, 0, False), (90, 0, False), (1, 0, False)):
            w = World(); w.links([(2, 92, 16), (3, 93, 11), (4, 94, 11), (5, 6, 4)]); w.state(e, ty, [1, 2])
            how, cpu, start, err = w.run(code, regs(e, ty))
            rows = [tuple(w.m.u(LINKS + 12 * k + 4 * j, 4) for j in range(3)) for k in range(4)]
            want = [(2, 92, 16), (3, 93, 11), (4, 94, 11), (5, 6, 4)]
            if fix: want[e - 2] = (e, 6, e - 1)
            if rows != want: err.append(f'rows {rows}')
            if name == 'build':
                if w.m.u(STATES + F.STATE * e, 4) != ty & 0xFFFFFFFF: err.append('type not stored')
                for k in range(1, 11):
                    if k not in (0, 11, 12) and cpu.r[k] != start[k]: err.append(f'r{k} changed')
            else:
                if cpu.r[0] != 0x15: err.append('r0 != 0x15')
                for k in range(1, 32):
                    if k not in (0, 9) and cpu.r[k] != start[k]: err.append(f'r{k} changed')
            for k in range(13, 32):
                if cpu.r[k] != start[k]: err.append(f'r{k}')
            check(f'links {name} event {e} type {ty} -> {"restored" if fix else "kept"}', how == 'END', err)


if __name__ == '__main__':
    test_mark(); test_nit(); test_build(); test_build(at=1, auto=0); test_build_fallback(); test_rec(); test_apps(); test_links()
    print(f'{sum(results)}/{len(results)} passed')
    sys.exit(0 if all(results) else 1)
