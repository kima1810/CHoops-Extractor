"""Add (or replace) the First Four entries in the RPCS3 patch file: the normal one and a DEBUG copy."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import first_four_asm as F
import first_four_tree_asm as G

PATCH = r'D:/RPCS3 2026/patches/imported_patch.yml'
NAME = 'NCAA Tournament: 68 teams with a four-game First Four (Stage 1)'
NOTES = ("Code caves (RPCS3 calloc). Selection (0x5C1D30, and the projection screen 0x5BFCDC) makes the four lowest "
         "automatic bids play-in teams; the NIT fill (0x5C2124) leaves out the three best teams outside the field, who "
         "join the last at-large team in the at-large games. The bracket builder (0x590084) is replaced: event 90 "
         "(two lowest autos, Tuesday) feeds East 16, and the finished 2K Sports Classic first-round events 2, 3 and 4 "
         "become South 16 (autos, Tuesday), Midwest 11 and West 11 (at-large, Wednesday) through link-table rows 0-2 "
         "(restored when events 2-4 are next built or finished as holiday events: 0x58F848, 0x58F310). While they hold a play-in game, events 2-4 read the event 90 record "
         "(name, schedule config) at 0x58C270, 0x58F234, 0x58F600, 0x58F700 and 0x58F8A4. NCAA appearances "
         "(0x5C19E0) come from the built bracket, so all 68 teams are credited, play-in teams with the seed of the "
         "slot their game feeds. If the field does not have four play-in teams the stock builder runs. Enable before "
         "Selection Sunday of a new season. The tournament bracket screen still shows only the event 90 play-in game.")
DEBUG_NAME = NAME.replace('(Stage 1)', '(Stage 1, DEBUG report to TTY.log)')
DEBUG_NOTES = ("Same as the Stage 1 entry (enable only one of the two). The bracket builder also writes one line to "
               "log/TTY.log on Selection Sunday: 'FF4 <stage> <r21> <r27> <r22> <r9> <65 field types>'. Stage ee = four "
               "play-in games built; 01-0a = the check that sent it to the stock builder.")


TREE_NAME = 'NCAA Tournament: First Four on the Tournament Tree (Stage 2)'
TREE_NOTES = ("Needs the Stage 1 entry. The tree's NCAA pages already include First Four events 2-4 (before the stock "
              "play-in, event 90). The NCAA tree's play-in box (0x65A548) shows the open First Four page's game; on a First Four page LT/RT step from the page (0x65FD60, 0x65FE98) and on arrival the bracket is redrawn for the page and the cursor put on the play-in box (0x65A264), so all four play-in pages can be reached. These caves also extend the screen's event 90 special cases: no seeds on the "
              "play-in pages (0x65DC28, 0x65DCA0), and 'PLAY-IN GAME WINNER' (text 0x65DF24, Legacy TBD paths 0x65DE88 and 0x65DEE0, box style 0x65E7F4) in "
              "every regional first-round slot a First Four game feeds (East 16, South 16, Midwest 11, West 11) "
              "instead of only East 1-16.")


def entry(name, notes, debug, blocks=None, version='1.2'):
    lines = [f'  "{name}":', '    Games:', '      "College Hoops 2K8":', '        BLUS30078: [ All ]',
             '    Author: "Claude Code"', f'    Notes: "{notes}"', f'    Patch Version: {version}', '    Patch:']
    for hook, code, what in (blocks if blocks is not None else F.blocks(debug=debug)):
        words = [int.from_bytes(code[i:i + 4], 'big') for i in range(0, len(code), 4)]
        lines.append(f'      - [ calloc, 0x{hook:08x}, {len(words)} ] # {what}')
        lines += [f'      - [ be32, 0x{hook:08x}, 0x{w:08x} ]' for w in words]
    return '\n'.join(lines) + '\n'


def put(text, name, body):
    start = text.find(f'  "{name}":')
    if start < 0:
        return text.rstrip('\n') + '\n' + body
    nxt = text.find('\n  "', start + 4)
    return text[:start] + body + (text[nxt + 1:] if nxt >= 0 else '')


text = open(PATCH, encoding='utf-8').read()
text = put(text, NAME, entry(NAME, NOTES, False))
text = put(text, DEBUG_NAME, entry(DEBUG_NAME, DEBUG_NOTES, True))
text = put(text, TREE_NAME, entry(TREE_NAME, TREE_NOTES, False, G.blocks(), '1.7'))
text = text.replace("# conference member order, and a 30-second shot clock.",
                    "# conference member order, a 30-second shot clock, and a 68-team NCAA field\n# with a four-game First Four.")
open(PATCH, 'w', encoding='utf-8', newline='\n').write(text)
print('wrote:', NAME, '|', DEBUG_NAME, '|', TREE_NAME)
