"""Archive only the distributable, with source identity and SHA-256 evidence."""
import hashlib
import json
import platform
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from choops_py import __version__  # noqa: E402


def main():
    mac = sys.platform == 'darwin'
    system = 'macos' if mac else 'windows'
    arch = platform.machine().lower()
    if not mac:
        if sys.platform != 'win32' or arch not in ('amd64', 'x86_64'):
            raise SystemExit('Only native macOS and Windows x64 releases are supported.')
        arch = 'x64'
    package = ROOT/'dist'/('CHoops-Studio-macos-'+arch if mac else 'CHoops-Studio')
    if not package.is_dir():
        raise SystemExit('Build the native package before archiving.')
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    (package/'BUILD-INFO.json').write_text(json.dumps({
        'version': __version__, 'source_commit': sha, 'platform': system,
        'architecture': arch, 'python': platform.python_version(),
        'apple_notarized': False if mac else None,
        'gameplay_tested': False,
    }, indent=2)+'\n', encoding='utf8')
    release = ROOT/'dist/release'
    release.mkdir(exist_ok=True)
    filename = f'CHoops-Studio-v{__version__}-{system}-{arch}.zip'
    archive = release/filename
    if mac:
        # ditto preserves executable bits, framework symlinks and app metadata.
        subprocess.run(['ditto', '-c', '-k', '--sequesterRsrc', '--keepParent',
                        str(package), str(archive)], check=True)
    else:
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as target:
            for path in sorted(package.rglob('*')):
                relative = path.relative_to(package)
                if relative.parts[0] == 'output':
                    continue  # Never distribute smoke caches/settings/logs.
                if path.is_file():
                    target.write(path, package.name+'/'+relative.as_posix())
    with zipfile.ZipFile(archive) as target:
        if target.testzip() is not None:
            raise SystemExit('Release ZIP failed its CRC check.')
        for name in target.namelist():
            parts = Path(name).parts
            if any(part in ('.private', '.git', '.venv', '__pycache__') for part in parts):
                raise SystemExit('Private/development file found in release archive.')
    with archive.open('rb') as source:
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
    (release/(filename+'.sha256')).write_text(digest+'  '+filename+'\n', encoding='ascii')
    print(filename, digest)


if __name__ == '__main__':
    main()
