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


def test_show_region():
    code = G.build_show_region(); RET = 0x50000000
    for name, team_id, h3, want in (('event 2 team -> South (92)', 141, False, 92), ('event 3 team -> Midwest (93)', 157, False, 93),
                                    ('event 4 team -> West (94)', 240, False, 94), ('event 90 team -> stock', 186, False, 'END'),
                                    ('regional team -> stock', 49, False, 'END'), ('event 3 is a holiday event -> stock', 157, True, 'END'),
                                    ('null team -> stock', None, False, 'END')):
        w = world(h3)
        w.state(2, 3, [141, 329]); w.state(4, 3, [309, 240]); w.state(90, 3, [186, 147])
        w.state(3, 0 if h3 else 3, [237, 157, 1, 2] if h3 else [237, 157])
        team = 0 if team_id is None else T.TEAMS + 0x30
        if team: w.m.w(team + 0x15E, 2, team_id)
        how, cpu, start, err = w.run(code, {3: team}, stop=(RET,))
        for r_ in range(13, 32):
            if cpu.r[r_] != start[r_]: err.append(f'r{r_}')
        if cpu.r[1] != (STACK - 0x90 if want == 'END' else STACK): err.append('r1')
        if want == 'END':
            ok = how == 'END' and cpu.r[3] == team   # the copied stock stdu has run; the function continues
        else:
            ok = how == RET and cpu.r[3] == want
        check(f'show region: {name}', ok, err)


def test_show_seed():
    code = G.build_show_seed(); RET = 0x50000000
    for name, team_id, h3, want in (('event 2 team -> 16', 141, False, 16), ('event 3 team -> 11', 157, False, 11),
                                    ('event 4 team -> 11', 240, False, 11), ('event 90 team -> stock', 186, False, 'END'),
                                    ('event 3 holiday -> stock', 157, True, 'END')):
        w = world(h3)
        w.state(2, 3, [141, 329]); w.state(4, 3, [309, 240]); w.state(90, 3, [186, 147])
        w.state(3, 0 if h3 else 3, [237, 157, 1, 2] if h3 else [237, 157])
        team = T.TEAMS + 0x30; w.m.w(team + 0x15E, 2, team_id)
        how, cpu, start, err = w.run(code, {3: team}, stop=(RET,))
        ok = (how == 'END' and cpu.r[3] == team) if want == 'END' else (how == RET and cpu.r[3] == want)
        check(f'show seed: {name}', ok, err)


def test_show_pair():
    for hook in G.SHOW_PAIR_HOOKS:
        code = G.build_show_pair(hook)
        for name, region, slot, h3, want in (('East 16 -> 90', 91, 15, False, 90), ('South 16 -> 2', 92, 15, False, 2),
                                             ('Midwest 11 -> 3', 93, 10, False, 3), ('West 11 -> 4', 94, 10, False, 4),
                                             ('Midwest 11, event 3 holiday -> 90', 93, 10, True, 90),
                                             ('South 15 (no row) -> 90', 92, 14, False, 90)):
            w = world(h3)
            how, cpu, start, err = w.run(code, {29: region, 30: slot, 0: 0x1111, 4: 0x4444, 11: 0xBBBB})
            for r_ in (0, 4, 11) + tuple(range(13, 32)):
                if cpu.r[r_] != start[r_]: err.append(f'r{r_}')
            if cpu.cr[0] != 1: err.append('cr0 changed')
            check(f'show pair {hook:#x}: {name}', how == 'END' and cpu.r[3] == want, err)


