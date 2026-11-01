import io
import json
import struct

import pytest
from PIL import Image

from support import iff_fixture,txtr_fixture
from choops_py.archive.folder_import import discover,compile_group
from choops_py.archive.hash_names import replacement_hash
from choops_py.archive.iff_validation import standard_iff
from choops_py.formats.cdf_backed_iff_writer import name_trailer
from choops_py.formats.standard_iff import StandardIFF
from choops_py.formats.standard_iff_writer import record_blocks
from choops_py.formats.txtr import TXTR
from choops_py.texture_tools.builtin_converter import to_dds
from choops_py.studio.build_diagnostics import diagnose


@pytest.mark.parametrize('kind',['TXTR','SCNE'])
def test_manifest_flat_cube_preserves_five_faces_and_unknown_header(tmp_path,kind):
    header=bytearray(txtr_fixture(format=0xa5,split=True)[0]);header[0x5b]=1
    struct.pack_into('>I',header,0x68,16);struct.pack_into('>I',header,0xa4,1)
    faces=b''.join(bytes((i,20+i,40+i,255))*16 for i in range(6))
    original=TXTR([bytes(header),faces]);base=to_dds(original.gtf())
    if kind=='SCNE':
        scene=bytearray(320);struct.pack_into('>II',scene,0x20,1,128-0x24+1);scene[128:304]=header
        parts=[bytes(scene),faces];selector='scene/texture_0';name='scene';tag=0xe26c9b5d
    else:parts=[bytes(header),faces];selector='texture';name='texture';tag=0x5c369069
    source=iff_fixture(parts,[(tag,[0,0])])+name_trailer([dict(name=name,type=kind)])
    entry=dict(name='menu.iff',hash=replacement_hash('menu.iff'),size=len(source),index=0,offset=0)
    class MemoryArchive:
        entries=[entry]
        def read(self,entry):return source[entry['offset']:entry['offset']+entry['size']]
    folder=tmp_path/'overrides';folder.mkdir()
    output=io.BytesIO();Image.new('RGBA',(8,8),(255,0,0,255)).save(output,format='DDS')
    (folder/'image.dds').write_bytes(output.getvalue())
    (folder/'manifest.json').write_text(json.dumps(dict(source='menu.iff',textures=[dict(texture_name=selector,dds_output_path='image.dds')])),encoding='utf8')
    group=discover(MemoryArchive(),folder)['groups'][0]
    assert group['dds_rank'][selector]==3
    result,reports=compile_group(MemoryArchive(),group);parsed=StandardIFF(result)
    changed=[v[3] for v in record_blocks(parsed,parsed.records[0])]
    if kind=='SCNE':
        from choops_py.formats.package import textures
        item=textures(changed)[0];changed=[item.header,item.payload]
    cube=TXTR(changed);actual=to_dds(cube.gtf())
    assert cube.info()['cubemap'] and changed[0][:0xa4]==original.blocks[0][:0xa4]
    assert actual[128+64:]==base[128+64:] and actual[128:192]!=base[128:192]
    assert any(r.get('cubemap_face_updated')=='+X' and r['cubemap_faces_preserved']==5 for r in reports)
    assert source.startswith(bytes.fromhex('ff3bef94'))


def test_wrong_container_identifies_archive_role_magic_and_keeps_rejection():
    with pytest.raises(ValueError,match=r'legalpage.iff .*replacement.*magic=326b546c.*Not a standard') as failure:
        standard_iff(b'2kTl'+bytes(32),'legalpage.iff','replacement')
    assert 'complete' in diagnose(failure.value)['problem']
    with pytest.raises(ValueError,match='menu.iff.*magic=empty'):
        standard_iff(b'','menu.iff','source')


def test_structural_errors_keep_their_error_code_and_context():
    from choops_py.core.errors import ToolError
    from unittest.mock import patch
    with patch('choops_py.archive.iff_validation.StandardIFF',side_effect=ToolError('unsupported','metadata')):
        with pytest.raises(ToolError) as failure:standard_iff(b'abcd','menu.iff','source')
    assert failure.value.code=='unsupported' and 'menu.iff' in str(failure.value)


def test_paired_cdf_flat_cube_keeps_other_faces(tmp_path):
    from test_cdf_folder_import import logo_pair,memory_archive
    from choops_py.formats.cdf_backed_iff import CDFPair
    from choops_py.formats.cdf_backed_iff_writer import replace_texture_records
    from choops_py.formats.compression import decode
    metadata,payload=logo_pair()
    header=bytearray(txtr_fixture(format=0xa5,split=True)[0]);header[0x5b]=1
    struct.pack_into('>I',header,0x68,16)
    faces=b''.join(bytes((i,20+i,40+i,255))*16 for i in range(6))
    base=TXTR([bytes(header),faces]);metadata,payload=replace_texture_records(metadata,payload,{0:base.blocks})
    folder=tmp_path/'logos'/'_logo001.txtr';folder.mkdir(parents=True)
    artwork=io.BytesIO();Image.new('RGBA',(8,8),(255,0,0,255)).save(artwork,format='DDS')
    (folder/'logo001.dds').write_bytes(artwork.getvalue())
    archive=memory_archive(metadata,payload);group=discover(archive,tmp_path)['groups'][0]
    rebuilt,reports=compile_group(archive,group);_,_,cdf=group['compiled_companion']
    rec=CDFPair(rebuilt,cdf).records[0]
    result=TXTR([decode(cdf[rec[k+'_offset']:rec[k+'_offset']+rec[k+'_length']]) for k in ('header','payload')])
    assert result.info()['cubemap']
    assert to_dds(result.gtf())[192:]==to_dds(base.gtf())[192:]
    assert any(r.get('cubemap_faces_preserved')==5 for r in reports)
