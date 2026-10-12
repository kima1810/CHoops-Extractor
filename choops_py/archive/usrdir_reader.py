from pathlib import Path
from .hash_names import lookup
from ..formats.binary import Binary
def usrdir(path):
    p=Path(path).resolve()
    if p.is_file() and p.name=='0A':p=p.parent
    for candidate in (p,p/'PS3_GAME'/'USRDIR',p/'USRDIR'):
        if (candidate/'0A').is_file():return candidate
    raise ValueError("No PS3 USRDIR/0A found")
class Archive:
    def __init__(self,path):
        self.path=usrdir(path)
        with (self.path/'0A').open('rb') as f:
            b=Binary(f.read(24));self.magic=b.u32(0);self.alignment=b.u32(4);na=b.u32(8);nf=b.u32(16)
            if self.magic!=0xAA00B3BF or not self.alignment or self.alignment & (self.alignment-1) or not 1<=na<=256 or not 1<=nf<=1000000:raise ValueError("Invalid CH2K8 archive header")
            desc=Binary(f.read(na*16));self.parts=[]
            for i in range(na):
                name=desc.slice(i*16+8,8).decode('utf-16-be').rstrip('\0')
                if not name or Path(name).name!=name or any(c in name for c in '/\\:') or name in ('.','..'):raise ValueError("Unsafe archive part name")
                p=self.path/name;size=desc.u32(i*16)<<11
                if p.stat().st_size!=size:raise ValueError("Archive part size mismatch")
                if any(part['name'].casefold()==name.casefold() for part in self.parts):raise ValueError('Duplicate archive part name')
                self.parts.append(dict(name=name,size=size))
            toc=Binary(f.read(nf*16));self.entries=[]
            for i in range(nf):
                h=toc.u32(i*16);off=toc.u32(i*16+4)*self.alignment;size=toc.u32(i*16+12)
                self.entries.append(dict(index=i,hash=h,name=lookup().get(h),offset=off,stored_size=size,size=size,toc_flags=toc.u32(i*16+8)))
        ordered=sorted(self.entries,key=lambda e:e['offset']);total=sum(p['size'] for p in self.parts)
        if ordered[0]['offset']<24+na*16+nf*16:raise ValueError('Archive entry overlaps header/TOC')
        for i,e in enumerate(ordered):
            boundary=ordered[i+1]['offset'] if i+1<len(ordered) else total
            if not 0<=e['offset']<boundary<=total:raise ValueError("Invalid TOC ordering/range")
            capacity=boundary-e['offset']
            e['allocation_size']=capacity
            if not 0<e['stored_size']<=capacity:
                e['size_derived']=True
                e['content_size']=None
                e['size']=capacity
            else:
                e['content_size']=e['stored_size']
                e['size']=min(capacity,(e['stored_size']+self.alignment-1)//self.alignment*self.alignment)
        from .identity import load_cached
        load_cached(self)
    def read(self,entry):
        start=entry['offset'];remaining=entry['size'];chunks=[];base=0
        for part in self.parts:
            end=base+part['size']
            if base<=start<end and remaining:
                n=min(remaining,end-start)
                with (self.path/part['name']).open('rb') as f:f.seek(start-base);data=f.read(n)
                if len(data)!=n:raise ValueError("Short archive read")
                chunks.append(data);remaining-=n;start+=n
            base=end
        if remaining:raise ValueError("Archive range outside split parts")
        return b''.join(chunks)

    def chunks(self, entry, chunk_size=1024*1024):
        """Bounded streaming across split parts; never materialize a full bank."""
        if chunk_size <= 0:
            raise ValueError("Chunk size must be positive")
        start, remaining = entry['offset'], entry['size']
        if start < 0 or remaining < 0 or start + remaining > sum(p['size'] for p in self.parts):
            raise ValueError("Archive range outside split parts")
        base = 0
        for part in self.parts:
            end = base + part['size']
            if base <= start < end and remaining:
                n = min(remaining, end-start)
                with (self.path/part['name']).open('rb') as stream:
                    stream.seek(start-base)
                    while n:
                        data = stream.read(min(n, chunk_size))
                        if not data:
                            raise ValueError("Short archive read")
                        yield data
                        n -= len(data)
                        remaining -= len(data)
                        start += len(data)
            base = end
        if remaining:
            raise ValueError("Archive range outside split parts")
