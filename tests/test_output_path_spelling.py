"""Windows path spellings must not break worker output guards."""
import sys
import uuid
from pathlib import Path

import pytest

from choops_py.archive.manifests import OUTPUT, safe_output, resolved_path


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows extended paths')
def test_worker_extended_path_matches_output_root_and_keeps_protection(monkeypatch, tmp_path):
    original = Path.resolve
    def extended(path, *args, **kwargs):
        result = original(path, *args, **kwargs)
        if path.name == 'worker.bin':
            return Path('\\\\?\\' + str(result))
        return result
    monkeypatch.setattr(Path, 'resolve', extended)
    target = OUTPUT/'temp'/uuid.uuid4().hex/'worker.bin'
    assert safe_output(target) == target
    with pytest.raises(ValueError, match='project output'):
        safe_output(tmp_path/'worker.bin')
    root = OUTPUT/'temp'/('input_'+uuid.uuid4().hex)
    root.mkdir(parents=True)
    protected = root/'worker.bin'; protected.write_bytes(b'source')
    with pytest.raises(ValueError, match='overwrite input'):
        safe_output(protected, [protected])
    assert protected.read_bytes() == b'source'


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows UNC paths')
def test_extended_unc_spelling_normalizes_without_accessing_network(monkeypatch):
    monkeypatch.setattr(Path, 'resolve', lambda self: Path(r'\\?\UNC\server\share\output\worker.bin'))
    assert str(resolved_path('unused')) == r'\\server\share\output\worker.bin'
