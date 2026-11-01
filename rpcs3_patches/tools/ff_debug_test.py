import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import first_four_test as T, first_four_asm as F
out = []
def sc(self, pc):
    assert self.r[11] == 403
    out.append(self.m.read(self.r[4], self.r[5]).decode()); return pc + 4
T.CPU2.syscall = sc
ok = True
for name, types, want in (('success', None, 'FF4 ee'), ('stock field (61 direct teams)', 'stock', 'FF4 06')):
    w = T.World(); out.clear()
    if types is None:
        ty = [0 if (i % 3) else 1 for i in range(59)] + [1, 1, 2, 2, 2, 2]; ty[58] = 0
    else:
        ty = [0] * 63 + [2, 2]
    w.field([(T.team(i), ty[i], 900 - i) for i in range(65)])
    w.table(T.CAND, [T.team(i) for i in range(65) if ty[i] == 0] + [T.team(200 + k) for k in range(60)])
    w.table(T.NIT, [T.team(201)] + [T.team(210 + k) for k in range(31)])
    how, cpu, start, err = w.run(F.build_builder(debug=True))
    bad = [k for k in range(13, 32) if cpu.r[k] != start[k]]
    good = out and out[0].startswith(want) and len(out[0]) == 4 + 15 + 65 + 1 and not err and not bad
    good &= (how == 0x50000000 and len(w.calls) == 12) if types is None else (how == 'END' and not w.calls)
    ok &= bool(good); print('PASS' if good else 'FAIL', name, repr(out[0] if out else None), err, bad)
sys.exit(0 if ok else 1)
