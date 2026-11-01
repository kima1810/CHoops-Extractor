import pytest
pytestmark = pytest.mark.unit
from support import WorkspaceTest,pair_fixture
from choops_py.formats.cdf_backed_iff import CDFPair
class CDFTests(WorkspaceTest):
    def test_bounds_and_preservation(self):
        iff,cdf=pair_fixture();p=CDFPair(iff,cdf);self.assertEqual(p.records[0]['type'],'AUDO');self.assertEqual(p.cdf_name,'x.cdf');self.assertEqual(p.replace('0',b'MODS'),b'HEADMODSTAIL')
        with self.assertRaises(ValueError):p.replace('0',b'x')
        with self.assertRaises(ValueError):CDFPair(iff,cdf[:6])
