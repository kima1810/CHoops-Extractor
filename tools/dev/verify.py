"""Public PR checks: synthetic Python/Qt only, no emulator or game copy."""

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--python", type=Path, help="Override the virtualenv interpreter"
    )
    args = parser.parse_args()
    local = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    executable = args.python or (local if local.is_file() else Path(sys.executable))
    if not executable.is_file():
        raise SystemExit(
            "Create the development environment with tools/dev/setup.py first."
        )
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    checks = [
        ["tools/dev/handoff.py", "--check"],
        [
            "-m",
            "compileall",
            "-q",
            "choops_py",
            "tools/dev",
            "tools/audio_encoder/build.py",
        ],
        [
            "-m",
            "pytest",
            "-q",
            "-m",
            "not real_game and not runtime_manual",
            "-k",
            "not native_reference_matches_descriptors_and_pixels",
        ],
        ["-m", "choops_py.cli", "--help"],
        ["-m", "choops_py.studio", "--smoke"],
        [
            "-m",
            "ruff",
            "check",
            "--isolated",
            "--select",
            "E9,F63,F7,F82",
            "choops_py/studio",
            "choops_py/modding/patch_package.py",
            "choops_py/audio_tools",
            "tools/dev",
        ],
        ["-m", "ruff", "check", "--isolated", "--select", "E,F,I", "tools/dev"],
        [
            "-m",
            "mypy",
            "choops_py/studio",
            "choops_py/modding/patch_package.py",
            "--follow-imports=skip",
            "--ignore-missing-imports",
        ],
    ]
    for check in checks:
        print("Checking:", " ".join(check), flush=True)
        subprocess.run([str(executable), *check], cwd=ROOT, env=env, check=True)
    subprocess.run(["git", "diff", "--check"], cwd=ROOT, check=True)
    print("Portable PR checks passed. Gameplay NOT RUN; testing JB NOT BUILT.")


if __name__ == "__main__":
    main()
