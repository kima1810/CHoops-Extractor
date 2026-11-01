"""Tiny PPC64 interpreter for the scorebug rank patch (Unicorn PPC64 is unusable here).

Executes the real assembled bytes; game functions are modeled at their addresses.
Only the instructions used by the patch are implemented; anything else fails loudly.
"""
import re
import struct
import sys

import capstone

sys.path.insert(0, __file__.replace('\\', '/').rsplit('/', 1)[0])
import rank_asm as R

MAIN_TOC, LIB_TOC = 0xA64A94, 0xA54AC8
STACK, HEAP, DATA, RET = 0x20000000, 0x30000000, 0x40000000, 0x50000000
M64 = (1 << 64) - 1
md = capstone.Cs(capstone.CS_ARCH_PPC, capstone.CS_MODE_64 | capstone.CS_MODE_BIG_ENDIAN)


class Mem:
    def __init__(self):
        self.b = {}

    def write(self, a, data):
        for i, x in enumerate(data):
            self.b[a + i] = x

    def read(self, a, n):
        return bytes(self.b.get(a + i, 0) for i in range(n))

    def u(self, a, n):
        return int.from_bytes(self.read(a, n), 'big')

    def w(self, a, n, v):
        self.write(a, (v & ((1 << (8 * n)) - 1)).to_bytes(n, 'big'))


def sx(v, bits):
    v &= (1 << bits) - 1
    return v - (1 << bits) if v >> (bits - 1) else v


