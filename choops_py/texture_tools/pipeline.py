"""Shared export/import pipeline for TXTR, IFF, CDF and SCNE textures.

Uniform/court/logo commands select assets here; they do not own separate writers.
"""
from dataclasses import dataclass, field
from pathlib import Path
import json
import uuid
from ..formats.standard_iff import StandardIFF
from ..formats.standard_iff_writer import record, record_blocks, replace_records
from ..formats.cdf_backed_iff import CDFPair
from ..formats.compression import decode, encode_like, MAGIC
from ..formats.binary import Binary
from ..formats.tool_wrapper import unwrap,wrap
from ..formats.txtr import TXTR
from ..formats.package import textures as package_textures, replace_texture as package_replace
from ..archive.manifests import OUTPUT, write_bytes, safe_output, safe_name, digest
from ..core.reports import save_json, import_report
from ..core.errors import ToolError
from . import external_converters as converters, dds, gtf

@dataclass
class Asset:
    name: str
    index: int
    kind: str
    raw: bytes
    texture: TXTR | None = None
    record_index: int | None = None
    package_index: int | None = None
    package_blocks: list | None = None
    warnings: list = field(default_factory=list)

class Container:
    def __init__(self,source,cdf=None):
        self.source=Path(source).resolve();self.raw=self.source.read_bytes();self.cdf_path=Path(cdf).resolve() if cdf else None
        self.iff=None;self.pair=None;self.wrapper_type=None;self.assets=[]
        if self.raw[:4]==bytes.fromhex('ff3bef94'):
            self.kind='standard-iff';self.iff=StandardIFF(self.raw)
            for rec in self.iff.records:
                if rec['type'] not in ('TXTR','SCNE'):continue
                try:
                    blocks=[x[3] for x in record_blocks(self.iff,rec)]
                    self._add(rec['name'],rec['index'],rec['type'],blocks,rec['index'])
                except ValueError as error:self.assets.append(Asset(rec['name'],rec['index'],rec['type'],b'',warnings=[str(error)]))
        elif self.raw[:4]==bytes.fromhex('f0985030'):
            if not self.cdf_path:raise ToolError('cdf_pair_required','CDF-backed IFF requires its paired CDF')
            self.kind='cdf-pair';self.pair=CDFPair(self.raw,self.cdf_path.read_bytes())
            # Verify paired filename when the metadata supplies it.
            if Path(self.pair.cdf_name).name.lower()!=self.cdf_path.name.lower():raise ToolError('cdf_pair_mismatch',f'Metadata names {self.pair.cdf_name}, selected {self.cdf_path.name}')
            for rec in self.pair.records:
                if rec['type'] not in ('TXTR','SCNE'):continue
                raw_header=self.pair.cdf[rec['header_offset']:rec['header_offset']+rec['header_length']]
                raw_payload=self.pair.cdf[rec['payload_offset']:rec['payload_offset']+rec['payload_length']]
                if raw_payload[:4]==bytes.fromhex('01080000'):
                    try:
                        _,desc,payload=gtf.parse(raw_payload);header=bytearray(176);header[0x58:0x70]=desc
                        self.assets.append(Asset(rec['name'],rec['index'],'GTF',raw_payload,TXTR([bytes(header),payload]),rec['index']))
                    except ValueError as error:self.assets.append(Asset(rec['name'],rec['index'],'GTF',raw_payload,warnings=[str(error)]))
                else:
                    try:self._add(rec['name'],rec['index'],rec['type'],[decode(raw_header),decode(raw_payload)],rec['index'])
                    except ValueError as error:self.assets.append(Asset(rec['name'],rec['index'],rec['type'],raw_header+raw_payload,warnings=[str(error)]))
        elif self.raw[:4]==b'2kTl':
            self.wrapper_type,blocks=unwrap(self.raw)
            self.kind='tool-wrapper'
            self._add(self.source.stem,0,'SCNE' if self.wrapper_type==2 else 'TXTR',blocks)
        elif self.source.suffix.lower()=='.scne' and self.raw[:4]==bytes.fromhex('00010b1d'):
            self.kind='raw-scne';self._add(self.source.stem,0,'SCNE',[self.raw])
        else:
            self.kind='raw-txtr';self._add(self.source.stem,0,'TXTR',[self.raw])
    def _add(self,name,index,typ,blocks,record_index=None):
        wrapped=wrap(1 if typ=='TXTR' else 2,blocks)
        if typ=='TXTR':
            texture=TXTR(blocks,self.wrapper_type if self.kind=='tool-wrapper' else None)
            asset=Asset(name,index,typ,wrapped,texture,record_index)
            try:texture.info()
            except ValueError as error:asset.warnings.append(str(error));asset.texture=None
            self.assets.append(asset)
        else:
            try:
                for t in package_textures(blocks):
                    self.assets.append(Asset(f'{name}/texture_{t.index}',index,'SCNE',wrap(1,[t.header,t.payload]),TXTR([t.header,t.payload]),record_index,t.index,blocks))
            except ValueError as error:self.assets.append(Asset(name,index,'SCNE',wrapped,warnings=[str(error)]))
    def select(self,selector):
        selector=str(selector);matches=[a for a in self.assets if a.name==selector or str(a.index)==selector and a.package_index is None or (a.name+'.txtr')==selector]
        if len(matches)!=1:raise ToolError('ambiguous_texture',f'Select a unique texture name; {selector} matches {len(matches)} assets')
        if not matches[0].texture:raise ToolError('texture_layout_not_supported','; '.join(matches[0].warnings))
        return matches[0]
    def replacement(self,asset,image):
        replacement=asset.texture.replace_image(image)
        blocks=package_replace(asset.package_blocks,asset.package_index,image,len(image)) if asset.package_index is not None else replacement.blocks
        if self.iff:return replace_records(self.iff,{asset.record_index:blocks})
        if self.pair:
            rec=next(r for r in self.pair.records if r['index']==asset.record_index)
            start,size=rec['payload_offset'],rec['payload_length'];original=self.pair.cdf[start:start+size]
            logical=blocks[1]
            if asset.kind=='GTF':
                info,desc,payload=gtf.parse(original);out=bytearray(original);out[info['payload_offset']:info['payload_offset']+len(image)]=image;stored=bytes(out)
            elif original[:4]==MAGIC.to_bytes(4,'big'):
                stored=encode_like(original,logical)
                if len(stored)>size:raise ToolError('cdf_payload_capacity_exceeded',f'Recompressed record needs {len(stored)} bytes; original is {size}')
                stored=stored+b'\0'*(size-len(stored));mutable=bytearray(stored)
                import struct
                struct.pack_into('>I',mutable,8,size);stored=bytes(mutable)
                if decode(stored)!=logical:raise ToolError('writer_validation_failed','CDF recompression differs')
            else:stored=logical
            return self.pair.replace(str(asset.record_index),stored)
        if self.wrapper_type is not None:return wrap(self.wrapper_type,blocks)
        if len(blocks)!=1:raise ToolError('raw_package_layout_not_supported','Raw package requires explicit block separation')
        return blocks[0]

