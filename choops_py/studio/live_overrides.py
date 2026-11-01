"""Read current loose override inputs without changing prepared build snapshots."""
from collections import OrderedDict
from pathlib import Path
import json
from ..archive.manifests import digest


def describe_groups(groups,folder,archive):
    root=Path(folder).resolve()
    def relative(path):return str(Path(path).resolve().relative_to(root)) if path else None
    return dict(schema=1,folder=str(root),groups=[dict(
        index=g['entry']['index'],hash=g['entry']['hash'],name=g['name'],
        source_sha256=g.get('_preview_source_sha') or digest(archive.read(g['entry'])),
        whole=relative(g['whole']),cdf_whole=relative(g.get('cdf_whole')),
        logo_templates=g.get('logo_templates',{}),
        records=[dict(name=name,type=kind,paths=[relative(p) for p in (value if isinstance(value,list) else [value])],multiple=isinstance(value,list)) for (name,kind),value in g['records'].items()],
        dds={name:relative(path) for name,path in g['dds'].items()},
        dds_rank=g['dds_rank'],package_records={name:relative(path) for name,path in g['package_records'].items()}) for g in groups])


class LiveOverrides:
    def __init__(self,base,path):
        document=json.loads(Path(path).read_text(encoding='utf8'))
        if document.get('schema')!=1:raise ValueError('Unsupported live override index; select overrides again')
        self.base=base;self.root=Path(document['folder']).resolve();self.groups={};self.companions={}
        self.cache=OrderedDict();self.bytes=0
        def file(name):
            if name is None:return None
            path=self.root/name
            if not path.resolve().is_relative_to(self.root):raise ValueError('Live override path escapes selected folder')
            return path
        for row in document['groups']:
            index=row['index'];entry=base.entries[index]
            if entry['hash']!=row['hash']:raise ValueError('Live overrides belong to another JB')
            group=dict(entry=entry,source_sha256=row['source_sha256'],name=row['name'],whole=file(row['whole']),cdf_whole=file(row.get('cdf_whole')),
                       records={},dds={k:file(v) for k,v in row['dds'].items()},dds_rank=row['dds_rank'],
                       package_records={k:file(v) for k,v in row['package_records'].items()})
            if row.get('logo_templates'):group['logo_templates']=row['logo_templates']
            for record in row['records']:
                paths=[file(name) for name in record['paths']]
                group['records'][(record['name'],record['type'])]=paths if record['multiple'] else paths[0]
            self.groups[index]=group
            if group['name'].lower().endswith('.iff'):
                partner=next((e for e in base.entries if e.get('name')==group['name'][:-4]+'.cdf'),None)
                if partner:self.companions[partner['index']]=index

    def owner(self,index):return index if index in self.groups else self.companions.get(index)

    def signature(self,index):
        owner=self.owner(index)
        if owner is None:return None
        group=self.groups[owner];files=[]
        for key in ('whole','cdf_whole'):
            if group.get(key):files.append(group[key])
        dds={name.casefold() for name in group['dds']}
        for key in ('records','dds','package_records'):
            for name,value in group[key].items():
                if key=='records' and name[1]=='TXTR' and name[0].casefold() in dds:continue
                if key=='package_records' and name.casefold() in dds:continue
                files.extend(value if isinstance(value,list) else [value])
        result=[]
        for path in files:
            if not path.resolve().is_relative_to(self.root) or any(p.is_symlink() or (hasattr(p,'is_junction') and p.is_junction()) for p in [path,*path.parents] if p!=self.root.parent):
                raise ValueError('Linked/escaped live override input; select a regular overrides folder')
            stat=path.stat();result.append((str(path),stat.st_size,stat.st_mtime_ns,stat.st_ino))
        for part in self.base.parts:
            stat=(self.base.path/part['name']).stat();result.append((part['name'],stat.st_size,stat.st_mtime_ns,stat.st_ino))
        return tuple(result)

    def read(self,index):
        owner=self.owner(index)
        if owner is None:return None
        signature=self.signature(index);key=(owner,signature)
        if key not in self.cache:
            from ..archive.folder_import import compile_group
            group=self.groups[owner]
            from ..archive.manifests import digest
            if digest(self.base.read(group['entry']))!=group['source_sha256']:
                raise ValueError('Live overrides belong to another or changed JB source')
            group.pop('compiled_companion',None)
            data,details=compile_group(self.base,group)
            failures=[d for d in details if d.get('status')=='unmatched']
            if failures:raise ValueError('Live preview has unapplied override textures; supply matching SCNE: '+group['name'])
            if signature!=self.signature(index):raise ValueError('Overrides changed during preview; preview again')
            payloads={owner:data}
            if group.get('compiled_companion'):
                companion,_,payload=group['compiled_companion'];payloads[companion['index']]=payload
            size=sum(map(len,payloads.values()))
            while self.cache and self.bytes+size>64*1024*1024:
                _,previous=self.cache.popitem(last=False);self.bytes-=sum(map(len,previous.values()))
            if size<=64*1024*1024:self.cache[key]=payloads;self.bytes+=size
        else:
            payloads=self.cache[key];self.cache.move_to_end(key)
        if index not in payloads:return self.base.read(self.base.entries[index])
        return payloads[index]
