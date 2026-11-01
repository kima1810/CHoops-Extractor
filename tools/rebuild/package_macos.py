"""Build a native Mac app and include exact LGPL corresponding sources."""
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run(*args, **kwargs):
    subprocess.run([str(arg) for arg in args], cwd=ROOT, check=True, **kwargs)


def main():
    if sys.platform != 'darwin':
        raise SystemExit('Build on macOS with a native Python interpreter.')
    helpers = [ROOT/'choops_py/audio_tools/bin'/name
               for name in ('choops_ffmpeg', 'choops_atrac3_encoder')]
    for helper in helpers:
        if not helper.is_file():
            raise SystemExit(f'Build the native audio helper first: {helper.name}')
    args = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
            '--onedir', '--windowed', '--name', 'CHoops-Studio',
            '--osx-bundle-identifier', 'org.choopsreborn.studio',
            '--target-architecture', platform.machine()]
    for relative in ('archive/names.json', 'archive/verified_names.json',
                     'audio_tools/soundtrack_names.json', 'formats/native/LICENSE.txt'):
        source = ROOT/'choops_py'/relative
        args += ['--add-data', f'{source}:choops_py/{Path(relative).parent.as_posix()}']
    for helper in helpers:
        args += ['--add-binary', f'{helper}:choops_py/audio_tools/bin']
    for module in ('av', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
                   'PySide6.QtPdf', 'PySide6.QtQml', 'tkinter'):
        args += ['--exclude-module', module]
    run(*args, 'tools/rebuild/studio_entry.py')
    package = ROOT/'dist'/f'CHoops-Studio-macos-{platform.machine()}'
    package.mkdir(exist_ok=False)
    run('ditto', ROOT/'dist/CHoops-Studio.app', package/'CHoops-Studio.app')
    shutil.copytree(ROOT/'docs', package/'docs')
    shutil.copy2(ROOT/'README.md', package)
    sources = package/'THIRD-PARTY-SOURCES'
    sources.mkdir()
    for directory, revision, filename, prefix in (
        ('ffmpeg-n9.0.2', '946fcce07b6dcd0331c8cc609192aeff5e1924f8',
         'ffmpeg-n9.0.2.tar.gz', 'ffmpeg-n9.0.2/'),
        ('atracdenc', 'cb170709f836cb43dc0312455188c791159d81dc',
         'atracdenc.tar.gz', 'atracdenc/'),
    ):
        vendor = ROOT/'.private/vendor'/directory
        # Match the compiled source tree, not just the requested archive revision.
        actual = subprocess.check_output(['git', '-C', str(vendor), 'rev-parse', 'HEAD'], text=True).strip()
        dirty = subprocess.check_output(['git', '-C', str(vendor), 'status', '--porcelain'], text=True)
        if actual != revision or dirty.strip():
            raise SystemExit('Codec source identity/cleanliness check failed: '+directory)
        run('git', '-C', vendor, 'archive', '--format=tar.gz', '--prefix='+prefix,
            '--output='+str(sources/filename), revision)
    for relative in ('tools/audio_codec/build_ffmpeg.sh', 'tools/audio_codec/THIRD-PARTY-NOTICES.txt',
                     'tools/audio_encoder/encoder.cpp', 'tools/audio_encoder/build.py',
                     'tools/audio_encoder/LICENSE.txt', 'tools/audio_encoder/README.md'):
        shutil.copy2(ROOT/relative, sources)
    shutil.copy2(ROOT/'.private/vendor/ffmpeg-n9.0.2/COPYING.LGPLv2.1', sources)
    (package/'README-START-HERE.txt').write_text(
        'Move CHoops-Studio.app to Applications. Requires macOS 13 or newer.\n'
        'This app is ad-hoc signed, not Apple-notarized. See docs/MACOS.md for opening instructions.\n'
        'Writable data: ~/Library/Application Support/CHoops Studio/output.\n'
        'Audio helpers, corresponding sources and notices are included. No game assets.\n', encoding='utf8')
    executable = package/'CHoops-Studio.app/Contents/MacOS/CHoops-Studio'
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
    for option in ('--smoke', '--audio-codec-smoke'):
        run(executable, option, env=env)
    run(executable, '--cli', '--help', env=env)
    graphics_env = dict(os.environ, QT_QPA_PLATFORM='cocoa')
    run(executable, '--render-smoke', env=graphics_env)
    run('codesign', '--verify', '--deep', '--strict', package/'CHoops-Studio.app')


if __name__ == '__main__':
    main()
