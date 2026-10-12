param()
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$pythonExe = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) { $pythonExe = (Get-Command python).Source }
Push-Location $projectRoot
try {
    $ffmpegExe = Join-Path $projectRoot 'choops_py/audio_tools/bin/choops_ffmpeg.exe'
    $encoderExe = Join-Path $projectRoot 'choops_py/audio_tools/bin/choops_atrac3_encoder.exe'
    $ffmpegSource = Join-Path $projectRoot '.private/vendor/ffmpeg-n9.0.2'
    $encoderSource = Join-Path $projectRoot '.private/vendor/atracdenc'
    if (-not (Test-Path -LiteralPath $ffmpegExe)) { throw 'Build the LGPL FFmpeg helper with tools/audio_codec/build_ffmpeg.sh from an MSYS2 MINGW64 shell.' }
    if (-not (Test-Path -LiteralPath $encoderExe)) { throw 'Build the LGPL ATRAC3 helper with python tools/dev/setup.py --audio-encoder.' }
    if (-not (Test-Path -LiteralPath $ffmpegSource)) { throw 'The pinned FFmpeg source checkout is missing; run tools/audio_codec/build_ffmpeg.sh first.' }
    if (-not (Test-Path -LiteralPath $encoderSource)) { throw 'The pinned AtracDEnc source checkout is missing; run tools/dev/setup.py --audio-encoder first.' }
    $nativeArgs = @('--add-binary', "$ffmpegExe;choops_py/audio_tools/bin", '--add-binary', "$encoderExe;choops_py/audio_tools/bin")
    if (Test-Path -LiteralPath 'choops_py/formats/_h7a.dll') { $nativeArgs += @('--add-binary', 'choops_py/formats/_h7a.dll;choops_py/formats') }
    & $pythonExe -m PyInstaller --noconfirm --onedir --console --name CHoops-Studio --add-data 'choops_py/archive/names.json;choops_py/archive' --add-data 'choops_py/archive/verified_names.json;choops_py/archive' --add-data 'choops_py/audio_tools/soundtrack_names.json;choops_py/audio_tools' --add-data 'choops_py/formats/native/LICENSE.txt;choops_py/formats/native' @nativeArgs --exclude-module av --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets --exclude-module PySide6.QtPdf --exclude-module PySide6.QtQml --exclude-module tkinter tools/rebuild/studio_entry.py
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }
    # Recent Qt uses Windows' unversioned ICU API. An unrelated ICU on PATH
    # can be collected by PyInstaller and shadow that API with suffixed exports.
    $bundleIcu = Join-Path $projectRoot 'dist/CHoops-Studio/_internal/icuuc.dll'
    if (Test-Path -LiteralPath $bundleIcu) {
        $icuImport = & $pythonExe -c "from pathlib import Path; import pefile; p=pefile.PE(str(Path(r'dist/CHoops-Studio/_internal/PySide6/Qt6Core.dll'))); print(int(any(i.dll.lower()==b'icuuc.dll' and any(s.name==b'ucnv_open' for s in i.imports) for i in p.DIRECTORY_ENTRY_IMPORT)))"
        $icuExport = & $pythonExe -c "from pathlib import Path; import pefile; p=pefile.PE(str(Path(r'dist/CHoops-Studio/_internal/icuuc.dll'))); print(int(any(s.name==b'ucnv_open' for s in p.DIRECTORY_ENTRY_EXPORT.symbols)))"
        if ($icuImport -eq '1' -and $icuExport -eq '0') { Remove-Item -LiteralPath $bundleIcu }
    }
    # Include exact codec sources and notices with the LGPL helpers.
    $codecSources = Join-Path $projectRoot 'dist/CHoops-Studio/THIRD-PARTY-SOURCES'
    New-Item -ItemType Directory -Force -Path $codecSources | Out-Null
    $ffmpegArchive = Join-Path $codecSources 'ffmpeg-n9.0.2.tar.gz'
    & git -C $ffmpegSource archive --format=tar.gz --prefix=ffmpeg-n9.0.2/ "--output=$ffmpegArchive" 946fcce07b6dcd0331c8cc609192aeff5e1924f8
    if ($LASTEXITCODE -ne 0) { throw 'Could not package the pinned FFmpeg corresponding source.' }
    Copy-Item -LiteralPath (Join-Path $ffmpegSource 'COPYING.LGPLv2.1') -Destination $codecSources
    Copy-Item -LiteralPath (Join-Path $projectRoot 'tools/audio_codec/build_ffmpeg.sh') -Destination $codecSources
    $encoderArchive = Join-Path $codecSources 'atracdenc.tar.gz'
    & git -C $encoderSource archive --format=tar.gz --prefix=atracdenc/ "--output=$encoderArchive" cb170709f836cb43dc0312455188c791159d81dc
    if ($LASTEXITCODE -ne 0) { throw 'Could not package the pinned AtracDEnc corresponding source.' }
    Copy-Item -LiteralPath 'tools/audio_encoder/encoder.cpp', 'tools/audio_encoder/build.py', 'tools/audio_encoder/LICENSE.txt', 'tools/audio_encoder/README.md', 'tools/audio_codec/THIRD-PARTY-NOTICES.txt' -Destination $codecSources
    # Independent DDS conversion is included. Legacy converters are not bundled.
    Copy-Item -LiteralPath README.md, docs/USER_GUIDE.md, docs/rebuild/CONVERTER_PROVENANCE.md -Destination dist/CHoops-Studio
    Copy-Item -LiteralPath docs/AUDIO_WORKFLOW.md -Destination dist/CHoops-Studio
    Set-Content -LiteralPath dist/CHoops-Studio/README-START-HERE.txt -Value 'Run CHoops-Studio.exe. CLI: CHoops-Studio.exe --cli --help. DDS conversion and the Audio workspace are available. Audio WAV import/export uses separately built LGPL FFmpeg and ATRAC3 helpers; corresponding source archives and license notices are in THIRD-PARTY-SOURCES. No PyAV/FFmpeg GPL wheel or game assets are included. External texture converters are not included. See USER_GUIDE.md and AUDIO_WORKFLOW.md. Gameplay is unverified.'
    & dist/CHoops-Studio/CHoops-Studio.exe --smoke
    if ($LASTEXITCODE -ne 0) { throw 'Packaged Qt smoke failed' }
    & dist/CHoops-Studio/CHoops-Studio.exe --audio-codec-smoke
    if ($LASTEXITCODE -ne 0) { throw 'Packaged audio codec round-trip smoke failed' }
} finally { Pop-Location }
