"""Bounded process workers for independent override archives; one writer per archive."""
import ctypes
import gc
import hashlib
import json
import multiprocessing as mp
import os
import queue
import sys
import time
from pathlib import Path
from .manifests import digest,write_bytes

MIB=1024*1024


def resources():
    cores=os.cpu_count() or 1
    available=2*1024*MIB
    try:
        if os.name=='nt':
            class Memory(ctypes.Structure):
                _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(name,ctypes.c_ulonglong) for name in ('total','available','page_total','page_available','virtual_total','virtual_available','extended')]
            memory=Memory();memory.length=ctypes.sizeof(memory)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):available=memory.available
        else:available=os.sysconf('SC_AVPHYS_PAGES')*os.sysconf('SC_PAGE_SIZE')
    except (AttributeError,OSError,ValueError):pass
    return cores,available


def policy(count,workers=None):
    cores,available=resources();budget=max(256*MIB,min(4096*MIB,int(available*.5)))
    limit=min(max(1,cores-1),6,max(1,budget//(384*MIB)),max(1,count))
    if workers is not None:limit=min(limit,max(1,workers))
    return limit,budget


def input_signature(group):
    result=[]
    dds={name.casefold() for name in group.get('dds',{})}
    for category in ('whole','cdf_whole','records','dds','package_records'):
        values=group.get(category)
        if not values:continue
        pairs=values.items() if isinstance(values,dict) else [('',values)]
        for key,value in pairs:
            if category=='records' and key[1]=='TXTR' and key[0].casefold() in dds:continue
            if category=='package_records' and key.casefold() in dds:continue
            for path in value if isinstance(value,list) else [value]:
                info=Path(path).stat();result.append([category,str(key),str(Path(path).resolve()),info.st_size,info.st_mtime_ns,info.st_ino])
    return result


def memory_cost(group):
    sizes=sum(row[3] for row in input_signature(group))
    return 256*MIB+4*(group['entry']['size']+sizes)


def code_identity():
    from ..core.code_identity import module_bytes
    root=Path(__file__).resolve().parents[1];identity=hashlib.sha256(b'choops-prepared-cache-1')
    if getattr(sys,'frozen',False):
        modules=('archive.folder_import','archive.iff_validation','archive.parallel_import','archive.layouts','formats.record_labels','formats.package','formats.txtr',
                 'formats.standard_iff','formats.standard_iff_writer','formats.cdf_backed_iff',
                 'formats.cdf_backed_iff_writer','formats.compression','formats.native_codec',
                 'texture_tools.override_import','texture_tools.archive_layout','texture_tools.builtin_converter',
                 'texture_tools.dds','texture_tools.gtf','texture_tools.runtime_layout','texture_tools.legacy_cube',
                 'modding.court_template','modding.team_assets','modding.addition_manifest','studio.services')
        for name in modules:identity.update(module_bytes('choops_py.'+name))
    else:
        for folder in ('archive','formats','texture_tools','modding'):
            for path in sorted((root/folder).glob('*.py')):identity.update(path.read_bytes())
    from PIL import __version__
    identity.update(__version__.encode());return identity.hexdigest()


def _compile_one(archive,group,index,work,job,code,reuse):
    from .folder_import import compile_group
    group.pop('compiled_companion',None)
    original=archive.read(group['entry']);before=digest(original);signature=input_signature(group)
    reference_policy=group.get('logo_templates',{})
    valid=reuse and reuse.get('code')==code and reuse.get('signature')==signature and reuse.get('source_sha256')==before and reuse.get('reference_policy',{})==reference_policy
    if valid:
        payloads=None
        try:
            verified=[];root=Path(reuse['root']).resolve()
            for row in reuse['outputs']:
                reference=archive.entries[row['index']]
                source=original if row['index']==group['entry']['index'] else archive.read(reference)
                if reference['hash']!=row['hash'] or digest(source)!=row['source_sha256']:raise ValueError('Cached source changed')
                path=(root/row['path']).resolve()
                if not path.is_relative_to(root) or path.is_symlink():raise ValueError('Unsafe cached override')
                payload=path.read_bytes()
                if len(payload)!=row['size'] or digest(payload)!=row['sha256']:raise ValueError('Cached override changed')
                verified.append((row,payload))
            payloads=verified
        except (OSError,ValueError,KeyError,IndexError,TypeError):pass
        if payloads is not None:
            if signature!=input_signature(group):raise ValueError('Override inputs changed during preparation; select the folder again')
            for row,payload in payloads:write_bytes(work/row['path'],payload,[archive.path])
            if signature!=input_signature(group):raise ValueError('Override inputs changed during preparation; select the folder again')
            return {**reuse,'cache_hit':True,'root':str(work)}
    data,imports=compile_group(archive,group,job)
    if signature!=input_signature(group):raise ValueError('Override inputs changed during preparation; select the folder again')
    outputs=[]
    unchanged=data==original and group['whole'] is None and not group.get('compiled_companion') and group['entry']['index']<len(getattr(archive,'base',archive).entries)
    def store(entry,name,payload,suffix=''):
        target=f"assets/{group['entry']['index']:06d}{suffix}.bin";write_bytes(work/target,payload,[archive.path])
        source=original if entry['index']==group['entry']['index'] else archive.read(entry)
        outputs.append(dict(index=entry['index'],hash=entry['hash'],archive=name,path=target,size=len(payload),sha256=digest(payload),source_size=len(source),source_sha256=digest(source)))
    if not unchanged:store(group['entry'],group['name'],data)
    if group.get('compiled_companion'):
        entry,name,payload=group['compiled_companion'];store(entry,name,payload,'_cdf')
        group.pop('compiled_companion',None)
    return dict(code=code,signature=signature,reference_policy=reference_policy,source_sha256=before,imports=imports,outputs=outputs,unchanged=unchanged,cache_hit=False,root=str(work))


def _worker(source,work,tasks,results,progress,cancel,code,addition_folder=None):
    from .usrdir_reader import Archive
    from ..studio.services import JobContext
    archive=Archive(source);last=[0.]
    if addition_folder:
        from ..modding.team_assets import AdditionInputs
        archive=AdditionInputs(archive,addition_folder)
    def report(done,total,label):
        now=time.monotonic()
        if now-last[0]<.15:return
        last[0]=now
        try:progress.put_nowait(label)
        except queue.Full:pass
    job=JobContext(report);job.cancelled=cancel
    while not cancel.is_set():
        task=tasks.get()
        if task is None:return
        index,group,reuse=task
        try:result=_compile_one(archive,group,index,Path(work),job,code,reuse)
        except BaseException as error:
            results.put((index,None,group['name']+': '+str(error)));return
        results.put((index,result,None));gc.collect()


def compiled_groups(archive,groups,work,job,*,workers=None,reuse=None):
    """Yield completed groups with bounded CPU/memory, cancelling before cleanup."""
    limit,budget=policy(len(groups),workers);code=code_identity();reuse=reuse or {}
    if limit==1:
        for index,group in enumerate(groups):
            job.check();job.progress(index,len(groups),'DDS priority: '+group['name']+' (1 worker)')
            try:result=_compile_one(archive,group,index,work,job,code,reuse.get(str(group['entry']['index'])))
            except (ValueError,OSError) as error:raise ValueError(group['name']+': '+str(error)) from error
            yield index,group,result,limit
        return
    context=mp.get_context('spawn');cancel=context.Event()
    tasks=context.Queue(limit);results=context.Queue(limit);progress=context.Queue(128)
    processes=[];active={};waiting=list(enumerate(groups));done=0
    costs={index:memory_cost(group) for index,group in waiting}
    try:
        for i in range(limit):
            process=context.Process(target=_worker,args=(str(archive.path),str(work),tasks,results,progress,cancel,code,getattr(archive,'addition_folder',None)),name='CHoops-DDS-'+str(i+1))
            process.start();processes.append(process)
        while waiting or active:
            job.check()
            while waiting and len(active)<limit:
                used=sum(active.values())
                position=next((n for n,(index,g) in enumerate(waiting) if not active or costs[index]+used<=budget),None)
                if position is None:break
                index,group=waiting.pop(position);active[index]=costs[index]
                tasks.put((index,group,reuse.get(str(group['entry']['index']))))
            while True:
                try:label=progress.get_nowait()
                except queue.Empty:break
                job.progress(done,len(groups),f'{label} · {len(active)} active workers · {done}/{len(groups)} archives')
            try:index,result,error=results.get(timeout=.1)
            except queue.Empty:
                if any(p.exitcode is not None for p in processes):raise ValueError('An override worker stopped unexpectedly')
                continue
            active.pop(index)
            if error:raise ValueError(error)
            done+=1;job.progress(done,len(groups),f'Overrides prepared: {done}/{len(groups)} · up to {limit} workers')
            yield index,groups[index],result,limit
    finally:
        cancel.set()
        for _ in processes:
            try:tasks.put_nowait(None)
            except queue.Full:break
        deadline=time.monotonic()+2
        for process in processes:process.join(max(0,deadline-time.monotonic()))
        for process in processes:
            if process.is_alive():process.terminate()
        for process in processes:process.join()
        for channel in (tasks,results,progress):channel.cancel_join_thread();channel.close()


def prior_cache(mod):
    try:
        path=Path(mod)/'compiled_inputs.json';document=json.loads(path.read_text(encoding='utf8'))
        return {key:{**row,'root':str(Path(mod).resolve())} for key,row in document.items()}
    except (OSError,ValueError,TypeError):return {}
