import pytest
pytestmark = pytest.mark.integration
from support import WorkspaceTest,iff_fixture,game_fixture
from choops_py.archive.importer import stage,validate
from choops_py.archive.build_copy import build
from choops_py.core.errors import ToolError
class ModTests(WorkspaceTest):
    def test_staging_dry_run_build_and_safe_overwrite(self):
        source=game_fixture(self.work/'source',iff_fixture());payload=self.work/'payload';payload.write_bytes(b'WXYZ');mod=self.work/'mod';stage(mod,payload,'ua000.iff','0');self.assertEqual(len(validate(mod)),1)
        before=(source/'PS3_GAME'/'USRDIR'/'0A').read_bytes();out=self.build_path();self.assertTrue(build(source,mod,out,dry_run=True)['dry_run']);self.assertFalse(out.exists())
        report=build(source,mod,out);self.assertTrue(report['vanilla_inventory_unchanged']);self.assertEqual((source/'PS3_GAME'/'USRDIR'/'0A').read_bytes(),before)
        self.assertEqual((out/'PS3_GAME'/'USRDIR'/'0A').read_bytes()[2048+84:2048+88],b'WXYZ');build(source,mod,out,overwrite=True)
    def test_unsafe_paths_staging_and_unowned_output(self):
        file=self.work/'x';file.write_bytes(b'x')
        with self.assertRaises(ToolError):stage(self.work/'bad',file,'../oops')
        source=game_fixture(self.work/'source',iff_fixture());mod=self.work/'mod';mod.mkdir();out=self.build_path();out.mkdir();(out/'important').write_bytes(b'keep')
        with self.assertRaises(ToolError):build(source,mod,out,overwrite=True)
        self.assertEqual((out/'important').read_bytes(),b'keep')
        with self.assertRaises(ValueError):build(source,mod,source/'output',dry_run=True)
