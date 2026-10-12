"""Batch publication must preserve inputs and leave no incomplete output."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace

import pytest

from choops_py.audio_tools import workflow
from choops_py.archive.manifests import OUTPUT
from choops_py.studio.services import Cancelled

pytestmark = pytest.mark.unit


@pytest.fixture
def batch(tmp_path, monkeypatch):
    archive = SimpleNamespace(path=tmp_path / 'read_only_source')
    rows = [dict(bank='cribmusic', index=i, artist='Artist', title=f'Track {i}') for i in range(2)]
    def export(archive, row, output, job):
        output.write_bytes(b'WAV fixture ' + bytes([row['index']]))
        return dict(output=str(output), source_unchanged=True)
    monkeypatch.setattr(workflow, 'export_track', export)
    parent=OUTPUT/'temp';parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='audio_batch_test_',dir=parent) as directory:
        yield archive, rows, Path(directory) / 'export'


def test_batch_success_publishes_manifest_and_final_paths(batch):
    archive, rows, output = batch
    result = workflow.export_tracks(archive, rows, output)
    assert result['exported'] == 2
    manifest = json.loads((output / 'audio_manifest.json').read_text())
    assert len(manifest['tracks']) == 2
    for row in manifest['tracks']:
        file = output / row['file']
        assert workflow.digest(file.read_bytes()) == row['sha256']
        assert json.loads(file.with_suffix('.audio.json').read_text())['output'] == str(file)
    assert not list(output.parent.glob('.audio_export_*'))


@pytest.mark.parametrize('failure', [ValueError('decode failed'), Cancelled('cancelled')])
def test_failed_batch_removes_only_owned_temporary_folder(batch, monkeypatch, failure):
    archive, rows, output = batch
    unrelated = output.parent / 'keep_user_data'
    unrelated.mkdir()
    keep = unrelated / 'original.wav'
    keep.write_bytes(b'KEEP')
    original = workflow.export_track
    def export(archive, row, path, job):
        if row['index'] == 1:
            raise failure
        return original(archive, row, path, job)
    monkeypatch.setattr(workflow, 'export_track', export)
    with pytest.raises(type(failure)):
        workflow.export_tracks(archive, rows, output)
    assert not output.exists()
    assert not list(output.parent.glob('.audio_export_*'))
    assert keep.read_bytes() == b'KEEP'


def test_existing_batch_destination_is_untouched(batch):
    archive, rows, output = batch
    output.mkdir()
    file = output / 'keep.wav'
    file.write_bytes(b'KEEP')
    with pytest.raises(ValueError, match='new audio export folder'):
        workflow.export_tracks(archive, rows, output)
    assert file.read_bytes() == b'KEEP'
