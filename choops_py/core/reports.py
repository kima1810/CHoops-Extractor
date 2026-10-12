import json
import os
import uuid
from pathlib import Path
from ..archive.manifests import safe_output, OUTPUT

def save_json(path, data, sources=()):
    """Atomically replace a generated report/config, never a source input."""
    path = safe_output(path, sources)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / ('.r_'+uuid.uuid4().hex[:12]+'.tmp')
    try:
        with temporary.open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(data, stream, indent=2, ensure_ascii=False)
            stream.write('\n')
        os.replace(temporary, path)
    finally:
        if Path(temporary).exists(): Path(temporary).unlink()
    return path

def import_report(data):
    save_json(OUTPUT/'reports'/'texture_import_report.json', data)
    path = safe_output(OUTPUT/'reports'/'texture_import_report.md')
    path.write_text('# Texture import report\n\n'+json.dumps(data,indent=2)+'\n', encoding='utf-8')