def test_pair_store():
    SLOTS = STACK + 0x138
    for slot, want in ((15, {'s15': 0xA, 's16': 0xB, 'slot': None}), (10, {'s15': 0, 's16': 0, 'slot': 0xA})):
        w = world()
        for hook, val in ((0x5EC438, 0xA), (0x5EC44C, 0xB)):
            how, cpu, start, err = w.run(G.build_pair_store(hook), {3: val, 30: slot, 20: SLOTS})
            for r_ in [k for k in range(32) if k != 12]:
                if cpu.r[r_] != start[r_]: err.append(f'r{r_}')
            if how != 'END': err.append(str(how))
        got = {'s15': w.m.u(STACK + 0x174, 4), 's16': w.m.u(STACK + 0x178, 4), 'slot': w.m.u(SLOTS + 4 * slot, 4) if slot != 15 else None}
        check(f'pair store: empty slot {slot} -> {want}', got == want, err)


class NameWorld(TreeWorld):
    """Teams: pointer TEAMS + 0x400 * id, name pointer at +0 = 0x7000 + id, id at +0x15E."""
    def __init__(self, games):
        super().__init__(games); self.fmt = []; self.freed = []
    def call(self, pc, a, cpu):
        if pc == G.TEAM_OF: return 0 if a[0] == 0 else T.TEAMS + 0x400 * (a[0] & 0xFFFF)
        if pc == G.GET_TEAM:
            ids = {2: (141, 329), 3: (237, 157), 4: (309, 240), 90: (186, 147)}.get(a[0] & 0xFFFFFFFF)
            return 0 if ids is None else T.TEAMS + 0x400 * ids[a[1] & 1]
        if pc == G.STR_FROM:
            self.m.w(a[0] & 0xFFFFFFFF, 4, 0x55000000 | (a[1] & 0xFFFF)); return a[0]
        if pc == G.FORMAT:
            out, tmpl, args = (x & 0xFFFFFFFF for x in a[:3])
            n = self.m.u(args + 4, 4)
            vals = [(self.m.u(self.m.u(args + 0xC + 12 * i, 4), 4), self.m.u(args + 0x10 + 12 * i, 4)) for i in range(n)]
            self.fmt.append((out, self.m.u(tmpl, 4), vals)); return 0
        if pc == G.STR_FREE: self.freed.append(a[0] & 0xFFFFFFFF); return 0
        return super().call(pc, a, cpu)


def test_playin_names():
    T.STUBS.update({G.TEAM_OF, G.STR_FROM, G.FORMAT, G.STR_FREE}); T.MAIN_FUNCS.add(G.GET_TEAM)
    code = G.build_playin_names(); SHOW, WIDGET, STR_T_VAL = T.DATA + 0x70000, T.DATA + 0x71000, 0x5754
    for name, team1_id, h3, want in (('East 1 seed -> event 90 pair', 49, False, (186, 147)),
                                     ('South 1 seed -> event 2 pair', 84, False, (141, 329)),
                                     ('Midwest 6 seed -> event 3 pair', 58, False, (237, 157)),
                                     ('West 6 seed -> event 4 pair', 114, False, (309, 240)),
                                     ('Midwest 6 seed, event 3 holiday -> stock', 58, True, None),
                                     ('team not in a regional -> stock', 999, False, None),
                                     ('no team 1 -> stock', 0, False, None)):
        w = NameWorld({})
        w.links([(2, 92, 16), (3, 93, 11), (4, 94, 11), (5, 6, 4)] + [(0, 0, 0)] * 12 + [(90, 91, 16)])
        regions = {91: [49] + [1] * 14 + [0x7FFF], 92: [84] + [1] * 14 + [0x7FFF],
                   93: [2] * 5 + [58] + [2] * 4 + [0x7FFF] + [2] * 5, 94: [3] * 5 + [114] + [3] * 4 + [0x7FFF] + [3] * 5}
        for e, ids in regions.items(): w.state(e, 3, ids)
        w.state(2, 3, [141, 329]); w.state(4, 3, [309, 240]); w.state(90, 3, [186, 147])
        w.state(3, 0 if h3 else 3, [237, 157, 9, 9] if h3 else [237, 157])
        for tid in (49, 84, 58, 114, 999, 141, 329, 237, 157, 309, 240, 186, 147):
            w.m.w(T.TEAMS + 0x400 * tid + 0x15E, 2, tid); w.m.w(T.TEAMS + 0x400 * tid, 4, 0x7000 + tid)
        w.m.w(T.MAIN_TOC - 0x2CE8, 4, SHOW); w.m.w(SHOW + 0x10, 4, team1_id)
        w.m.w(T.MAIN_TOC + G.STR_T, 4, STR_T_VAL)
        how, cpu, start, err = w.run(code, {31: WIDGET}, stop=(0x5E5530,))
        for r_ in range(13, 32):   # the stock path runs the copied addi r29,r1,0xFC
            if cpu.r[r_] != start[r_] and not (r_ == 29 and want is None): err.append(f'r{r_}')
        if cpu.r[2] != T.MAIN_TOC: err.append('TOC')
        if want is None:
            ok = how == 'END' and not w.fmt and cpu.r[1] == STACK and cpu.r[29] == STACK + 0xFC
        else:
            exp = [(WIDGET + 0x10, 0x0018C1FB, [(0x55000000 | (0x7000 + want[0]), STR_T_VAL), (0x55000000 | (0x7000 + want[1]), STR_T_VAL)])]
            ok = how == 0x5E5530 and w.fmt == exp and len(w.freed) == 2 and cpu.r[1] == STACK
            if w.fmt != exp: err.append(f'fmt {w.fmt}')
        check(f'play-in names: {name}', ok, err)


