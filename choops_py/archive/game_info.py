"""Read optional PS3 PARAM.SFO display identity; never use it to guess a TOC."""
import struct


def read_identity(path):
    file = path.parent/'PARAM.SFO'
    if not file.is_file() or file.stat().st_size > 1024*1024:
        return {}
    try:
        raw = file.read_bytes()
        magic, version, keys, values, count = struct.unpack_from('<5I', raw)
        if magic != 0x46535000 or count > 4096 or 20+count*16 > keys or keys > values:
            return {}
        result = {}
        for i in range(count):
            key, fmt, length, maximum, offset = struct.unpack_from('<HHIII', raw, 20+i*16)
            start = keys+key
            end = raw.find(b'\0', start, values)
            if not keys <= start < end < values or length > maximum or values+offset+maximum > len(raw):
                return {}
            name = raw[start:end].decode('utf8')
            if name in ('TITLE', 'TITLE_ID') and fmt == 0x0204:
                result[name] = raw[values+offset:values+offset+length].rstrip(b'\0').decode('utf8')
        return result
    except (OSError, ValueError, struct.error):
        return {}
