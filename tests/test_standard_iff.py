import pytest
pytestmark = pytest.mark.unit
import struct
from support import WorkspaceTest,iff_fixture,literal
from choops_py.formats.standard_iff import StandardIFF
from choops_py.formats.standard_iff_writer import replace_records,record_blocks
from choops_py.formats.compression import decode,encode_like
from choops_py.core.errors import ToolError
class StandardTests(WorkspaceTest):
    def test_parser_pointer_and_raw_roundtrip(self):
        data=iff_fixture();iff=StandardIFF(data);self.assertEqual(iff.records[0]['type'],'TXTR');self.assertEqual(iff.raw,data);self.assertEqual(record_blocks(iff,iff.records[0])[0][3],b'abcd')
        broken=bytearray(data);struct.pack_into('>I',broken,64,0xffffffff)
        with self.assertRaises(ValueError):StandardIFF(bytes(broken))
    def test_writer_preserves_unknown_and_other_block(self):
        data=iff_fixture([b'abcd',b'UNCHANGED'],[(0x5c369069,[0,0])],compressed=True,padding=128);iff=StandardIFF(data)
        result=replace_records(iff,{0:[b'WXYZ',b'UNCHANGED']});new=StandardIFF(result)
        self.assertEqual(len(result),len(data));self.assertEqual(record_blocks(new,new.records[0])[0][3],b'WXYZ')
        old_b=iff.blocks[1];new_b=new.blocks[1];self.assertEqual(data[old_b['start']:old_b['start']+old_b['size']],result[new_b['start']:new_b['start']+new_b['size']])
    def test_size_and_alias_blocked(self):
        iff=StandardIFF(iff_fixture(records=[(0x5c369069,[0]),(0x5c369069,[0])]))
        with self.assertRaises(ToolError):replace_records(iff,{0:[b'WXYZ']})
        with self.assertRaises(ToolError):replace_records(StandardIFF(iff_fixture()),{0:[b'x']})
    def test_h7a_literal_and_reference(self):
        raw=struct.pack('>5I',0x0e4837c3,6,26,7,8)+b'\x08abc\x00\x03'
        self.assertEqual(decode(raw),b'abcabc');self.assertEqual(decode(encode_like(raw,b'abcabd')),b'abcabd');self.assertEqual(encode_like(raw,b'abcabc'),raw)
        with self.assertRaises(ValueError):decode(raw[:-1])
