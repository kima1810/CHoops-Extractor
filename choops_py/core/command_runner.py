import os
import subprocess
from pathlib import Path
from ..archive.manifests import OUTPUT, safe_output
from .errors import ToolError

def run_tool(argv, cwd, timeout=120):
    """Invoke an executable without a shell, with all temporary data in output/."""
    cwd = safe_output(cwd)
    cwd.mkdir(parents=True, exist_ok=True)
    temp = safe_output(OUTPUT/'temp'); temp.mkdir(parents=True,exist_ok=True)
    env = os.environ.copy(); env.update(TEMP=str(temp), TMP=str(temp), TMPDIR=str(temp))
    try:
        result = subprocess.run([str(x) for x in argv], cwd=cwd, env=env,
                                capture_output=True, text=True, errors='replace',
                                timeout=timeout, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ToolError('converter_execution_failed', str(error)) from error
    return {'argv':[str(x) for x in argv], 'returncode':result.returncode,
            'stdout':result.stdout[-16000:], 'stderr':result.stderr[-16000:]}