def test_featured():
    T.MAIN_FUNCS.update({G.SEG_TEAM1, G.GET_TEAM})
    code = G.build_featured()
    for name, featured, team1_id, h3, want in (('null, Midwest 6 seed -> event 3 team A', 0, 58, False, 237),
                                               ('null, South 1 seed -> event 2 team A', 0, 84, False, 141),
                                               ('null, East 1 seed -> event 90 team A', 0, 49, False, 186),
                                               ('null, Midwest 6 seed, event 3 holiday -> null', 0, 58, True, 0),
                                               ('null, no segment game -> null', 0, None, False, 0),
                                               ('featured team present -> unchanged', 0x4444, 58, False, 0x4444)):
        w = NameWorld({})
        seg = 0 if team1_id is None else T.TEAMS + 0x400 * team1_id
        orig_call = w.call
        def call(pc, a, cpu, seg=seg, orig=orig_call):
            if pc == G.SEG_TEAM1: return seg
            return orig(pc, a, cpu)
        w.call = call
        w.links([(2, 92, 16), (3, 93, 11), (4, 94, 11), (5, 6, 4)] + [(0, 0, 0)] * 12 + [(90, 91, 16)])
        regions = {91: [49] + [1] * 14 + [0x7FFF], 92: [84] + [1] * 14 + [0x7FFF],
                   93: [2] * 5 + [58] + [2] * 4 + [0x7FFF] + [2] * 5, 94: [3] * 5 + [114] + [3] * 4 + [0x7FFF] + [3] * 5}
        for e, ids in regions.items(): w.state(e, 3, ids)
        w.state(2, 3, [141, 329]); w.state(4, 3, [309, 240]); w.state(90, 3, [186, 147])
        w.state(3, 0 if h3 else 3, [237, 157, 9, 9] if h3 else [237, 157])
        for tid in (49, 84, 58, 114): w.m.w(T.TEAMS + 0x400 * tid + 0x15E, 2, tid)
        how, cpu, start, err = w.run(code, {3: featured})
        for r_ in range(13, 32):
            if cpu.r[r_] != start[r_]: err.append(f'r{r_}')
        if cpu.r[1] != STACK: err.append('r1')
        exp = want if want in (0, 0x4444) else T.TEAMS + 0x400 * want
        check(f'featured: {name}', how == 'END' and cpu.r[3] == exp and cpu.r[0] == w.m.u(STACK + 0x80, 8), err)


