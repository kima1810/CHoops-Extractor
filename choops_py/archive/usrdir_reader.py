from pathlib import Path
from .hash_names import lookup
from ..formats.binary import Binary
from .layouts import decode_toc
def usrdir(path):
    p=Path(path).resolve()
    if p.is_file() and p.name in ('0A','0A.SDAT'):p=p.parent
    for candidate in (p,p/'PS3_GAME'/'USRDIR',p/'USRDIR'):
        if any((candidate/name).is_file() for name in ('0A','0A.SDAT')):return candidate
    raise ValueError("No PS3 USRDIR/0A or 0A.SDAT found")

class Archive:
    def __init__(self,path):
        self.path=usrdir(path)
        from .sdat import SDATReader
        first='0A' if (self.path/'0A').is_file() else '0A.SDAT'
        opener=SDATReader if first.endswith('.SDAT') else lambda p:p.open('rb')
        with opener(self.path/first) as f:
            b=Binary(f.read(24));self.magic=b.u32(0);self.alignment=b.u32(4);na=b.u32(8);nf=b.u32(16)
            if self.magic!=0xAA00B3BF or not self.alignment or self.alignment & (self.alignment-1) or not 1<=na<=256 or not 1<=nf<=1000000:raise ValueError("Invalid PS3 2K archive header")
            candidates=[];errors=[]
            for stride in (16,72):
                try:
                    f.seek(24);desc=Binary(f.read(na*stride));parts=[]
                    for i in range(na):
                        encoded=desc.slice(i*stride+8,stride-8).decode('utf-16-be')
                        name=encoded.split('\0',1)[0]
                        if encoded[len(name):].strip('\0'):raise ValueError('Nonzero descriptor suffix')
                        for prefix in ('DVD:','SDAT:'):
                            if name.startswith(prefix):name=name[len(prefix):]
                        if not name or Path(name).name!=name or any(c in name for c in '/\\:') or name in ('.','..'):raise ValueError("Unsafe archive part name")
                        physical=name if (self.path/name).is_file() else name+'.SDAT'
                        file=self.path/physical;size=desc.u32(i*stride)<<11
                        if physical.endswith('.SDAT'):
                            with SDATReader(file) as part:actual=part.size
                        else:actual=file.stat().st_size
                        if actual!=size:raise ValueError(f'Archive part size mismatch: {physical}; expected {size:,} bytes, found {actual:,}. Restore that source bank from the same rip and reselect the source JB.')
                        if any(part['name'].casefold()==physical.casefold() for part in parts):raise ValueError('Duplicate archive part name')
                        parts.append(dict(name=physical,size=size,encrypted=physical.endswith('.SDAT')))
                    self.parts=parts
                    from contextlib import ExitStack
                    from .build_io import BankReader
                    with ExitStack() as handles:raw=BankReader(self,handles).read(24+na*stride,nf*16)
                    layout,entries=decode_toc(raw,self.alignment,24+na*stride+nf*16,sum(p['size'] for p in parts))
                    candidates.append((stride,parts,layout,entries))
                except (ValueError,OSError,UnicodeError) as error:
                    errors.append(str(stride)+'-byte descriptors: '+str(error));continue
            if len(candidates)!=1:raise ValueError('Unsupported or ambiguous 2K bank descriptors/TOC: overlaps or invalid ranges. '+'; '.join(errors))
            self.descriptor_stride,self.parts,self.toc_layout,self.entries=candidates[0]
            self.read_only=any(p['encrypted'] for p in self.parts) or self.descriptor_stride!=16
            for entry in self.entries:entry['name']=lookup().get(entry['hash'])
        from .game_info import read_identity
        self.game_info=read_identity(self.path)
        from .identity import load_cached
        load_cached(self)

    def open_part(self,part):
        if part.get('encrypted'):
            from .sdat import SDATReader
            return SDATReader(self.path/part['name'])
        return (self.path/part['name']).open('rb')

    def require_writable(self):
        if self.read_only:
            raise ValueError('SDAT/extended bank archives support extraction and previews only; authenticated JB rebuilding is not implemented')

    def read(self,entry):
        start=entry['offset'];remaining=entry['size'];chunks=[];base=0
        for part in self.parts:
            end=base+part['size']
            if base<=start<end and remaining:
                n=min(remaining,end-start)
                with self.open_part(part) as f:f.seek(start-base);data=f.read(n)
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
                with self.open_part(part) as stream:
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
