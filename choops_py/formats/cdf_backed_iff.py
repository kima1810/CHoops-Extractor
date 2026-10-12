from .binary import Binary
from .standard_iff import names
from ..archive.manifests import write_bytes,report,safe_name
class CDFPair:
    def __init__(self,iff,cdf):
        self.iff=iff;self.cdf=cdf;b=Binary(iff);c=Binary(cdf)
        if b.u32(0)!=0xF0985030: raise ValueError("Not CDF-backed IFF")
        end=b.u32(4);count=b.u32(24)
        if not 0x68+count*4<=end<=len(iff):raise ValueError("Invalid metadata bounds")
        table=b.relative(32)
        if table+count*4>end:raise ValueError("Segment pointer table outside metadata")
        self.cdf_name=b.utf16(b.relative(36),'be');ns=names(iff,end,count);self.records=[]
        b.slice(0x68,count*4);b.slice(table,count*4)
        for i in range(count):
            rec=b.relative(0x68+i*4);desc=b.relative(table+i*4)
            if rec+20>end or desc+16>end:raise ValueError("Record outside metadata")
            b.slice(rec,20);vals=[b.u32(desc+j*4) for j in range(4)]
            h,hl,p,pl=vals;c.slice(h,hl);c.slice(p,pl)
            name,typ=ns[i] if i<len(ns) else (str(i),{0x1AEDDA1F:'AUDO',0x5C36FB69:'TXTR'}.get(b.u32(rec+4),'UNKNOWN'))
            self.records.append(dict(index=i,name=name,type=typ,header_offset=h,header_length=hl,payload_offset=p,payload_length=pl,primary_words=[b.u32(rec+j*4) for j in range(5)]))
    def manifest(self): return dict(family='cdf-backed-iff',cdf_name=self.cdf_name,records=self.records)
    def dump(self,out):
        for r in self.records:
            base=f"{r['index']:04d}_{safe_name(r['name'])}"
            for label,off,size in [('header',r['header_offset'],r['header_length']),('payload',r['payload_offset'],r['payload_length'])]:write_bytes(out/(base+'.'+label+'.bin'),self.cdf[off:off+size])
        report(out/'manifest.json',self.manifest())
    def replace(self,selector,payload):
        rs=[r for r in self.records if str(r['index'])==selector or r['name']==selector]
        if len(rs)!=1: raise ValueError("Record selector must be unique")
        r=rs[0];p=r['payload_offset'];n=r['payload_length']
        if len(payload)!=n: raise ValueError("Replacement must be same size")
        for other in self.records:
            ranges=[(other['header_offset'],other['header_length'])]
            if other is not r:ranges.append((other['payload_offset'],other['payload_length']))
            if any(p<o+s and o<p+n for o,s in ranges):raise ValueError("Payload overlaps another preserved range")
        out=bytearray(self.cdf);out[p:p+n]=payload;CDFPair(self.iff,bytes(out));return bytes(out)
