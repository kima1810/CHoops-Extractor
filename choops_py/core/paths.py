from pathlib import Path
from ..archive.manifests import OUTPUT, ROOT, safe_output, source_root
from .errors import ToolError

def output_directory(path, sources=(), category=None):
    result = safe_output(path, sources)
    if category and not result.is_relative_to((OUTPUT / category).resolve()):
        raise ToolError("unsafe_output_path", f"This workflow requires output/{category}/")
    result.mkdir(parents=True, exist_ok=True)
    return result

def reject_links(root):
    root = Path(root)
    for p in [root, *root.rglob('*')]:
        if p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction()):
            raise ToolError('linked_input_not_supported', f'Linked path: {p}')
