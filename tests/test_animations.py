from support import WorkspaceTest, iff_fixture

from choops_py.formats.animations import MOCAP_TYPE, inspect_animations
from choops_py.formats.standard_iff import StandardIFF


class MotionExtractionTest(WorkspaceTest):
    def test_motion_family_recognition_and_lossless_compressed_extraction(self):
        clip = b'packed motion bytes\x00' * 10
        raw = iff_fixture([clip + b'KEEP'], [(MOCAP_TYPE, [0]), (0x5c369069, [len(clip)])], compressed=True)
        result = inspect_animations(raw)
        assert result['records'] == [{'index': 0, 'name': '0', 'type': 'SingleMoCap',
                                      'blocks': [{'index': 0, 'decoded_bytes': len(clip)}]}]
        assert not result['skeletal_tracks_decoded']
        files = StandardIFF(raw).dump(self.work, types=('SingleMoCap',))
        assert len(files) == 1 and (self.work / files[0]).read_bytes() == clip
        assert StandardIFF(raw).raw == raw


def test_crowd_placement_is_not_mislabeled_as_animation():
    assert inspect_animations(iff_fixture([b'placements'], [(0xa7701f00, [0])]))['records'] == []