def test_playin_pair():
    T.MAIN_FUNCS.update({G.SEG_TEAM1})
    for hook in G.PLAYIN_PAIR_HOOKS:
        code = G.build_playin_pair(hook)
        for name, team1_id, h3, want in (('East 1 seed -> 90', 49, False, 90), ('South 1 seed -> 2', 84, False, 2),
                                         ('Midwest 6 seed -> 3', 58, False, 3), ('West 6 seed -> 4', 114, False, 4),
                                         ('Midwest 6 seed, event 3 holiday -> none', 58, True, 0),
                                         ('Midwest 3 seed (no play-in) -> none', 33, False, 0),
                                         ('no segment game -> 90', None, False, 90)):
            w = NameWorld({})
            seg = 0 if team1_id is None else T.TEAMS + 0x400 * team1_id
            orig_call = w.call
            def call(pc, a, cpu, seg=seg, orig=orig_call):
                if pc == G.SEG_TEAM1: return seg
                return orig(pc, a, cpu)
            w.call = call
            w.links([(2, 92, 16), (3, 93, 11), (4, 94, 11), (5, 6, 4)] + [(0, 0, 0)] * 12 + [(90, 91, 16)])
            regions = {91: [49] + [1] * 14 + [0x7FFF], 92: [84] + [1] * 14 + [0x7FFF],
                       93: [2, 2, 33] + [2] * 2 + [58] + [2] * 4 + [0x7FFF] + [2] * 5, 94: [3] * 5 + [114] + [3] * 4 + [0x7FFF] + [3] * 5}
            for e, ids in regions.items(): w.state(e, 3, ids)
            w.state(2, 3, [141, 329]); w.state(4, 3, [309, 240]); w.state(90, 3, [186, 147])
            w.state(3, 0 if h3 else 3, [237, 157, 9, 9] if h3 else [237, 157])
            for tid in (49, 84, 58, 114, 33): w.m.w(T.TEAMS + 0x400 * tid + 0x15E, 2, tid)
            lr = 0x50000000
            how, cpu, start, err = w.run(code, {}, lr=lr)
            for r_ in range(13, 32):
                if cpu.r[r_] != start[r_]: err.append(f'r{r_}')
            if cpu.r[1] != STACK or cpu.lr != lr: err.append('r1/lr')
            ok = (how == lr and cpu.r[3] == 0) if want == 0 else (how == 'END' and cpu.r[3] == want)
            check(f'play-in pair {hook:#x}: {name}', ok, err)


# Decompressed DRCT record of Director.iff (game data; extract it locally, it is not part of this repo)
DRCT = open(r'D:/Research Folder 3/director/Director.iff_0_director_DRCT.bin', 'rb').read()
NODES = 0x48000000   # director node block copied here (file offset 0x62000 -> NODES)


