import pytest
pytestmark = pytest.mark.unit
import unittest
from choops_py.formats.tool_wrapper import wrap,unwrap
class WrapperTests(unittest.TestCase):
    def test_roundtrip(self):
        data=wrap(1,[b'abc',b'def']);self.assertEqual(unwrap(data),(1,[b'abc',b'def']));self.assertEqual(unwrap(wrap(0,[])),(0,[]))
        with self.assertRaises(ValueError):unwrap(data[:-1])
