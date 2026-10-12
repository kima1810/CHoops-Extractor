import struct
import zlib
from support import literal,txtr_fixture
from choops_py.archive.hash_names import hash_name
from choops_py.archive.folder_import import discover,compile_group
from choops_py.formats.cdf_backed_iff import CDFPair
from choops_py.formats.cdf_backed_iff_writer import name_trailer,replace_texture_records
from choops_py.formats.compression import decode
from choops_py.formats.txtr import TXTR
from choops_py.texture_tools.dds import compressed_preview


def logo_pair():
    name='logos.cdf';end=148+len(name.encode('utf-16-be'))+2
    header=bytearray(end);parts=txtr_fixture(format=0x86,split=True)
    stored=[literal(p) for p in parts]
    struct.pack_into('>10I',header,0,0xf0985030,end,end,0,2,21,1,77,97,113)
    for j,p in enumerate(parts):
        struct.pack_into('>8I',header,40+j*32,1,1,16 if j==0 else 128,len(p),0,end+j*176,len(p),0)
    struct.pack_into('>I',header,104,5)
    struct.pack_into('>5I',header,108,zlib.crc32(b'logo001'),0x5c369069,2,0,0)
    struct.pack_into('>I',header,128,5)
    struct.pack_into('>4I',header,132,0,len(stored[0]),len(stored[0]),len(stored[1]))
    header[148:]=name.encode('utf-16-be')+b'\0\0'
    return bytes(header)+name_trailer([{'name':'logo001','type':'TXTR'}]),b''.join(stored)


def memory_archive(metadata,payload):
    class MemoryArchive:
        entries=[dict(hash=hash_name('logos.iff'),name='logos.iff',size=len(metadata),offset=0),
                 dict(hash=hash_name('logos.cdf'),name='logos.cdf',size=len(payload),offset=0)]
        def read(self,entry):
            data=metadata if entry['name']=='logos.iff' else payload
            return data[entry.get('offset',0):entry.get('offset',0)+entry['size']]
        def chunks(self,entry,size):yield self.read(entry)[:size]
    return MemoryArchive()


def test_cdf_dds_discovery_preserves_base_layout(tmp_path):
    metadata,cdf=logo_pair()
    folder=tmp_path/'overrides'/'logos'/'_logo001.txtr';folder.mkdir(parents=True)
    image=b'\x12'*64
    (folder/'logo001.dds').write_bytes(compressed_preview(8,8,'DXT5',image))
    archive=memory_archive(metadata,cdf);groups=discover(archive,tmp_path/'overrides')['groups']
    assert len(groups)==1
    rebuilt,details=compile_group(archive,groups[0])
    _,name,payload=groups[0]['compiled_companion']
    assert name=='logos.cdf' and details[0]['width']==4
    pair=CDFPair(rebuilt,payload);r=pair.records[0]
    parts=[decode(payload[r[k+'_offset']:r[k+'_offset']+r[k+'_length']]) for k in ('header','payload')]
    assert TXTR(parts).info()['width']==4 and TXTR(parts).info()['format']=='DXT1'
    assert len(TXTR(parts).image())==8
    assert any(detail.get('storage_layout_preserved') and detail.get('artwork_resampled') for detail in details)


def test_cdf_writer_preserves_unchanged_record_content():
    metadata,payload=logo_pair()
    rebuilt,cdf=replace_texture_records(metadata,payload,{})
    before=CDFPair(metadata,payload);after=CDFPair(rebuilt,cdf)
    for old,new in zip(before.records,after.records):
        for k in ('header','payload'):
            assert decode(payload[old[k+'_offset']:old[k+'_offset']+old[k+'_length']])==decode(cdf[new[k+'_offset']:new[k+'_offset']+new[k+'_length']])


def test_cdf_only_replacement_automatically_uses_paired_import(tmp_path):
    metadata,payload=logo_pair();archive=memory_archive(metadata,payload)
    (tmp_path/'logos.cdf').write_bytes(payload)
    groups=discover(archive,tmp_path)['groups']
    assert len(groups)==1 and groups[0]['name']=='logos.iff' and groups[0]['cdf_whole']
    rebuilt,_=compile_group(archive,groups[0])
    assert groups[0]['compiled_companion'][1]=='logos.cdf'
    CDFPair(rebuilt,groups[0]['compiled_companion'][2])


def test_legacy_cdf_record_folder_resolves_generic_artwork_name(tmp_path):
    metadata,payload=logo_pair()
    class MemoryArchive:
        entries=[dict(hash=hash_name('logos.iff'),name='logos.iff',size=len(metadata),offset=0),
                 dict(hash=hash_name('logos.cdf'),name='logos.cdf',size=len(payload),offset=0)]
        def read(self,entry):
            data=metadata if entry['name']=='logos.iff' else payload
            return data[entry.get('offset',0):entry.get('offset',0)+entry['size']]
        def chunks(self,entry,size):yield self.read(entry)[:size]
    folder=tmp_path/'logos'/'TXTR'/'logo001';folder.mkdir(parents=True)
    image=b'\x12'*64
    (folder/'logo.dds').write_bytes(compressed_preview(8,8,'DXT5',image))
    archive=MemoryArchive();group=discover(archive,tmp_path)['groups'][0]
    assert list(group['dds'])==['logo001']
    rebuilt,details=compile_group(archive,group)
    assert details[0]['selector']=='logo001'
    _,_,cdf=group['compiled_companion'];rec=CDFPair(rebuilt,cdf).records[0]
    blocks=[decode(cdf[rec[k+'_offset']:rec[k+'_offset']+rec[k+'_length']]) for k in ('header','payload')]
    assert TXTR(blocks).info()['width']==4 and TXTR(blocks).info()['format']=='DXT1'
