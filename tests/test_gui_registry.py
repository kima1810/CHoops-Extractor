import pytest
pytestmark = pytest.mark.unit
import unittest
from choops_py.gui import COMMAND_REGISTRY,PANELS
from choops_py.commands import COMMANDS
class RegistryTests(unittest.TestCase):
    def test_focused_registry(self):
        self.assertEqual(len(PANELS),12)
        for name in COMMAND_REGISTRY:self.assertIn(name,COMMANDS)
        labels=' '.join(label for label,_ in PANELS).lower();self.assertNotIn('iso',labels);self.assertNotIn('probe',labels);self.assertIn('roster editor',labels)
