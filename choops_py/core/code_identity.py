"""Fingerprint Python modules in source checkouts and frozen Windows bundles."""
import importlib.util
import marshal
from pathlib import Path


def module_bytes(name):
    spec=importlib.util.find_spec(name)
    if spec is None:raise ValueError('Cannot fingerprint conversion module: '+name)
    if spec.origin:
        path=Path(spec.origin)
        if path.suffix=='.py' and path.is_file():return path.read_bytes()
    code=spec.loader.get_code(name) if hasattr(spec.loader,'get_code') else None
    if code is None:raise ValueError('Cannot fingerprint frozen conversion module: '+name)
    return marshal.dumps(code)
