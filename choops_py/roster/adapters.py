"""Roster source adapters preserve IFF, USERDATA, raw and ZIP wrappers."""
from dataclasses import dataclass
from pathlib import Path
import copy
import io
import struct
import zipfile
from ..formats.standard_iff import StandardIFF
from ..formats.standard_iff_writer import record,record_blocks,replace_records_expanding
from ..formats.tool_wrapper import unwrap,wrap
from ..archive.manifests import digest
from ..core.errors import ToolError
@dataclass
class RosterSource:
    kind: str
    original: bytes
    payload: bytes
    source_path: str = ''
    iff: object = None
    record_index: int | None = None
    wrapper_type: int | None = None
    zip_member: str | None = None
    inner: object = None
    def encode(self,payload):
        if len(payload)!=len(self.payload):
            if self.kind=='standard-iff':
                from .uniforms import encode_roster_iff
                return encode_roster_iff(self.original,payload)
            if self.kind=='raw-rost':return payload
            raise ToolError('roster_size_change_blocked','Expanded alternate tables require a raw or single-record ROST IFF')
        if payload==self.payload:return self.original
        if self.kind=='raw-rost':return payload
        if self.kind=='userdata':return self.original[:4]+payload
        if self.kind=='tool-wrapper':return wrap(self.wrapper_type,[payload])
        if self.kind=='standard-iff':
            rec=record(self.iff,self.record_index,'ROST');spans=record_blocks(self.iff,rec);offset=0;parts=[]
            for _,start,end,_ in spans:parts.append(payload[offset:offset+end-start]);offset+=end-start
            return replace_records_expanding(self.iff,{self.record_index:parts})
        if self.kind=='save-zip':
            new_userdata=self.inner.encode(payload);out=io.BytesIO()
            with zipfile.ZipFile(io.BytesIO(self.original)) as old,zipfile.ZipFile(out,'w') as new:
                new.comment=old.comment
                for entry in old.infolist():new.writestr(copy.copy(entry),new_userdata if entry.filename==self.zip_member else old.read(entry))
            return out.getvalue()
        raise ToolError('unsupported_roster_wrapper',self.kind)

def load_bytes(data,path=''):
    if len(data)>64*1024*1024:raise ToolError('roster_too_large','Roster adapter caps input at 64 MiB')
    if data[:4]==bytes.fromhex('ff3bef94'):
        iff=StandardIFF(data);rec=next((r for r in iff.records if r['type']=='ROST'),None)
        if not rec:raise ToolError('roster_not_found','IFF contains no ROST record')
        payload=b''.join(x[3] for x in record_blocks(iff,rec))
        return RosterSource('standard-iff',data,payload,path,iff,rec['index'])
    if data[:4]==b'2kTl':
        typ,blocks=unwrap(data)
        if typ!=21 or len(blocks)!=1:raise ToolError('unsupported_roster_wrapper','Expected ROST wrapper type 21 with one block')
        return RosterSource('tool-wrapper',data,blocks[0],path,wrapper_type=typ)
    if data[:4]==b'PK\x03\x04':
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                matches=[i for i in archive.infolist() if i.filename.replace('\\','/').split('/')[-1].upper()=='USERDATA']
                if len(matches)!=1:raise ToolError('userdata_not_found','ZIP must contain exactly one USERDATA')
                entry=matches[0]
                if entry.flag_bits&1 or entry.file_size>64*1024*1024:raise ToolError('unsupported_save_zip','Encrypted/oversized USERDATA is blocked')
                if sum(i.file_size for i in archive.infolist())>128*1024*1024:raise ToolError('oversized_save_zip','Uncompressed ZIP exceeds limit')
                inner=load_bytes(archive.read(entry),path+'!'+entry.filename)
                if inner.kind!='userdata':raise ToolError('unsupported_save_zip','USERDATA must have a validated length prefix')
                return RosterSource('save-zip',data,inner.payload,path,zip_member=entry.filename,inner=inner)
        except zipfile.BadZipFile as error:raise ToolError('invalid_save_zip',str(error)) from error
    if len(data)>=4 and struct.unpack_from('>I',data)[0]==len(data)-4:return RosterSource('userdata',data,data[4:],path)
    return RosterSource('raw-rost',data,data,path)

def load(path):return load_bytes(Path(path).read_bytes(),str(Path(path).resolve()))