def export(source,output,cdf=None,want_dds=True,converter=None,strict=False,scope='all'):
    sources=[source]+([cdf] if cdf else []);out=safe_output(output,sources);out.mkdir(parents=True,exist_ok=True)
    raw=Path(source).read_bytes();write_bytes(out/('source_'+safe_name(Path(source).name)),raw,sources)
    if cdf:write_bytes(out/('source_'+safe_name(Path(cdf).name)),Path(cdf).read_bytes(),sources)
    container=Container(source,cdf);entries=[]
    for number,asset in enumerate(container.assets):
        if scope=='atlas' and asset.name not in ('names','jersey_numbers'):continue
        if scope=='scne' and asset.kind!='SCNE':continue
        name=f'{number:04d}_{safe_name(asset.name)}';entry=dict(source_file=str(Path(source).resolve()),source_sha256=digest(raw),texture_name=asset.name,texture_index=asset.index,record_index=asset.record_index,package_index=asset.package_index,container_type=container.kind,wrapper_status='2kTl' if container.wrapper_type is not None else 'unwrapped',raw_output_path=str(out/(name+'.txtr')),gtf_output_path=None,dds_output_path=None,inferred_dimensions=None,inferred_format=None,mip_count=None,converter_status='not_requested',warnings=list(asset.warnings),import_eligibility={'eligible':False,'reason':'layout_not_validated'})
        write_bytes(out/(name+'.txtr'),asset.raw,sources)
        try:
            if not asset.texture:raise ToolError('texture_layout_not_supported','; '.join(asset.warnings))
            info=asset.texture.info();entry.update(inferred_dimensions=[info['width'],info['height']],inferred_format=info['format'],mip_count=info['mip_count'],texture_metadata=info)
            gtf_path=out/(name+'.gtf');write_bytes(gtf_path,asset.texture.gtf(),sources);entry['gtf_output_path']=str(gtf_path)
            entry['import_eligibility']={'eligible':True,'reason':'same_format_dimensions_mips_only; compressed growth must fit original extent'}
            if want_dds:
                dds_path=out/(name+'.dds')
                try:
                    converters.convert('gtf2dds',gtf_path,dds_path,converter)
                    meta=dds.inspect(dds_path.read_bytes())
                    validate_layout(info,meta)
                    entry['converter_status']='success'
                except ToolError as error:
                    # Old CH2K8 inline L8 atlases use an unsupported converter format.
                    # Preserve the proven linear bytes; never pad/truncate incomplete input.
                    if info['format']=='L8' and info['linear']:
                        if dds_path.exists():dds_path.unlink()
                        write_bytes(dds_path,dds.linear_l8(info['width'],info['height'],info['mip_count'],asset.texture.image()),sources)
                        entry['converter_status']='native_linear_l8_fallback';entry['warnings'].append(str(error))
                    else:
                        if dds_path.exists():dds_path.unlink()
                        raise
                entry['dds_output_path']=str(dds_path)
        except (ValueError,OSError) as error:
            entry['converter_status']=getattr(error,'code','export_failed');entry['warnings'].append(str(error))
            if strict:
                entries.append(entry);save_json(out/'manifest.json',{'textures':entries});save_json(out/'conversion_report.json',entries);raise
        entries.append(entry)
        if (number+1)%25==0:print(f'Exported {number+1}/{len(container.assets)} texture candidates',flush=True)
    result={'schema':2,'source':str(Path(source).resolve()),'container':container.kind,'textures':entries,'dds_exported':sum(bool(e['dds_output_path']) for e in entries),'raw_exported':len(entries)}
    save_json(out/'manifest.json',result,sources);save_json(out/'conversion_report.json',entries,sources);return result

