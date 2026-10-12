"""AUSB stream tables pair cumulative byte boundaries with duration values."""
import math
import re
import struct
from ..formats.binary import Binary
from .codec import playback_samples


class StreamBank:
    def __init__(self,metadata,data_size):
        self.metadata=metadata;b=Binary(metadata);b.slice(0,96)
        match=re.match(r'([a-zA-Z0-9_-]+\.bin)',b.slice(0,64).decode('utf-16-be'),re.I)
        if not match:raise ValueError('AUSB stream filename is not recognized')
        self.filename=match[1];self.count=b.u32(64);self.rate=b.u32(76);fmt=b.u32(84)
        if not 0<self.count<=100000 or fmt not in (14,15) or not 8000<=self.rate<=192000:raise ValueError('Unsupported AUSB stream parameters')
        self.channels=1 if fmt==14 else 2;b.slice(88,(self.count+1)*8)
        self.offsets=[b.u32(92+i*8) for i in range(self.count+1)]
        self.durations=[struct.unpack_from('>f',metadata,96+i*8)[0] for i in range(self.count)]
        if self.offsets!=sorted(self.offsets) or self.offsets[-1]>data_size:raise ValueError('AUSB stream boundaries exceed the audio bank')
        if any(not math.isfinite(d) or d<0 for d in self.durations):raise ValueError('AUSB duration is invalid')

    def info(self,index):
        if not 0<=index<self.count:raise ValueError('Audio stream index is out of range')
        size=self.offsets[index+1]-self.offsets[index]
        samples=playback_samples(size,self.channels,self.rate,self.durations[index]*self.rate)
        return dict(index=index,codec='ATRAC3',channels=self.channels,sample_rate=self.rate,encoded_bytes=size,
                    samples=samples,seconds=samples/self.rate,stored_seconds=self.durations[index])

    def replace(self,data,changes):
        head=bytearray(self.metadata);out=bytearray(data[:self.offsets[0]])
        if any(index not in range(self.count) for index in changes):raise ValueError('Invalid replacement stream index')
        for i in range(self.count):
            struct.pack_into('>I',head,92+i*8,len(out))
            if i in changes:
                encoded,samples=changes[i]
                if samples<=0 or len(encoded)%(152*self.channels) or len(encoded)//(152*self.channels)*1024-2048<samples:
                    raise ValueError('Invalid encoded stream replacement')
                duration=samples/self.rate;struct.pack_into('>f',head,96+i*8,duration)
                if i==0:struct.pack_into('>f',head,88,duration)
                out+=encoded
            else:out+=data[self.offsets[i]:self.offsets[i+1]]
        struct.pack_into('>I',head,92+self.count*8,len(out));out+=data[self.offsets[-1]:]
        result=bytes(head);payload=bytes(out);check=StreamBank(result,len(payload))
        for i in range(self.count):
            expected=changes[i][0] if i in changes else data[self.offsets[i]:self.offsets[i+1]]
            if payload[check.offsets[i]:check.offsets[i+1]]!=expected:raise ValueError('Audio bank rebuild changed another stream')
        return result,payload