def test_node_gate():
    from rank_interp import LIB_TOC
    T.MAIN_FUNCS.update({G.SEG_TEAM1})
    code = G.build_node_gate()
    node = lambda off: NODES + off - 0x62000
    cases = (('play-in A, East 1 seed (event 90)', 0x63070, 49, False, 1),
             ('play-in A, South 1 seed (event 2)', 0x63070, 84, False, 1),
             ('play-in A, Midwest 6 seed (event 3)', 0x63070, 58, False, 1),
             ('play-in A, Midwest 3 seed (no feed)', 0x63070, 33, False, 0),
             ('play-in A, Midwest 6 seed, event 3 holiday', 0x63070, 58, True, 0),
             ('play-in A, no segment game', 0x63070, None, False, 0),
             ('play-in B, South 1 seed', 0x63058, 84, False, 1),
             ('play-in B, Midwest 3 seed', 0x63058, 33, False, 0),
             ('seed lines 1-2, South 1 seed', 0x630BC, 84, False, 0),
             ('seed line 1, West 6 seed', 0x630E0, 114, False, 0),
             ('seed line 3 >30, East 1 seed', 0x63094, 49, False, 0),
             ('seed line 3, South 1 seed', 0x630A8, 84, False, 0),
             ('seed lines 1-2, Midwest 3 seed -> stock', 0x630BC, 33, False, 'END'),
             ('seed line 1 copy in another group -> stock', 0x63148, 84, False, 'END'),
             ('seed line 3 copy in another group -> stock', 0x63134, 84, False, 'END'),
             ('team 1 line 1 -> stock', 0x63030, 84, False, 'END'))
    for name, off, team1_id, h3, want in cases:
        w = NameWorld({})
        w.m.write(NODES, DRCT[0x62000:0x64000])
        seg = 0 if team1_id is None else T.TEAMS + 0x400 * team1_id
        orig_call = w.call
        def call(pc, a, cpu, seg=seg, orig=orig_call):
            if pc == G.SEG_TEAM1: return seg
            return orig(pc, a, cpu)
        w.call = call
        w.links([(2, 92, 16), (3, 93, 11), (4, 94, 11), (5, 6, 4)] + [(0, 0, 0)] * 12 + [(90, 91, 16)])
        regions = {91: [49] + [1] * 14 + [0x7FFF], 92: [84] + [1] * 14 + [0x7FFF],
                   93: [2, 2, 33] + [2] * 2 + [58] + [2] * 4 + [0x7FFF] + [2] * 5, 94: [3] * 5 + [114] + [3] * 4 + [0x7FFF] + [3] * 5}
        for e, ids in regions.items(): w.state(e, 3, ids)
        w.state(2, 3, [141, 329]); w.state(4, 3, [309, 240]); w.state(90, 3, [186, 147])
        w.state(3, 0 if h3 else 3, [237, 157, 9, 9] if h3 else [237, 157])
        for tid in (49, 84, 58, 114, 33): w.m.w(T.TEAMS + 0x400 * tid + 0x15E, 2, tid)
        lr = 0x50000000; director = 0xD0040000
        how, cpu, start, err = w.run(code, {2: LIB_TOC, 3: director, 4: node(off)}, lr=lr)
        for r_ in range(13, 32):
            if cpu.r[r_] != start[r_]: err.append(f'r{r_}')
        sp = STACK - 0x90 if want == 'END' else STACK   # stock path runs the original stdu r1,-0x90(r1)
        if cpu.r[1] != sp or cpu.r[2] != LIB_TOC or cpu.lr != lr: err.append('r1/r2/lr')
        if want == 'END':
            ok = how == 'END' and cpu.r[3] == director and cpu.r[4] == node(off)
        else:
            ok = how == lr and cpu.r[3] == want
        check(f'node gate: {name}', ok, err)


def test_stamp_skip():
    from rank_interp import LIB_TOC
    code = G.build_stamp_skip()
    node = lambda off: NODES + off - 0x62000
    for name, off, skip in (('play-in A', 0x63070, True), ('play-in B', 0x63058, True),
                            ('seed lines 1-2', 0x630BC, False), ('team 1 line 1', 0x63030, False),
                            ('line 4 elsewhere (29 007F 00 not in group A)', 0x61C7D, False)):
        w = NameWorld({})
        w.m.write(NODES, DRCT[0x62000:0x64000])
        lr = 0x50000000
        how, cpu, start, err = w.run(code, {2: LIB_TOC, 3: 0xD0040000, 4: node(off)}, lr=lr)
        for r_ in [3, 4] + list(range(13, 32)):
            if cpu.r[r_] != start[r_]: err.append(f'r{r_}')
        sp = STACK if skip else STACK - 0x90
        if cpu.r[1] != sp or cpu.r[2] != LIB_TOC: err.append('r1/r2')
        check(f'stamp skip: {name}', how == (lr if skip else 'END'), err)


