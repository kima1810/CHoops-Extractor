import struct
class Binary:
    def __init__(self, data): self.data = data
    def slice(self, offset, size):
        if offset < 0 or size < 0 or offset + size > len(self.data): raise ValueError(f"Out of bounds: {offset}+{size}/{len(self.data)}")
        return self.data[offset:offset+size]
    def u32(self, offset, endian=">"): return struct.unpack(endian+"I", self.slice(offset,4))[0]
    def u16(self, offset, endian=">"): return struct.unpack(endian+"H", self.slice(offset,2))[0]
    def relative(self, offset, endian=">"):
        value=self.u32(offset,endian)
        if not value: raise ValueError("Null relative pointer")
        return relative_target(offset,value)
    def utf16(self, offset, endian="le"):
        end=offset
        while self.slice(end,2) != b"\0\0": end+=2
        return self.slice(offset,end-offset).decode("utf-16-"+endian)
def relative_target(field,value): return field+value-1
def relative_value(field,target): return target-field+1
