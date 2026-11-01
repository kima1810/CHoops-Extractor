"""DEBUG probe entry: which Selection Show commentary/widget value functions run, and from where."""
import re
import probe_asm as P

PATCH = r'D:/RPCS3 2026/patches/imported_patch.yml'
TITLE = 'DEBUG probes: Selection Show commentary -> TTY.log'
# 0x5E925C / 0x5E9274 (event 90 play-in teams) are Stage 2 caves since v2.2, so not probed here.
PROBES = [('SGT2', 0x5E91F0, 'plain'),   # current segment game, team 2
          ('STM2', 0x5E9A48, 'plain'),   # widget/speech value: team 2
          ('SPV1', 0x5E9AA4, 'plain'),   # widget/speech value: play-in team 1
          ('SPV2', 0x5E9B00, 'plain'),   # widget/speech value: play-in team 2
          ('SSED', 0x5EA8E8, 'plain'),   # speech token: featured team seed
          ('SFOC', 0x5E928C, 'plain'),   # featured team lookup
          ('SVAR', 0x564D28, 'index'),   # speech variable id (r3)
          ('TOKN', 0x573B64, 'index'),   # speech token value lookup (r3 = token id)
          ('FACT', 0x77F670, 'regs'),    # director fact provider: r3, r4 = fact id, r5 (64-bit each)
          ('FRES', 0x5BBE0, 'slot'),     # value the fact provider wrote (evaluator stack slot)
          ('FAC2', 0x77F798, 'regs'),    # parameterised fact provider (evaluator opcode 2): r3, r4 = fact id, r5
          ('FAR2', 0x77F79C, 'r5'),      # its argument value (the popped 0x20-byte slot at r5)
          ('FRS2', 0x5BC74, 'slot'),     # value it wrote
          ('SPIX', 0x652A0, 'regs'),     # phrase -> stream resolver: r3 engine, r4/r5 lookup keys
          ('SPCK', 0x6519C, 'regs')]     # candidate stream check: r3 engine, r4 = stream index
# 0x5BABC (condition evaluator entry) is a Stage 2 cave since v2.6, so it is not probed here.

# Pointer setup for the dump probes: 'regs' dumps the saved r3-r5, 'slot' the evaluator
# stack slot [r30] + 0x20 * [[TOC-0x7440]] that 0x5BABC hands to the fact provider.
PRE = {'regs': '    addi 7, 1, 0x88' + chr(10), 'r5': '    ld 7, 0x98(1)' + chr(10),
       'slot': chr(10).join(['    lwz 7, 0(30)', '    lwz 8, -0x7440(2)', '    lwz 8, 0(8)', '    slwi 8, 8, 5',
                             '    add 7, 7, 8']) + chr(10)}

if __name__ == '__main__':
    lines = [f'  "{TITLE}":', '    Games:', '      "College Hoops 2K8":', '        BLUS30078: [ All ]',
             '    Author: "Claude Code"',
             '    Notes: "Diagnostic only. Logs Selection Show commentary and widget value calls to log/TTY.log. Leave disabled normally."',
             '    Patch Version: 1.9', '    Patch:']
    for tag, addr, mode in PROBES:
        code = P.build(tag, addr, index=mode == 'index', bt=mode == 'bt', dump=mode in ('dump', 'regs', 'slot', 'r5'),
                       pre=PRE.get(mode))
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
    print('probe lines', sum(1 for l in block.splitlines() if 'be32' in l))
