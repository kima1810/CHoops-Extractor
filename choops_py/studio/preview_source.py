"""Read-only preview overlay of source-bound staged complete archives."""
import json
from pathlib import Path
from ..archive.manifests import digest
from ..archive.hash_names import replacement_hash


class PreviewArchive:
    def __init__(self,archive,mod):
        self.base=archive;self.path=archive.path;self.entries=[dict(e) for e in archive.entries]
        self.toc_layout=getattr(archive,'toc_layout',None);self.game_info=getattr(archive,'game_info',{})
        self.replacements={};self.conditions={};self.live=None
        root=Path(mod).resolve();manifest=root/'overrides.json'
        self.logo_templates=json.loads((root/'team_logo_templates.json').read_text(encoding='utf8')) if (root/'team_logo_templates.json').is_file() else {}
        self.alternate_fallbacks=json.loads((root/'alternate_fallbacks.json').read_text(encoding='utf8')) if (root/'alternate_fallbacks.json').is_file() else []
        if not manifest.is_file():return
        conditions=root/'source_preconditions.json'
        if not conditions.is_file():raise ValueError('Override previews require source preconditions; select the overrides folder again')
        self.conditions={e['index']:e for e in json.loads(conditions.read_text(encoding='utf8'))['entries']}
        for row in json.loads(manifest.read_text(encoding='utf8')):
            if row.get('subfile') is not None or row.get('kind')!='archive':raise ValueError('Select an overrides folder containing complete archives before previewing this mod')
            matches=[e for e in self.entries if e['hash']==replacement_hash(row['archive'])]
            if len(matches)!=1:raise ValueError('Override preview archive identity is ambiguous')
            entry=matches[0];target=(root/row['path']).resolve()
            if not target.is_relative_to(root) or not target.is_file():raise ValueError('Override preview path is invalid')
            if entry['index'] in self.replacements:raise ValueError('Duplicate override archive')
            self.replacements[entry['index']]=(target,row['sha256'])
            entry['size']=target.stat().st_size

        if (root/'preview_inputs.json').is_file():
            from .live_overrides import LiveOverrides
            self.live=LiveOverrides(archive,root/'preview_inputs.json')
            for index in self.live.groups:
                self.replacements.setdefault(index,(root/'preview_inputs.json',digest((root/'preview_inputs.json').read_bytes())))
        from ..modding.addition_manifest import load as load_additions
        self.additions=load_additions(root,archive)
        for name,data in self.additions.items():
            self.replacements[len(self.entries)]=(root,digest(data))
            self.entries.append(dict(index=len(self.entries),hash=replacement_hash(name),name=name,size=len(data),
                                     content_size=len(data),stored_size=len(data),offset=0,toc_flags=0,size_derived=False))

    @property
    def read_only(self):
        return self.base.read_only

    def read(self,entry):
        index=entry['index']
        if index>=len(self.base.entries):return self.additions[entry['name']]
        if index not in self.replacements:return self.base.read(self.base.entries[index])
        if self.live and self.live.owner(index) is not None:
            return self.live.read(index)
        expected=self.conditions.get(index)
        original=self.base.entries[index]
        if not expected or expected['hash']!=original['hash'] or expected['sha256']!=digest(self.base.read(original)):
            raise ValueError('Override previews belong to another or changed JB source')
        path,checksum=self.replacements[index];data=path.read_bytes()
        if digest(data)!=checksum:raise ValueError('Override preview asset checksum changed; select the overrides folder again')
        return data

    def chunks(self,entry):
        if entry['index'] in self.replacements or entry['index']>=len(self.base.entries):
            data=self.read(entry)
            for offset in range(0,len(data),1024*1024):yield data[offset:offset+1024*1024]
        else:yield from self.base.chunks(self.base.entries[entry['index']])
