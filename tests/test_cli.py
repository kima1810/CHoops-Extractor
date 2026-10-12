import pytest
pytestmark = pytest.mark.unit
import contextlib
import io
from support import WorkspaceTest,iff_fixture
from choops_py.cli import main,parser,SPECS
from choops_py.archive.manifests import OUTPUT,safe_output
class CLITests(WorkspaceTest):
    def test_registration_and_no_removed_commands(self):
        sub=next(a for a in parser()._actions if getattr(a,'choices',None));self.assertEqual(set(sub.choices),set(SPECS)|{'gui'})
        self.assertNotIn('build-iso',sub.choices);self.assertNotIn('build-iso-folder',sub.choices)
        for name in ('export-dds','import-dds','roster-save','test-texture-tools','build-copy'):self.assertIn(name,sub.choices)
    def test_help_roundtrip_and_output_safety(self):
        with contextlib.redirect_stdout(io.StringIO()),self.assertRaises(SystemExit) as e:main(['--help'])
        self.assertEqual(e.exception.code,0);source=self.work/'in.iff';source.write_bytes(iff_fixture());out=self.work/'out.iff'
        with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(main(['round-trip-iff',str(source),str(out),'--compare']),0)
        self.assertEqual(source.read_bytes(),out.read_bytes())
        with self.assertRaises(ValueError):safe_output(OUTPUT.parent/'unsafe')
        with self.assertRaises(ValueError):safe_output(source,[source])
        folder=self.work/'vanilla';folder.mkdir()
        with self.assertRaises(ValueError):safe_output(folder/'bad',[folder])
