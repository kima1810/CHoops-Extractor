import pytest
pytestmark = pytest.mark.real_game
import os
import unittest
from pathlib import Path
from choops_py.archive.usrdir_reader import Archive
from choops_py.formats.standard_iff import StandardIFF
from choops_py.roster.editor_model import EditorModel
JB=Path(os.environ.get('CHOOPS_JB',str(Path(__file__).resolve().parents[2]/'College Hoops 2K8 (USA)')))
@unittest.skipUnless(JB.exists(),'Proprietary JB fixture absent')
class IntegrationTests(unittest.TestCase):
    def test_real_iff_and_roster(self):
        from choops_py.roster.adapters import load_bytes
        archive=Archive(JB);entry=next(e for e in archive.entries if e['name']=='ua000.iff');self.assertTrue(StandardIFF(archive.read(entry)).records)
        entry=next(e for e in archive.entries if e['name']=='roster_english.iff');model=EditorModel(load_bytes(archive.read(entry)));self.assertTrue(model.validate()['valid']);self.assertEqual(len(model.rows['players']),5685)
