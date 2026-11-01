"""Content-addressed builtin texture conversion cache with corruption checks."""
import hashlib
import os
import uuid
import re
import time
from functools import lru_cache
from pathlib import Path
from ..archive.manifests import OUTPUT


def cached_conversion(name,source,swizzle,convert,root=None):
    folder=Path(root) if root is not None else OUTPUT/'cache'/'texture_conversions'
    identity=_base_identity().copy()
    identity.update(name.encode());identity.update(bytes([bool(swizzle)]));identity.update(source)
    key=identity.hexdigest();target=folder/(key+'.bin')
    try:
        cached=target.read_bytes()
        if len(cached)>=32 and hashlib.sha256(cached[32:]).digest()==cached[:32]:
            target.touch()
            return cached[32:],True
    except OSError:pass
    result=convert()
    # Cache failures never prevent conversion; cap any one stored entry.
    if len(result)<=128*1024*1024:
        temporary=folder/('.'+uuid.uuid4().hex)
        try:
            folder.mkdir(parents=True,exist_ok=True)
            temporary.write_bytes(hashlib.sha256(result).digest()+result)
            os.replace(temporary,target)
            _maintain(folder,len(result)+32)
        except OSError:pass
        finally:
            if temporary.exists():temporary.unlink()
    return result,False


@lru_cache(maxsize=1)
def _base_identity():
    identity=hashlib.sha256(b'choops-conversion-cache-1')
    from ..core.code_identity import module_bytes
    for module in ('builtin_converter','dds','gtf','runtime_layout'):
        identity.update(module_bytes('choops_py.texture_tools.'+module))
    from PIL import __version__
    identity.update(__version__.encode())
    return identity


_maintenance={}


def _maintain(folder,written=0,force=False):
    """Batch cache directory scans; cross-process lock only guards pruning."""
    key=str(folder.resolve());last,pending=_maintenance.get(key,(0.,0));pending+=written
    if not force and time.monotonic()-last<5 and pending<16*1024*1024:
        _maintenance[key]=(last,pending);return
    lock=folder/'.prune.lock'
    try:
        try:handle=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        except FileExistsError:
            if not lock.is_symlink() and time.time()-lock.stat().st_mtime>60:lock.unlink()
            return
        try:
            os.close(handle);entries=[]
            for path in folder.glob('*.bin'):
                if not re.fullmatch(r'[0-9a-f]{64}\.bin',path.name) or path.is_symlink():continue
                try:info=path.stat()
                except OSError:continue
                entries.append((info.st_mtime_ns,info.st_size,path))
            total=sum(size for _,size,_ in entries)
            for _,size,path in sorted(entries):
                if total<=512*1024*1024:break
                try:path.unlink();total-=size
                except OSError:continue
            _maintenance[key]=(time.monotonic(),0)
        finally:lock.unlink(missing_ok=True)
    except OSError:pass
