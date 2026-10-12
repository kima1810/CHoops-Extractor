import pytest
pytestmark = pytest.mark.unit
import unittest
from choops_py.formats.binary import Binary,relative_target,relative_value
class BinaryTests(unittest.TestCase):
    def test_helpers_and_bounds(self):
        b=Binary(b'\0\0\0\5A\0\0\0');self.assertEqual(b.u32(0),5);self.assertEqual(b.utf16(4),'A');self.assertEqual(b.relative(0),4)
        self.assertEqual(relative_target(10,relative_value(10,100)),100)
        for off,size in [(-1,1),(0,20)]:
            with self.assertRaises(ValueError):b.slice(off,size)
        with self.assertRaises(ValueError):Binary(b'\0'*4).relative(0)
