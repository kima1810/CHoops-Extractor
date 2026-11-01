"""Conference menu-logo naming established by read-only executable tracing."""


def logo_record(index):
    # Menu helpers 0x6A0734 / 0x6E7120 pass 900 + selected conference index
    # to 0x7FD80's logo%3d formatter. This is not conference row +0x1A.
    if type(index) is not int or not 0 <= index < 39:
        raise ValueError('Conference logo routing is established only for stock indices 0..38')
    return f'logo{900 + index:03d}'
