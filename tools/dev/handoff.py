"""Render the portable master prompt from maintained project documentation."""

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCUMENTS = (
    "CURRENT_STATUS.md",
    "COLLABORATION.md",
    "DEVELOPER_GUIDE.md",
    "AUDIO_RESEARCH.md",
    "AUDIO_WORKFLOW.md",
    "PROJECT_SOURCE_OF_TRUTH.md",
    "projects/01-uniform-preview.md",
    "projects/02-team-uniform-routing.md",
    "projects/03-roster-palettes.md",
    "projects/04-archive-size-and-assets.md",
    "projects/05-roster-usability.md",
    "projects/06-declone-d1-teams.md",
    "projects/07-shoes-and-asset-identities.md",
    "SINGLE_SURFACE_COURT.md",
    "KNOWN_LIMITATIONS.md",
    "TEST_REPORT.md",
)


def render():
    docs = ROOT / "docs"
    content = [
        (docs / "SECONDARY_CODEX_PROMPT.template.md")
        .read_text(encoding="utf8")
        .rstrip()
    ]
    for name in DOCUMENTS:
        content.append(
            "\n---\n\nEmbedded source: docs/"
            + name
            + "\n\n"
            + (docs / name).read_text(encoding="utf8").rstrip()
        )
    return "\n".join(content) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    target = ROOT / "docs/SECONDARY_CODEX_PROMPT.md"
    content = render()
    if args.check:
        if not target.exists() or target.read_text(encoding="utf8") != content:
            raise SystemExit("Master prompt is stale; run python tools/dev/handoff.py")
        print("Master prompt matches maintained documentation.")
    else:
        target.write_text(content, encoding="utf8", newline="\n")
        print("Wrote docs/SECONDARY_CODEX_PROMPT.md")


if __name__ == "__main__":
    main()
