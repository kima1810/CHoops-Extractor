"""Portable development setup; does not read game inputs or create JB builds."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVISION = "cb170709f836cb43dc0312455188c791159d81dc"


def run(args):
    subprocess.run([str(arg) for arg in args], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check existing dependencies without installing",
    )
    parser.add_argument(
        "--audio-encoder",
        action="store_true",
        help="Fetch pinned LGPL sources and build the native helper",
    )
    args = parser.parse_args()
    if sys.version_info < (3, 11):  # noqa: UP036 - setup can be launched outside the project interpreter
        raise SystemExit("Python 3.11+ required; Python 3.12 x64 is the CI baseline.")
    executable = (
        ROOT
        / ".venv"
        / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    )
    if not executable.is_file():
        if args.check:
            raise SystemExit("Missing .venv; run setup without --check first.")
        run([sys.executable, "-m", "venv", ROOT / ".venv"])
    if not args.check:
        run([executable, "-m", "pip", "install", "-e", ".[dev]"])
    probe = (
        "import PySide6,PIL,pytest,pytestqt,ruff,mypy,psutil,PyInstaller; "
        "print('Desktop/development dependencies import successfully')"
    )
    run([executable, "-c", probe])
    if args.audio_encoder:
        if args.check:
            raise SystemExit(
                "--check cannot fetch/build; use --audio-encoder separately."
            )
        if sys.platform != "darwin":
            run([executable, "-m", "pip", "install", "ziglang==0.13.0"])
        source = ROOT / ".private/vendor/atracdenc"
        source.parent.mkdir(parents=True, exist_ok=True)
        if not source.exists():
            run(["git", "clone", "https://github.com/dcherednik/atracdenc.git", source])
        actual = subprocess.check_output(
            ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
        ).strip()
        if actual != REVISION:
            dirty = subprocess.check_output(
                ["git", "-C", str(source), "status", "--porcelain"], text=True
            )
            if dirty.strip():
                raise SystemExit(
                    "Encoder source has local changes; preserve them before checkout."
                )
            run(["git", "-C", source, "fetch", "origin", REVISION])
            run(["git", "-C", source, "checkout", "--detach", REVISION])
        run([executable, ROOT / "tools/audio_encoder/build.py", source])
    versions = subprocess.check_output(
        [str(executable), "-m", "pip", "freeze"], text=True
    )
    report = ROOT / "output/reports/dev-setup.txt"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(versions, encoding="utf8")
    print(
        json.dumps(
            {
                "dependencies_checked": True,
                "encoder_requested": args.audio_encoder,
                "private_report": str(report.relative_to(ROOT)),
                "jb_built": False,
            }
        )
    )


if __name__ == "__main__":
    main()
