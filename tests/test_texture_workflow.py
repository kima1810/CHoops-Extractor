import pytest
pytestmark = pytest.mark.unit
import os
import struct
from pathlib import Path
from unittest.mock import patch
from support import WorkspaceTest,txtr_fixture,iff_fixture
from choops_py.formats.txtr import TXTR
from choops_py.formats.tool_wrapper import wrap,unwrap
from choops_py.formats.package import textures,replace_texture
from choops_py.texture_tools import dds,gtf,external_converters
from choops_py.texture_tools.pipeline import export,import_texture
from choops_py.archive.manifests import ROOT
from choops_py.core.errors import ToolError
class TextureTests(WorkspaceTest):
    def test_txtr_inline_split_and_wrapper_preservation(self):
        for split in (False,True):
            texture=TXTR(txtr_fixture(split=split),1);before=texture.serialize();parsed=TXTR.from_bytes(before);self.assertEqual(parsed.info()['width'],4)
            new=parsed.replace_image(b'Z'*16);self.assertTrue(new.blocks[-1].endswith(b'KEEP'));self.assertEqual(new.blocks[0][:0xb0],parsed.blocks[0][:0xb0]);self.assertEqual(unwrap(new.serialize())[0],1)
    def test_package_texture_preserves_geometry(self):
        texture=TXTR(txtr_fixture(split=True));header=bytearray(0x54)+bytearray(texture.blocks[0]);struct.pack_into('>II',header,0x20,1,0x54-0x24+1);struct.pack_into('>I',header,0x54+0xa4,1);blocks=[bytes(header),texture.blocks[1]+b'GEOMETRY']
        items=textures(blocks);self.assertEqual(items[0].index,0);result=replace_texture(blocks,0,b'Q'*16,16);self.assertEqual(result[0],blocks[0]);self.assertEqual(result[1][16:],blocks[1][16:])
    def test_dds_bounds_format_and_payload_size(self):
        data=dds.linear_l8(4,4,1,b'Z'*16);self.assertEqual(dds.inspect(data)['format'],'L8')
        with self.assertRaises(ToolError):dds.inspect(data[:-1])
        broken=bytearray(data);struct.pack_into('<I',broken,16,8)
        with self.assertRaises(ToolError):dds.inspect(bytes(broken))
    def test_builtin_conversion_works_without_external_executables(self):
        source=self.work/'input.txtr';source.write_bytes(txtr_fixture()[0])
        with patch('choops_py.texture_tools.external_converters.find',return_value=None):
            result=export(source,self.work/'export');entry=result['textures'][0];self.assertEqual(entry['converter_status'],'success');self.assertTrue(Path(entry['raw_output_path']).exists());self.assertTrue(Path(entry['gtf_output_path']).exists());self.assertTrue(Path(entry['dds_output_path']).exists())
            replacement=self.work/'input.dds';replacement.write_bytes(dds.linear_l8(4,4,1,b'X'*16))
            imported=import_texture(source,'input',replacement,self.work/'result.txtr')
            self.assertEqual(imported['status'],'success')
            self.assertEqual(TXTR.from_bytes((self.work/'result.txtr').read_bytes()).image(),b'X'*16)
    def test_converter_failure_preserves_raw(self):
        source=self.work/'input.txtr';source.write_bytes(txtr_fixture(format=0x86)[0])
        with patch('choops_py.texture_tools.external_converters.convert',side_effect=ToolError('conversion_failed','test failure')):
            result=export(source,self.work/'export');self.assertEqual(result['textures'][0]['converter_status'],'conversion_failed');self.assertEqual(result['raw_exported'],1)
    def test_bundled_paths_have_precedence(self):
        # Discovery precedence needs a synthetic file, not a proprietary binary
        # that is deliberately absent from a clean public clone.
        tools=self.work/'tools';tools.mkdir();bundled=tools/'gtf2dds.exe'
        bundled.write_bytes(b'synthetic discovery fixture; never executed')
        with patch.object(external_converters,'ROOT',self.work),patch.object(external_converters,'configured',return_value={'gtf2dds':'missing'}):
            self.assertEqual(external_converters.find('gtf2dds','other'),bundled.resolve())
    def test_absent_legacy_tools_do_not_block_builtin_readiness(self):
        with patch.object(external_converters,'ROOT',self.work),patch.object(external_converters,'configured',return_value={}):
            self.assertIsNone(external_converters.find('gtf2dds'))
            self.assertTrue(external_converters.status(check=False)['export_dds_ready'])
    def test_wrong_dimensions_block_before_output(self):
        source=self.work/'input.txtr';source.write_bytes(txtr_fixture()[0]);file=self.work/'input.dds';file.write_bytes(dds.linear_l8(8,4,1,b'X'*32))
        with self.assertRaises(ToolError) as error:import_texture(source,'input',file,self.work/'result.txtr')
        self.assertEqual(error.exception.code,'texture_width_mismatch');self.assertFalse((self.work/'result.txtr').exists())
    @pytest.mark.windows
    @__import__('unittest').skipUnless(os.name=='nt','Bundled converters are Windows executables')
    def test_real_bundled_dds_roundtrip(self):
        source=self.work/'input.txtr';source.write_bytes(txtr_fixture()[0]);result=export(source,self.work/'export');file=Path(result['textures'][0]['dds_output_path']);modified=bytearray(file.read_bytes());modified[128]^=1;edited=self.work/'edited.dds';edited.write_bytes(modified)
        imported=import_texture(source,'input',edited,self.work/'result.txtr');self.assertEqual(imported['status'],'success');new=TXTR.from_bytes((self.work/'result.txtr').read_bytes());self.assertEqual(new.image()[0],modified[128]);self.assertEqual(new.blocks[0][-4:],b'KEEP')
