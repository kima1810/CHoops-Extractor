"""Add/replace the DEBUG probe entry in the RPCS3 patch file."""
import re, yaml
import probe_asm as P

PATCH = r'D:/RPCS3 2026/patches/imported_patch.yml'
TITLE = 'DEBUG probes: team name functions -> TTY.log'
PROBES = [('GTEA', 0x1BBB58, 'index')]   # library getTeam(index): logs caller + requested team index

lines = [f'  "{TITLE}":', '    Games:', '      "College Hoops 2K8":', '        BLUS30078: [ All ]',
         '    Author: "Claude Code"',
         '    Notes: "Diagnostic only. Each probed function writes \'TAG caller-address\' to log/TTY.log when it runs. Leave disabled normally."',
         '    Patch Version: 1.0', '    Patch:']
for tag, addr, mode in PROBES:
    code = P.build(tag, addr, text=mode == 'text', index=mode == 'index')
    words = [int.from_bytes(code[i:i + 4], 'big') for i in range(0, len(code), 4)]
    lines.append(f'      - [ calloc, 0x{addr:08x}, {len(words)} ] # {tag}')
    lines += [f'      - [ be32, 0x{addr:08x}, 0x{w:08x} ]' for w in words]
block = '\n'.join(lines) + '\n'

txt = open(PATCH, encoding='utf-8').read()
if f'  "{TITLE}":' in txt:
    i = txt.index(f'  "{TITLE}":'); m = re.compile(r'^  "', re.M).search(txt, i + 5)
    txt = txt[:i] + block + txt[m.start() if m else len(txt):]
else:
    txt = txt.rstrip('\n') + '\n' + block
open(PATCH, 'w', encoding='utf-8', newline='\n').write(txt)
d = yaml.safe_load(open(PATCH, encoding='utf-8'))
root = [k for k in d if k.startswith('PPU')][0]
e = d[root][TITLE]['Patch']
print('entries', len(d[root]), 'probe lines', len(e), 'callocs', sum(x[0] == 'calloc' for x in e))
