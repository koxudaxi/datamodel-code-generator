"""Generate experimental feature documentation and release-note snippets.

Usage:
    python scripts/build_experimental_docs.py
    python scripts/build_experimental_docs.py --check
    python scripts/build_experimental_docs.py --release-notes 0.59.0
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS_PATH = ROOT / "docs" / "experimental.md"
SRC_PATH = ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from datamodel_code_generator.experimental import (  # noqa: E402
    render_experimental_features_markdown,
    render_release_note_experimental_features,
)


def build_docs(*, check: bool) -> int:
    """Generate or check the experimental feature documentation page."""
    content = render_experimental_features_markdown().rstrip() + "\n"

    if check:
        if not DOCS_PATH.exists() or DOCS_PATH.read_text(encoding="utf-8").rstrip() + "\n" != content:
            print("Experimental feature docs are out of date.", file=sys.stderr)
            print("Run 'python scripts/build_experimental_docs.py' to update.", file=sys.stderr)
            return 1
        return 0

    DOCS_PATH.write_text(content, encoding="utf-8")
    return 0


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Build experimental feature documentation")
    parser.add_argument("--check", action="store_true", help="Check whether docs/experimental.md is up to date")
    parser.add_argument(
        "--release-notes",
        metavar="VERSION",
        help="Print release-note experimental feature sections for a version instead of writing docs",
    )
    return parser.parse_args()


def main() -> int:
    """Script entrypoint."""
    args = parse_args()
    if args.release_notes:
        print(render_release_note_experimental_features(args.release_notes), end="")
        return 0
    return build_docs(check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