class CPU:
    def __init__(self, mem, code_ranges):
        self.m, self.r, self.cr, self.lr, self.ctr = mem, [0] * 32, [0] * 8, 0, 0
        self.code = code_ranges

    def syscall(self, pc):
        raise RuntimeError(f'sc at {pc:#x} with no handler')

    def setcr(self, field, a, b):
        self.cr[field] = 8 if a < b else 4 if a > b else 2   # LT GT EQ

    def step(self, pc):
        raw = self.m.read(pc, 4)
        ins = next(md.disasm(raw, pc), None)
        if ins is None:
            raise RuntimeError(f'undecodable at {pc:#x}')
        mn, ops = ins.mnemonic, [o.strip() for o in ins.op_str.split(',')] if ins.op_str else []
        R_ = lambda s: int(s.lstrip('r'))
        def memop(s):
            m = re.match(r'(-?(?:0x)?[0-9a-f]+)\(r(\d+)\)', s)
            return int(m.group(1), 0), int(m.group(2))
        imm = lambda s: int(s, 0)
        r, nxt = self.r, pc + 4
        if mn == 'mflr': r[R_(ops[0])] = self.lr
        elif mn == 'mtlr': self.lr = r[R_(ops[0])]
        elif mn in ('std', 'stw', 'sth', 'stdu'):
            d, ra = memop(ops[1]); n = {'std': 8, 'stdu': 8, 'stw': 4, 'sth': 2}[mn]
            ea = (r[ra] + d) & M64; self.m.w(ea, n, r[R_(ops[0])])
            if mn == 'stdu': r[ra] = ea
        elif mn in ('ld', 'lwz', 'lhz', 'lbz'):
            d, ra = memop(ops[1]); n = {'ld': 8, 'lwz': 4, 'lhz': 2, 'lbz': 1}[mn]
            r[R_(ops[0])] = self.m.u((r[ra] + d) & M64, n)
        elif mn in ('mr', 'or', 'or.', 'mr.'):
            src = R_(ops[1]); r[R_(ops[0])] = r[src]
            if mn.endswith('.'): self.setcr(0, sx(r[src], 64), 0)
        elif mn == 'li': r[R_(ops[0])] = imm(ops[1]) & M64
        elif mn == 'lis': r[R_(ops[0])] = (sx(imm(ops[1]), 16) << 16) & M64
        elif mn == 'addi': r[R_(ops[0])] = ((r[R_(ops[1])] if ops[1] != 'r0' else 0) + imm(ops[2])) & M64
        elif mn == 'addis': r[R_(ops[0])] = (r[R_(ops[1])] + (sx(imm(ops[2]), 16) << 16)) & M64
        elif mn == 'ori': r[R_(ops[0])] = r[R_(ops[1])] | imm(ops[2])
        elif mn == 'add': r[R_(ops[0])] = (r[R_(ops[1])] + r[R_(ops[2])]) & M64
        elif mn == 'subf': r[R_(ops[0])] = (r[R_(ops[2])] - r[R_(ops[1])]) & M64
        elif mn == 'mullw': r[R_(ops[0])] = (sx(r[R_(ops[1])], 32) * sx(r[R_(ops[2])], 32)) & M64
        elif mn == 'divw': r[R_(ops[0])] = int(sx(r[R_(ops[1])], 32) / sx(r[R_(ops[2])], 32)) & 0xFFFFFFFF
        elif mn == 'slwi': r[R_(ops[0])] = (r[R_(ops[1])] << imm(ops[2])) & 0xFFFFFFFF
        elif mn in ('cmpw', 'cmpwi'):
            f = int(ops[0].replace('cr', '')) if len(ops) == 3 else 0
            a = sx(r[R_(ops[-2])], 32)
            b = sx(r[R_(ops[-1])], 32) if mn == 'cmpw' else sx(imm(ops[-1]), 16)
            self.setcr(f, a, b)
        elif mn == 'bla':
            self.lr = pc + 4; nxt = imm(ops[-1])
        elif mn in ('beq', 'bne', 'blt', 'bge', 'b', 'bl'):
            target = imm(ops[-1])
            f = int(ops[0].replace('cr', '')) if len(ops) == 2 else 0
            take = {'beq': self.cr[f] == 2, 'bne': self.cr[f] != 2, 'blt': self.cr[f] == 8,
                    'bge': self.cr[f] != 8, 'b': True, 'bl': True}[mn]
            if mn == 'bl': self.lr = pc + 4
            if take: nxt = target
        elif mn == 'blr': nxt = self.lr
        elif mn == 'mfcr': r[R_(ops[0])] = sum(v << (28 - 4 * i) for i, v in enumerate(self.cr))
        elif mn == 'mtcrf' or mn == 'mtcr':
            v = r[R_(ops[-1])]; self.cr = [(v >> (28 - 4 * i)) & 15 for i in range(8)]
        elif mn == 'lwzx':
            r[R_(ops[0])] = self.m.u((r[R_(ops[1])] + r[R_(ops[2])]) & M64, 4)
        elif mn == 'cmplw':
            f = int(ops[0].replace('cr', '')) if len(ops) == 3 else 0
            self.setcr(f, r[R_(ops[-2])] & 0xFFFFFFFF, r[R_(ops[-1])] & 0xFFFFFFFF)
        elif mn == 'cmplwi':
            f = int(ops[0].replace('cr', '')) if len(ops) == 3 else 0
            self.setcr(f, r[R_(ops[-2])] & 0xFFFFFFFF, imm(ops[-1]))
        elif mn in ('cmpld', 'cmpldi'):
            f = int(ops[0].replace('cr', '')) if len(ops) == 3 else 0
            self.setcr(f, r[R_(ops[-2])] & M64, r[R_(ops[-1])] & M64 if mn == 'cmpld' else imm(ops[-1]))
        elif mn == 'sc': nxt = self.syscall(pc)
        elif mn == 'stb':
            d, ra = memop(ops[1]); self.m.w((r[ra] + d) & M64, 1, r[R_(ops[0])])
        elif mn == 'andi.':
            r[R_(ops[0])] = r[R_(ops[1])] & imm(ops[2]); self.setcr(0, sx(r[R_(ops[0])], 64), 0)
        elif mn == 'srdi': r[R_(ops[0])] = r[R_(ops[1])] >> imm(ops[2])
        elif mn == 'rldicl':
            v, sh, mb = r[R_(ops[1])], imm(ops[2]), imm(ops[3])
            r[R_(ops[0])] = (((v << sh) | (v >> (64 - sh))) & M64 if sh else v) & (M64 >> mb)
        elif mn == 'ble':
            f = int(ops[0].replace('cr', '')) if len(ops) == 2 else 0
            if self.cr[f] != 4: nxt = imm(ops[-1])
        elif mn == 'bgt':
            f = int(ops[0].replace('cr', '')) if len(ops) == 2 else 0
            if self.cr[f] == 4: nxt = imm(ops[-1])
        else:
            raise RuntimeError(f'unimplemented {mn} {ins.op_str} at {pc:#x}')
        return nxt


