"""Mac app data must remain writable without modifying the application bundle."""
from pathlib import Path

from choops_py.archive import manifests


def test_frozen_mac_data_outside_bundle(monkeypatch, tmp_path):
    monkeypatch.setattr(manifests.sys, 'frozen', True, raising=False)
    monkeypatch.setattr(manifests.sys, 'platform', 'darwin')
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    expected = tmp_path/'Library/Application Support/CHoops Studio/output'
    assert manifests.output_root() == expected
    monkeypatch.setattr(manifests, 'OUTPUT', expected)
    result = manifests.write_bytes(expected/'reports/test.txt', b'synthetic')
    assert result.read_bytes() == b'synthetic'
    assert not (manifests.ROOT/'reports/test.txt').exists()


def test_other_platforms_retain_existing_output(monkeypatch):
    monkeypatch.setattr(manifests.sys, 'frozen', True, raising=False)
    monkeypatch.setattr(manifests.sys, 'platform', 'win32')
    assert manifests.output_root() == manifests.ROOT/'output'
    monkeypatch.setattr(manifests.sys, 'frozen', False)
    monkeypatch.setattr(manifests.sys, 'platform', 'darwin')
    assert manifests.output_root() == manifests.ROOT/'output'
