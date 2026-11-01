param()
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$pythonExe = Join-Path $projectRoot '.venv/Scripts/python.exe'
Push-Location $projectRoot
try {
    $env:ZIG_GLOBAL_CACHE_DIR = Join-Path $projectRoot 'output/temp/zig-cache'
    & $pythonExe -m ziglang cc -O3 -shared -target x86_64-windows-gnu choops_py/formats/native/h7a.c -o choops_py/formats/_h7a.dll
    if ($LASTEXITCODE -ne 0) { throw 'Native codec build failed; install build-only ziglang==0.13.0 or use the Python fallback' }
} finally { Pop-Location }
