"""Stage 2 (Tournament Tree) caves in the interpreter with modeled event/game lookups."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import first_four_test as T
import first_four_tree_asm as G
from rank_interp import M64, STACK

T.MAIN_FUNCS |= {G.EVENT_OF_GAME, G.GET_GAME, G.IS_GAME_24}
ENTRY = T.DATA + 0x50000
results = []


def check(name, ok, err=()):
    ok = ok and not err; results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'} {name}", list(err) if err else '')


class TreeWorld(T.World):
    def __init__(self, games):
        super().__init__(); self.games = games                     # {(event, index): game id}

    def event_of(self, g):
        for (e, k), v in sorted(self.games.items()):
            if v == g: return e
        return -1

    def call(self, pc, a, cpu):
        if pc == G.EVENT_OF_GAME: return self.event_of(a[0] & 0xFFFFFFFF)
        if pc == G.GET_GAME: return self.games.get((a[0] & 0xFFFFFFFF, a[1] & 0xFFFFFFFF), 0)
        if pc == G.IS_GAME_24:
            g = self.m.u(a[0] & 0xFFFFFFFF, 4); e = self.event_of(g)
            return int(e >= 0 and self.games.get((e, 24)) == g)
        return super().call(pc, a, cpu)


def world(holiday3=False):
    games = {(e, k): 0x1000 * e + k for e in (91, 92, 93, 94) for k in range(16, 32)}
    games.update({(85, k): 0x55000 + k for k in range(24, 32)}); games[(60, 24)] = 0x60024
    w = TreeWorld(games)
    w.links([(2, 92, 16), (3, 93, 11), (4, 94, 11), (5, 6, 4)] + [(0, 0, 0)] * 12 + [(90, 91, 16)])
    for e in (2, 4): w.state(e, 3, [1, 2])
    w.state(3, 0 if holiday3 else 3, [1, 2, 3, 4] if holiday3 else [1, 2])
    return w


def run_label(code, game, regs, stops, holiday3=False):
    w = world(holiday3); w.m.w(ENTRY, 4, game)
    how, cpu, start, err = w.run(code, regs, stop=stops)
    for k in range(13, 32):
        if cpu.r[k] != start[k]: err.append(f'r{k}')
    if cpu.r[1] != STACK or cpu.r[2] != T.MAIN_TOC: err.append('r1/r2')
    return how, err


def test_text():
    code = G.build_label_text(); stops = (0x65DF58, 0x65DEE0)
    for name, game, want, h3 in (('East 1-16 (event 90)', 0x1000 * 91 + 24, 0x65DF58, False),
                                 ('South 1-16 (event 2)', 0x1000 * 92 + 24, 0x65DF58, False),
                                 ('Midwest 6-11 (event 3)', 0x1000 * 93 + 28, 0x65DF58, False),
                                 ('West 6-11 (event 4)', 0x1000 * 94 + 28, 0x65DF58, False),
                                 ('Midwest, event 3 is a holiday event', 0x1000 * 93 + 28, 0x65DEE0, True),
                                 ('East second round', 0x1000 * 91 + 16, 0x65DEE0, False),
                                 ('NIT game', 0x55000 + 24, 0x65DEE0, False),
                                 ('game in no event', 0x777, 0x65DEE0, False)):
        how, err = run_label(code, game, {30: ENTRY}, stops, h3)
        check(f'text: {name}', how == want, err)


def test_tbd():
  for code in (G.build_tbd(), G.build_tbd2()):
    stops = (0x65DF58,)
    for name, game, t2, want in (('South 1-16 TBD', 0x1000 * 92 + 24, 0x7FFF, 0x65DF58),
                                 ('Midwest 6-11 TBD', 0x1000 * 93 + 28, 0x7FFF, 0x65DF58),
                                 ('East 1-16 TBD', 0x1000 * 91 + 24, 0x7FFF, 0x65DF58),
                                 ('East second round TBD', 0x1000 * 91 + 16, 0x7FFF, 'END'),
                                 ('NIT TBD', 0x55000 + 24, 0x7FFF, 'END'),
                                 ('fed game, second team known', 0x1000 * 92 + 24, 55, 'END')):
        w = world(); w.m.w(ENTRY, 4, game); w.m.w(ENTRY + 6, 2, t2)
        how, cpu, start, err = w.run(code, {30: ENTRY}, stop=stops)
        for k in range(13, 32):
            if k != 29 and cpu.r[k] != start[k]: err.append(f'r{k}')
        if how == 'END' and cpu.r[29] != STACK + 0x78: err.append('stock addi r29 not run')
        if cpu.r[1] != STACK or cpu.r[2] != T.MAIN_TOC: err.append('r1/r2')
        check(f'tbd: {name}', how == want, err)


UI, REGION_TABLE = T.DATA + 0x61000, T.DATA + 0x60000


def nav_world(page, h3=False, region_order=(0, 1, 2, 3)):
    w = HideWorld({(e, 0): 0x9000 + e for e in (90, 2, 3, 4)})
    w.links([(2, 92, 16), (3, 93, 11), (4, 94, 11), (5, 6, 4)] + [(0, 0, 0)] * 12 + [(90, 91, 16)])
    for e in (2, 4): w.state(e, 3, [1, 2])
    w.state(3, 0 if h3 else 3, [1, 2, 3, 4] if h3 else [1, 2])
    w.m.w(T.MAIN_TOC - 0x2D8, 4, UI); w.m.w(UI + 0x18, 4, page)
    w.m.w(T.MAIN_TOC - 0x2D0, 4, REGION_TABLE)
    for j, reg in enumerate(region_order): w.m.w(REGION_TABLE + 4 * j, 4, reg)
    return w


class HideWorld(TreeWorld):
    def call(self, pc, a, cpu):
        if pc == G.SET_CURSOR: self.calls.append(('cursor', a[0])); return 0
        if pc == G.SET_CURSOR_SUB: self.calls.append(('sub', a[0])); return 0
        if pc == G.REDRAW: self.calls.append(('redraw', a[0])); return 0
        return super().call(pc, a, cpu)


def test_playin_box():
    code = G.build_playin_box(); stops = (0x65A3B4, 0x65A570)
    for k, page, want, h3 in ((0, 90, 90, False), (0, 2, 2, False), (0, 3, 3, False), (0, 4, 4, False),
                              (0, 91, 90, False), (0, 3, 90, True), (1, 2, None, False), (2, 3, None, False),
                              (3, 4, None, False)):
        w = nav_world(page, h3)
        how, cpu, start, err = w.run(code, {30: k, 31: 0x1234}, stop=stops)
        for r_ in range(13, 32):
            if cpu.r[r_] != start[r_]: err.append(f'r{r_}')
        ok = (how == 0x65A570) if want is None else (how == 0x65A3B4 and cpu.r[3] == 0x9000 + want)
        check(f'play-in box k={k} on page {page} -> {want}{" (event 3 holiday)" if h3 else ""}', ok, err)


def test_nav():
    T.MAIN_FUNCS.update({G.SET_CURSOR, G.SET_CURSOR_SUB, G.REDRAW})
    for hook in G.NAV_HOOKS:
        code = G.build_nav(hook)
        for page, cursor_event, want, h3 in ((3, 2, 3, False), (2, 95, 2, False), (90, 91, 90, False), (4, 4, 4, False),
                                              (91, 90, 90, False), (95, 95, 95, False), (3, 2, 2, True), (5, 7, 7, False)):
            w = nav_world(page, h3)
            how, cpu, start, err = w.run(code, {3: cursor_event})
            for r_ in range(13, 32):
                if cpu.r[r_] != start[r_]: err.append(f'r{r_}')
            check(f'nav {hook:#x} page {page}, cursor event {cursor_event} -> step from {want}', how == 'END' and cpu.r[3] == want, err)


def test_cursor():
    code = G.build_cursor(); stops = (0x65A298, 0x65A268)
    for name, page, found, order, want in (('search still running', 3, False, (0, 1, 2, 3), (0x65A268, [])),
                                           ('not found on page 3 -> East box 63', 3, True, (0, 1, 2, 3), (0x65A298, [('redraw', 3), ('cursor', 63), ('sub', 0)])),
                                           ('East is region k=2 -> box 65', 2, True, (1, 3, 0, 2), (0x65A298, [('redraw', 2), ('cursor', 65), ('sub', 0)])),
                                           ('not found on page 90 -> East box', 90, True, (0, 1, 2, 3), (0x65A298, [('redraw', 90), ('cursor', 63), ('sub', 0)])),
                                           ('not found on a regional page -> stock', 92, True, (0, 1, 2, 3), (0x65A298, []))):
        w2 = nav_world(page, region_order=order)
        # the stock code compared r31 with 0x43 into cr7 just before the hook (EQ = not found)
        how, cpu, start, err = run_with_cr(w2, code, {31: 0x43 if found else 5}, 2 if found else 8, stops)
        for r_ in range(13, 32):   # r30/r31 are restored by the function epilogue at 0x65A298
            if cpu.r[r_] != start[r_] and not (how == 0x65A298 and r_ in (30, 31)): err.append(f'r{r_}')
        check(f'cursor: {name}', (how, w2.calls) == want, err)


def run_with_cr(w, code, regs, cr7, stops):
    m = w.m; m.write(T.CAVE, code); cpu = T.CPU2(m)
    for k in range(32): cpu.r[k] = 0x3333000000000000 + k
    cpu.r[1], cpu.r[2], cpu.lr = STACK, T.MAIN_TOC, 0x50000000
    for k, v in regs.items(): cpu.r[k] = v
    cpu.cr = [1, 2, 4, 8, 2, 4, 8, cr7]
    start = list(cpu.r); err = []; pc = T.CAVE; end = T.CAVE + len(code); steps = 0
    while True:
        steps += 1
        if steps > 100000: err.append('runaway'); break
        if pc in stops: return pc, cpu, start, err
        if pc in T.MAIN_FUNCS or pc in T.STUBS:
            res = w.call(pc, cpu.r[3:9], cpu)
            for v in T.VOLATILE: cpu.r[v] = 0xBAD0000 + v
            cpu.r[3] = res & M64; pc = cpu.lr; continue
        if not T.CAVE <= pc < end: err.append(f'left cave {pc:#x}'); break
        pc = cpu.step(pc)
    return 'END', cpu, start, err


def test_style():
    code = G.build_label_style(); stops = (0x65E848, 0x65E824, 0x65E80C)
    for name, game, t2, want in (('South 1-16 TBD', 0x1000 * 92 + 24, 0x7FFF, 0x65E848),
                                 ('Midwest 6-11 TBD', 0x1000 * 93 + 28, 0x7FFF, 0x65E848),
                                 ('East 1-16 filled', 0x1000 * 91 + 24, 123, 0x65E80C),
                                 ('conference game 24 TBD (stock path)', 0x60024, 0x7FFF, 0x65E824),
                                 ('NIT game', 0x55000 + 25, 0x7FFF, 0x65E80C)):
        how, err = run_label(code, game, {24: ENTRY, 25: t2}, stops)
        check(f'style: {name}', how == want, err)


def test_seed():
    for hook in G.SEED_HOOKS:
        code = G.build_seed(hook)
        for e, typ, n, eq in ((90, 3, 2, True), (2, 3, 2, True), (4, 3, 2, True), (2, 0, 4, False),
                              (3, 3, 16, False), (91, 3, 16, False), (5, 3, 2, False), (0x7FFFFFFF, 0, 0, False)):
            w = T.World()
            if e < 97: w.state(e, typ, [1] * n)
            how, cpu, start, err = w.run(code, {3: e})
            for k in range(32):
                if k not in (11, 12) and cpu.r[k] != start[k]: err.append(f'r{k}')
            check(f'seed {hook:#x} event {e} type {typ} n {n} -> {"hidden" if eq else "shown"}',
                  how == 'END' and (cpu.cr[7] == 2) == eq, err)


if __name__ == '__main__':
    test_seed(); test_text(); test_tbd(); test_playin_box(); test_nav(); test_cursor(); test_style()
    print(f'{sum(results)}/{len(results)} passed')
    sys.exit(0 if all(results) else 1)
