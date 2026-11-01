import struct
from .binary import Binary
def unwrap(data):
    b=Binary(data)
    if b.u32(0)!=0x326b546c: raise ValueError("Not a 2kTl wrapper")
    header=b.u32(4);typ=b.u16(8);n=b.u16(10)
    if header!=12+4*n: raise ValueError("Invalid wrapper header size")
    pos=header;blocks=[]
    for i in range(n):
        size=b.u32(12+i*4);blocks.append(b.slice(pos,size));pos+=size
    if pos!=len(data): raise ValueError("Trailing wrapper bytes")
    return typ,blocks
def wrap(typ,blocks):
    typ=int(typ,0) if isinstance(typ,str) else typ
    if not 0<=typ<=65535 or len(blocks)>65535:raise ValueError("Wrapper type/count out of range")
    return struct.pack('>IIHH',0x326b546c,12+4*len(blocks),typ,len(blocks))+b''.join(struct.pack('>I',len(b)) for b in blocks)+b''.join(blocks)
