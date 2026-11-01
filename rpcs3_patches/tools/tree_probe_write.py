"""DEBUG probe entry for the Tournament Tree page navigation (First Four Stage 2)."""
import re
import yaml
import probe_asm as P

PATCH = r'D:/RPCS3 2026/patches/imported_patch.yml'
TITLE = 'DEBUG probes: Tournament Tree pages -> TTY.log'
# 'pair' logs (r3 & 0xFF) << 8 | (r4 & 0xFF) as four hex digits: category/event or category/position
PAIR_SRC = P.IDX_SRC.replace('    ld 8, 0x88(1)\n', '''    ld 8, 0x88(1)
    andi. 8, 8, 0xff
    slwi 8, 8, 8
    ld 12, 0x90(1)
    andi. 12, 12, 0xff
    or 8, 8, 12
''')
assert PAIR_SRC != P.IDX_SRC
PROBES = [('TCNT', 0x58BDB0, 'index'),   # category event count (r3 = category)
          ('TITH', 0x58BE24, 'pair'),    # i-th event of category (category, i)
          ('TNXT', 0x6597A4, 'pair'),    # next page (category, current event)
          ('TPRV', 0x659818, 'pair'),    # previous page (category, current event)
          ('TLBL', 0x65DF58, 'plain')]   # PLAY-IN GAME WINNER label drawn


def build(tag, addr, mode):
    if mode == 'pair':
        saved = P.IDX_SRC; P.IDX_SRC = PAIR_SRC
        try:
            return P.build(tag, addr, index=True)
        finally:
            P.IDX_SRC = saved
    return P.build(tag, addr, index=mode == 'index')


if __name__ == '__main__':
    lines = [f'  "{TITLE}":', '    Games:', '      "College Hoops 2K8":', '        BLUS30078: [ All ]',
             '    Author: "Claude Code"',
             '    Notes: "Diagnostic only. Logs Tournament Tree page counting / next / previous calls and the play-in label to log/TTY.log. Leave disabled normally."',
             '    Patch Version: 1.0', '    Patch:']
    for tag, addr, mode in PROBES:
        code = build(tag, addr, mode)
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
    print('entries', len(d[root]), 'probe lines', len(d[root][TITLE]['Patch']))
