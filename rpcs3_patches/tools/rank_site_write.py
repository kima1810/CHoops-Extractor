"""Write the call-site rank entries into the RPCS3 patch file and drop the probe entry."""
import re, sys, yaml
import rank_site_asm as S

P = r'D:/RPCS3 2026/patches/imported_patch.yml'
PROBE = 'DEBUG probes: team name functions -> TTY.log'
ENTRIES = {
    'teamselect': ('Team names: poll rank on short name (Team Select: #6 ILLINOIS)',
                   "Code cave (RPCS3 calloc) at the Legacy Team Select screen's short-name STR_FROM call (0x6E42D8 in 0x6E3FE4, found with a TTY probe). The block makes the call itself; if the text pointer is the short name of a team in the current media poll the name becomes '#N <short name>'. Other text reaching this call (path from 0x6E4724) is left alone."),
    'matchup': ('Pregame matchup card: poll rank (#6 Fighting Illini (13-0))',
                "Code cave (RPCS3 calloc) at the pregame matchup card's mascot STR_FROM call (0x70EEEC in 0x70EE00, found with a TTY probe; team in r28). If the team is in the current media poll (matched by team ID +0x15E) the mascot becomes '#N <mascot>'."),
}


def block(site, debug):
    title, notes = ENTRIES[site]
    addr, _, nop, _, _ = S.SITES[site]
    code = S.build(site, debug=debug)
    words = [int.from_bytes(code[i:i + 4], 'big') for i in range(0, len(code), 4)]
    out = [f'  "{title}":', '    Games:', '      "College Hoops 2K8":', '        BLUS30078: [ All ]',
           '    Author: "Claude Code"', '    Notes: "' + notes.replace('"', "'") + '"',
           '    Patch Version: ' + ('"1.1 debug"' if debug else '1.1'), '    Patch:',
           f'      - [ calloc, 0x{addr:08x}, {len(words)} ]']
    out += [f'      - [ be32, 0x{addr:08x}, 0x{w:08x} ]' for w in words]
    if nop:
        out.append(f'      - [ be32, 0x{nop:08x}, 0x60000000 ] # original STR_FROM call (made inside the block) -> nop')
    return '\n'.join(out) + '\n', words


def cut(txt, title):
    i = txt.index(f'  "{title}":'); m = re.compile(r'^  "', re.M).search(txt, i + 5)
    return txt[:i], txt[m.start() if m else len(txt):]


txt = open(P, encoding='utf-8').read()
if f'  "{PROBE}":' in txt:
    a, b = cut(txt, PROBE); txt = a + b
for site in ENTRIES:
    blk, _ = block(site, '--debug' in sys.argv)
    a, b = cut(txt, ENTRIES[site][0]); txt = a + blk + b
open(P, 'w', encoding='utf-8', newline='\n').write(txt.rstrip('\n') + '\n')
d = yaml.safe_load(open(P, encoding='utf-8')); root = [k for k in d if k.startswith('PPU')][0]
for site in ENTRIES:
    e = d[root][ENTRIES[site][0]]['Patch']; _, words = block(site, '--debug' in sys.argv)
    assert e[0] == ['calloc', S.SITES[site][0], len(words)] and [x[2] for x in e[1:1 + len(words)]] == words
    print(site, 'ok', len(words), 'words', 'nop' if S.SITES[site][2] else '')
print('entries', len(d[root]), 'probe present', PROBE in d[root])
