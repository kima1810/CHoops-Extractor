"""Small case-sensitive CRC dictionary for shared 2K internal asset labels.

Only used when no authored/export name table exists. Unknown IDs stay numeric;
these labels do not imply that unknown record types have been reversed.
"""
import zlib

_names = {'arena', 'floor', 'floor_lines', 'cloth', 'cloth_shorts', 'mascot',
          'unif', 'unifregion', 'short', 'shortregion', 'names', 'jersey_numbers',
          'logo', 'unidata', 'jerseynum00', 'jerseyname00', 'hi_shoe1',
          'scorebug_bottombar', 'scorebug_topbar', 'scorebug_blackbar'}
for shape in ('u', 'v', 'vtri', 'tri', 'wishbone'):
    for build in ('thin', 'reg', 'fat'):
        _names.add(f'jersey_{shape}_{build}')
for build in ('thin', 'reg', 'fat'):
    _names.add('shorts'+build)
for index in range(1024):
    _names.add(f'logo{index:03d}')
_labels = {zlib.crc32(name.encode('ascii')) & 0xffffffff: name for name in _names}
if len(_labels) != len(_names):
    raise ValueError('Ambiguous internal record label dictionary')


def label(identity, fallback):
    return _labels.get(identity, fallback)