def test_region_feature():
    from rank_interp import LIB_TOC
    T.MAIN_FUNCS.update({G.SEG_TEAM1})
    code = G.build_region_feature()
    EXPR = 0x48100000 + 0x6EF3F - 0x6EF00   # region expression at an odd address, as in game
    for name, off, team1_id, want in (('region expr, South 1 seed (fed)', 0x6EF3F, 84, 91.0),
                                      ('region expr, East 1 seed (fed)', 0x6EF3F, 49, 91.0),
                                      ('region expr, Midwest 6 seed (fed)', 0x6EF3F, 58, 91.0),
                                      ('region expr, Midwest 3 seed (not fed) -> stock', 0x6EF3F, 33, 'END'),
                                      ('region expr, no segment game -> stock', 0x6EF3F, None, 'END'),
                                      ('seed expr, South 1 seed (fed) -> 1', 0x6EF00, 84, 1.0),
                                      ('seed expr, Midwest 6 seed (fed) -> 1', 0x6EF00, 58, 1.0),
                                      ('seed expr, West 6 seed (fed) -> 1', 0x6EF00, 114, 1.0),
                                      ('seed expr, Midwest 3 seed (not fed) -> stock', 0x6EF00, 33, 'END'),
                                      ('fact 6 expr, South 1 seed -> stock', 0x6EF2A, 84, 'END')):
        w = NameWorld({})
        w.m.write(0x48100000, DRCT[0x6EF00:0x6F000])
        seg = 0 if team1_id is None else T.TEAMS + 0x400 * team1_id
        orig_call = w.call
        def call(pc, a, cpu, seg=seg, orig=orig_call):
            if pc == G.SEG_TEAM1: return seg
            return orig(pc, a, cpu)
        w.call = call
        w.links([(2, 92, 16), (3, 93, 11), (4, 94, 11), (5, 6, 4)] + [(0, 0, 0)] * 12 + [(90, 91, 16)])
        regions = {91: [49] + [1] * 14 + [0x7FFF], 92: [84] + [1] * 14 + [0x7FFF],
                   93: [2, 2, 33] + [2] * 2 + [58] + [2] * 4 + [0x7FFF] + [2] * 5, 94: [3] * 5 + [114] + [3] * 4 + [0x7FFF] + [3] * 5}
        for e, ids in regions.items(): w.state(e, 3, ids)
        w.state(2, 3, [141, 329]); w.state(4, 3, [309, 240]); w.state(90, 3, [186, 147]); w.state(3, 3, [237, 157])
        for tid in (49, 84, 58, 114, 33): w.m.w(T.TEAMS + 0x400 * tid + 0x15E, 2, tid)
        out = 0x48200000; w.m.w(out, 4, 0x11111111)
        expr = 0x48100000 + off - 0x6EF00
        lr = 0x50000000
        how, cpu, start, err = w.run(code, {2: LIB_TOC, 3: 0x12789DAC, 4: 0xD00400D0, 5: expr, 6: out}, lr=lr)
        for r_ in range(13, 32):
            if cpu.r[r_] != start[r_]: err.append(f'r{r_}')
        if want == 'END':
            if cpu.r[1] != STACK - 0xE0 or cpu.r[2] != LIB_TOC: err.append('r1/r2')
            ok = how == 'END' and [cpu.r[k] for k in (3, 4, 5, 6)] == [0x12789DAC, 0xD00400D0, expr, out] and w.m.u(out, 4) == 0x11111111
        else:
            if cpu.r[1] != STACK or cpu.r[2] != LIB_TOC or cpu.lr != lr: err.append('r1/r2/lr')
            ok = how == lr and cpu.r[3] == 1 and w.m.u(out, 4) == {91.0: 0x42B60000, 1.0: 0x3F800000}[want]
        check(f'team 1 feature: {name}', ok, err)


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
    test_seed(); test_text(); test_tbd(); test_playin_box(); test_nav(); test_cursor(); test_show_region(); test_show_seed(); test_show_pair(); test_pair_store(); test_playin_names(); test_featured(); test_playin_pair(); test_node_gate(); test_stamp_skip(); test_region_feature(); test_style()
    print(f'{sum(results)}/{len(results)} passed')
    sys.exit(0 if all(results) else 1)
