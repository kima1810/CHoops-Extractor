import pytest
pytestmark = pytest.mark.unit
from support import WorkspaceTest,iff_fixture,game_fixture
from choops_py.archive.hash_names import namespace,hash_name,lookup
from choops_py.archive.usrdir_reader import Archive
from choops_py.archive import cache
class CacheTests(WorkspaceTest):
    def test_names_and_archive(self):
        names=set(namespace());self.assertIn('ua800.iff',names);self.assertIn('h9999.iff',names);self.assertEqual(lookup()[hash_name('ua000.iff')],'ua000.iff')
        payload=iff_fixture();source=game_fixture(self.work/'source',payload);archive=Archive(source);self.assertTrue(archive.read(archive.entries[0]).startswith(payload));path=cache.build(source)
        self.assertEqual(cache.info(source)['schema'],3);path.unlink()
