from .binary import Binary
from ..archive.manifests import safe_name, write_bytes, report
MAGIC=0xFF3BEF94
TYPES={0x5C369069:"TXTR",0xE26C9B5D:"SCNE",0x86A1AC9E:"LAYT",0xC61649B2:"ROST",0x1AEDDA1F:"AUDO",0x68B693B2:"NAME",0xA7701F00:"CDAN"}
TYPES[0x61df2234]='AUSB'
def names(data,offset,count):
    b=Binary(data)
    if offset+8>len(data) or b.u32(offset)!=0xAA171516: return []
    body=Binary(b.slice(offset+8,b.u32(offset+4,"<")))
    n=body.u32(0,"<"); table=body.relative(4,"<"); result=[]
    for i in range(min(n,count)):
        entry=body.relative(table+i*4,"<")
        result.append((body.utf16(body.relative(entry,"<")),body.utf16(body.relative(entry+4,"<"))))
    return result
from .compression import decode as decompress
class StandardIFF:
    def __init__(self,data):
        self.raw=data;b=Binary(data)
        if b.u32(0)!=MAGIC: raise ValueError("Not a standard PS3 IFF")
        self.header_size=b.u32(4);self.file_length=b.u32(8);bc=b.u32(16);fc=b.u32(24)
        if not 32<=self.header_size<=self.file_length<=len(data): raise ValueError("Invalid IFF boundaries")
        b.slice(32,bc*32+fc*4);self.blocks=[];self.records=[]
        for i in range(bc):
            off=32+i*32;values=[b.u32(off+j*4) for j in range(8)]
            start,size=values[5:7]
            if start<self.header_size or start+size>self.file_length: raise ValueError("Invalid block range")
            self.blocks.append(dict(index=i,fields=values,start=start,size=size,logical_size=values[3],compressed=data[start:start+4]==bytes.fromhex('0e4837c3')))
        ns=names(data,self.file_length,fc)
        for i in range(fc):
            field=32+bc*32+i*4;off=b.relative(field);n=b.u32(off+8)
            if off<32+bc*32+fc*4 or off+12+n*4>self.header_size or n>bc: raise ValueError("Invalid file record")
            offsets=[b.u32(off+12+j*4) for j in range(n)]
            for j,v in enumerate(offsets):
                if v!=0xffffffff and v>self.blocks[j]['logical_size']: raise ValueError("Subfile offset out of bounds")
            name,typ=ns[i] if i<len(ns) else (str(i),TYPES.get(b.u32(off+4),'UNKNOWN'))
            self.records.append(dict(index=i,name=name,type=typ,id=b.u32(off),type_hash=b.u32(off+4),offsets=offsets))
    def manifest(self): return dict(family='standard-iff',header_size=self.header_size,file_length=self.file_length,blocks=self.blocks,records=self.records)
    def spans(self,record):
        if not hasattr(self, '_span_ends'):
            self._span_ends = []
            for j, block in enumerate(self.blocks):
                offsets = sorted({r['offsets'][j] for r in self.records
                                  if len(r['offsets']) > j and r['offsets'][j] != 0xffffffff})
                ends = offsets[1:] + [block['logical_size']]
                self._span_ends.append(dict(zip(offsets, ends)))
        for j, start in enumerate(record['offsets']):
            if start != 0xffffffff:
                yield j, start, self._span_ends[j][start]
    def dump(self,output,types=()):
        decoded={};items=[]
        for r in self.records:
            if types and r['type'] not in types: continue
            for j,start,end in self.spans(r):
                block=self.blocks[j]
                if j not in decoded: decoded[j]=decompress(self.raw[block['start']:block['start']+block['size']],block['logical_size'])
                name=f"{r['index']:04d}_{safe_name(r['name'])}.{r['type'].lower()}.block{j}"
                write_bytes(output/name,decoded[j][start:end]);items.append(name)
        report(output/'manifest.json',self.manifest());return items
    def replace(self,selector,payload):
        matches=[r for r in self.records if str(r['index'])==selector or r['name']==selector]
        if len(matches)!=1: raise ValueError("Subfile selector must match exactly one record")
        spans=list(self.spans(matches[0]))
        if len(spans)!=1: raise ValueError("Multi-block subfiles require a validated block-aware writer")
        j,start,end=spans[0];block=self.blocks[j]
        for other in self.records:
            if other is matches[0]: continue
            for bj,bs,be in self.spans(other):
                if bj==j and start<be and bs<end: raise ValueError("Subfile shares a preserved byte range")
        if block['compressed']: raise ValueError("Compressed subfile replacement blocked: no size-preserving compressor")
        if len(payload)!=end-start: raise ValueError("Replacement must be same size")
        out=bytearray(self.raw);off=block['start']+start;out[off:off+len(payload)]=payload
        StandardIFF(bytes(out));return bytes(out)
