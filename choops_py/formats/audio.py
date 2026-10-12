"""Bounds-checked 36-byte PS3 AUDO header and ATRAC3 payload layout."""
import struct
from .binary import Binary
from .tool_wrapper import unwrap
from ..audio_tools.codec import playback_samples


def parts_from_bytes(data):
    if data[:4]==b'2kTl':return unwrap(data)[1]
    if len(data)<36:raise ValueError('AUDO requires a 36-byte header and encoded payload')
    return [data[:36],data[36:]]


def info(parts):
    if len(parts)==1:parts=parts_from_bytes(parts[0])
    if len(parts)!=2:raise ValueError('AUDO requires header and payload blocks')
    b=Binary(parts[0]);b.slice(0,36)
    if b.u32(0)!=1 or b.u32(4)!=5 or b.u32(8) not in (14,15):raise ValueError('Unsupported AUDO codec/header; raw preservation remains available')
    channels=1 if b.u32(8)==14 else 2;rate=b.u32(16);size=b.u32(24)
    if not 8000<=rate<=192000 or size>len(parts[1]):raise ValueError('Invalid AUDO rate or payload bounds')
    samples=playback_samples(size,channels,rate,b.u32(12))
    return dict(codec='ATRAC3',codec_id=5,playback_format=b.u32(8),channels=channels,sample_rate=rate,
                encoded_bytes=size,samples=samples,stored_samples=b.u32(12),seconds=samples/rate,
                flags=b.u32(20),loop_start=b.u32(28),loop_end=b.u32(32))


def replace(parts,encoded,samples):
    inline=len(parts)==1;source=parts_from_bytes(parts[0]) if inline else parts;metadata=info(source)
    physical=playback_samples(len(encoded),metadata['channels'],metadata['sample_rate'])
    if not isinstance(samples,int) or not 0<samples<=physical:raise ValueError('Invalid AUDO replacement sample extent')
    if metadata['flags'] or metadata['loop_start'] or metadata['loop_end']:
        raise ValueError('Looped AUDO replacement requires confirmed loop routing; export is supported')
    head=bytearray(source[0]);struct.pack_into('>I',head,12,samples);struct.pack_into('>I',head,24,len(encoded))
    result=[bytes(head),encoded+source[1][metadata['encoded_bytes']:]];info(result)
    return [b''.join(result)] if inline else result


def inspect(data):return info(parts_from_bytes(data))