def run(entry, poll, home_team, away_team, out_obj=0x40008000, keys=None):
    m = Mem()
    home, away, hl, al = R.build()
    m.write(R.HOME, home); m.write(R.AWAY, away)
    names = {home_team: 'DUKE', away_team: 'KANSAS'}
    for i, (t, n) in enumerate(names.items()):
        sp = DATA + 0x1000 + i * 0x100
        m.write(sp, n.encode('utf-16-be') + b'\0\0'); m.w(t + 4, 4, sp)
    for ptr, key in (keys or {}).items():
        m.w(ptr + R.KEY, 2, key)
    cpu = CPU(m, None)
    cpu.r[1], cpu.r[2], cpu.r[3], cpu.lr = STACK, MAIN_TOC, out_obj, RET
    for n in range(14, 32):
        cpu.r[n] = 0x1111000000000000 + n
    nodes, chains, st = {}, {}, {'next': HEAP, 'out': None, 'err': [], 'formats': 0}
    permanent = (R.AWAY, R.AWAY_END)
    INT_T, STR_T = 0xA18CA0, 0xA18CD8                  # real descriptor values in the TOC
    m.w(MAIN_TOC + R.TOC_INT_TYPE, 4, INT_T); m.w(MAIN_TOC + R.TOC_STR_TYPE, 4, STR_T)
    templates = {R.FMT_RANK: '#{0}', R.FMT_PAIR: '{0} {1}'}

    def text(p):
        s = b''
        while m.read(p, 2) != b'\0\0':
            s += m.read(p, 2); p += 2
        return s.decode('utf-16-be')

    def full(n):
        return nodes[n] + ''.join(full(c) for c in chains.get(n, []))

    def stub(name):
        if cpu.r[2] != MAIN_TOC: st['err'].append(f'{name} entered with r2={cpu.r[2]:#x}')
        m.w(cpu.r[1] + 0x28, 8, cpu.r[2]); cpu.r[2] = LIB_TOC   # real stubs clobber r2

    pc, steps = entry, 0
    while pc != RET:
        steps += 1
        if steps > 20000: st['err'].append('runaway'); break
        r3, r4 = cpu.r[3] & 0xFFFFFFFF, cpu.r[4] & 0xFFFFFFFF
        if pc in (R.GET_HOME, R.GET_AWAY):
            cpu.r[3] = home_team if pc == R.GET_HOME else away_team; pc = cpu.lr; continue
        if pc == R.POLL_ENTRY:
            if r3 != 0: st['err'].append('poll mode not media')
            cpu.r[3] = poll[r4] if r4 < len(poll) else 0
            for v in (0, 4, 5, 6, 7, 8, 9, 10, 11, 12): cpu.r[v] = 0xBAD0 + v if v not in (3,) else cpu.r[3]
            pc = cpu.lr; continue
        if pc == R.STR_FROM:
            stub('STR_FROM')
            if cpu.r[5] & 0xFFFFFFFF != 0xFFFFFFFF: st['err'].append('length not -1')
            ok = permanent[0] <= r4 < permanent[1] or r4 in (DATA + 0x1000, DATA + 0x1100)
            if not ok: st['err'].append(f'text {r4:#x} is not permanent')
            node = st['next']; st['next'] += 0x10; nodes[node] = text(r4); m.w(r3, 4, node)
            pc = cpu.lr; continue
        if pc == R.FORMAT:
            stub('FORMAT'); st['formats'] += 1
            fmt = m.u(r4, 4); hdr = cpu.r[5] & 0xFFFFFFFF
            if cpu.r[6] & 0xFFFFFFFF: st['err'].append('FORMAT r6 not 0')
            if m.u(hdr, 4) != 0: st['err'].append('arg header word 0 not 0')
            count = m.u(hdr + 4, 4); vals = []
            for i in range(count):
                e = hdr + 8 + 12 * i
                if m.u(e, 4) != 0: st['err'].append(f'arg {i} word 0 not 0')
                ptr, typ = m.u(e + 4, 4), m.u(e + 8, 4)
                if typ == INT_T: vals.append(str(m.u(ptr, 4)))
                elif typ == STR_T: vals.append(full(m.u(ptr, 4)))
                else: st['err'].append(f'arg {i} unknown type {typ:#x}'); vals.append('?')
            if fmt not in templates: st['err'].append(f'unknown template {fmt:#x}')
            out = templates.get(fmt, '?').format(*vals)
            node = st['next']; st['next'] += 0x10; nodes[node] = out
            if r3 == out_obj: st['out'] = out
            else: m.w(r3, 4, node)
            pc = cpu.lr; continue
        if pc == R.STR_ASSIGN:
            stub('STR_ASSIGN'); st['out'] = full(m.u(r4, 4)); pc = cpu.lr; continue
        if pc == R.STR_FREE:
            stub('STR_FREE'); pc = cpu.lr; continue
        if not (R.HOME <= pc < R.HOME_END or R.AWAY <= pc < R.AWAY_END):
            st['err'].append(f'jumped outside patch to {pc:#x}'); break
        pc = cpu.step(pc)
    for n in range(14, 32):
        if cpu.r[n] != 0x1111000000000000 + n: st['err'].append(f'r{n} clobbered')
    if cpu.r[1] != STACK: st['err'].append('r1 not restored')
    if cpu.r[2] != MAIN_TOC: st['err'].append('r2 not restored')
    st['steps'] = steps
    return st