def validate_layout(original,replacement):
    for key in ('width','height','format','mip_count'):
        if original[key]!=replacement[key]:raise ToolError('texture_'+key+'_mismatch',f"Original {key}={original[key]}, replacement {replacement[key]}")

def imported_image(asset,dds_file,converter=None):
    original=asset.texture.info();data=Path(dds_file).read_bytes();meta=dds.inspect(data);validate_layout(original,meta)
    temp=OUTPUT/'temp';temp.mkdir(parents=True,exist_ok=True)
    work=temp/('dds_import_'+uuid.uuid4().hex);work.mkdir();result=converters.convert('dds2gtf',dds_file,work/'converted.gtf',converter,swizzle=not original['linear'])
    info,desc,payload=gtf.parse((work/'converted.gtf').read_bytes());validate_layout(original,info)
    if info['linear']!=original['linear']:raise ToolError('texture_layout_mismatch','Converter changed linear/swizzled layout')
    if len(payload)!=original['image_size'] and original['linear'] and original['format']=='L8':
        # dds2gtf stores every linear mip at the top-level pitch. CH2K8's
        # inline L8 atlas stores tight mip rows. Strip only verified row padding.
        width,height=info['width'],info['height'];pitch=info['pitch'];position=0;packed=bytearray()
        for _ in range(info['mip_count']):
            for row in range(height):
                packed.extend(Binary(payload).slice(position+row*pitch,width))
            position+=height*pitch;width=max(1,width//2);height=max(1,height//2)
        if position!=len(payload) or len(packed)!=original['image_size'] or bytes(packed)!=data[128:]:
            raise ToolError('linear_mip_layout_not_validated','Converter row padding cannot be safely normalized')
        payload=bytes(packed)
    if len(payload)!=original['image_size']:raise ToolError('payload_size_mismatch',f"Converted GTF has {len(payload)} bytes; expected {original['image_size']}")
    return payload,result

def import_texture(source,selector,dds_file,output,cdf=None,converter=None,dynamic=False):
    sources=[source,dds_file]+([cdf] if cdf else []);out=safe_output(output,sources)
    report={'source':str(source),'texture':str(selector),'dds_file':str(dds_file),'output':str(out),'status':'blocked'}
    try:
        container=Container(source,cdf);asset=container.select(selector)
        if dynamic and not container.pair:
            from .override_import import apply_dds
            from ..formats.standard_iff_writer import replace_records_expanding
            if container.iff:
                rec=container.iff.records[asset.record_index]
                parts=[span[3] for span in record_blocks(container.iff,rec)]
                kind=rec['type'];texture_selector='texture_'+str(asset.package_index) if asset.package_index is not None else str(selector)
            else:
                parts=asset.package_blocks if asset.package_index is not None else asset.texture.blocks
                kind='SCNE' if asset.package_index is not None else 'TXTR'
                texture_selector='texture_'+str(asset.package_index) if asset.package_index is not None else str(selector)
            changed,layout=apply_dds(parts,kind,texture_selector,dds_file,converter=converter)
            if container.iff:result=replace_records_expanding(container.iff,{asset.record_index:changed})
            elif container.wrapper_type is not None:result=wrap(container.wrapper_type,changed)
            else:
                if len(changed)!=1:raise ToolError('raw_package_layout_not_supported','Raw multiblock input requires a wrapper')
                result=changed[0]
            conversion={'dynamic_layout':True,'dds_layout':layout}
        else:
            image,conversion=imported_image(asset,dds_file,converter)
            result=container.replacement(asset,image)
        if cdf:
            CDFPair(container.raw,result);out.mkdir(parents=True,exist_ok=True)
            write_bytes(out/Path(source).name,container.raw,sources);write_bytes(out/Path(cdf).name,result,sources)
        else:
            if container.iff:StandardIFF(result)
            elif container.wrapper_type is not None:unwrap(result)
            write_bytes(out,result,sources)
        report.update(status='success',conversion=conversion,source_sha256=digest(container.raw),output_sha256=digest(result),unknown_metadata_preserved=True)
    except (ValueError,OSError) as error:
        report.update(reason=getattr(error,'code','import_failed'),detail=str(error));import_report(report);raise
    import_report(report);return report

def import_logo_batch(source,cdf,manifest,edited,output,converter=None):
    manifest=json.loads(Path(manifest).read_text(encoding='utf-8'));container=Container(source,cdf)
    if manifest.get('source')!=str(Path(source).resolve()):raise ToolError('manifest_source_mismatch','Export manifest belongs to another source')
    current=container.pair.cdf;edits=[]
    for entry in manifest['textures']:
        if entry['source_sha256']!=digest(container.raw):raise ToolError('manifest_source_mismatch','Metadata source changed')
        original_dds=entry.get('dds_output_path')
        if not original_dds:continue
        candidate=Path(edited)/Path(original_dds).name
        if not candidate.is_file():continue
        asset=container.select(entry['texture_name']);image,conversion=imported_image(asset,candidate,converter)
        container.pair=CDFPair(container.raw,current);current=container.replacement(asset,image);edits.append(entry['texture_name'])
    sources=[source,cdf,edited];out=safe_output(output,sources);out.mkdir(parents=True,exist_ok=True)
    CDFPair(container.raw,current);write_bytes(out/Path(source).name,container.raw,sources);write_bytes(out/Path(cdf).name,current,sources)
    result={'status':'success','edited_textures':edits};import_report(result);return result