if __name__ == '__main__':
    # Scorebug teams are per-game copies; the poll holds roster records: same ID, different address.
    H, A = DATA + 0x100, DATA + 0x200                  # game-team copies
    RH, RA = DATA + 0x4000, DATA + 0x4400              # roster records
    base = [DATA + 0x800 + 0x200 * i for i in range(25)]
    keys = {H: 216, A: 322, RH: 216, RA: 322}
    keys.update({b: 1000 + i for i, b in enumerate(base)})
    base[3] = 0; base[20] = 0                          # empty poll slots
    p1 = base[:]; p1[4] = RH; p1[12] = RA
    p2 = base[:]; p2[0] = RA; p2[24] = RH
    cases = [('home ranked #5', R.HOME, p1, '#5 DUKE'), ('away ranked #13', R.AWAY, p1, '#13 KANSAS'),
             ('home unranked', R.HOME, base, 'DUKE'), ('away unranked', R.AWAY, base, 'KANSAS'),
             ('away ranked #1', R.AWAY, p2, '#1 KANSAS'), ('home ranked #25', R.HOME, p2, '#25 DUKE'),
             ('home ranked #10', R.HOME, base[:9] + [RH] + base[10:], '#10 DUKE')]
    zero = {**keys, H: 0}                              # copy without an ID must not match ID-0 teams
    zpoll = base[:]; zpoll[2] = DATA + 0x6000; zero[DATA + 0x6000] = 0
    st = run(R.HOME, zpoll, H, A, keys=zero)
    good0 = st['out'] == 'DUKE' and not st['err']
    print(f"{'PASS' if good0 else 'FAIL'} ID 0 never matches -> {st['out']!r}", st['err'] or '')
    ok = True
    for name, e, poll, want in cases:
        st = run(e, poll, H, A, keys=keys)
        good = st['out'] == want and not st['err']; ok &= good
        print(f"{'PASS' if good else 'FAIL'} {name:16s} -> {st['out']!r:14s} ({st['steps']} steps)", st['err'] or '')
    st = run(R.HOME, p1, H, A, out_obj=0, keys=keys)
    good = st['out'] is None and not st['err']; ok &= good
    print(f"{'PASS' if good else 'FAIL'} null output slot -> no assignment", st['err'] or '')
    sys.exit(0 if ok else 1)
