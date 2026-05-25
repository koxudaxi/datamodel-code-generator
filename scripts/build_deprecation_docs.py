"""Generate deprecation documentation and release-note snippets.

Usage:
    python scripts/build_deprecation_docs.py
    python scripts/build_deprecation_docs.py --check
    python scripts/build_deprecation_docs.py --release-notes 0.58.0
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS_PATH = ROOT / "docs" / "deprecations.md"
SRC_PATH = ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from datamodel_code_generator.deprecations import (  # noqa: E402
    render_deprecations_markdown,
    render_release_note_deprecations,
)


def build_docs(*, check: bool) -> int:
    """Generate or check the deprecation documentation page."""
    content = render_deprecations_markdown()

    if check:
        if not DOCS_PATH.exists() or DOCS_PATH.read_text(encoding="utf-8") != content:
            print("Deprecation docs are out of date.", file=sys.stderr)
            print("Run 'python scripts/build_deprecation_docs.py' to update.", file=sys.stderr)
            return 1
        return 0

    DOCS_PATH.write_text(content, encoding="utf-8")
    return 0


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Build deprecation documentation")
    parser.add_argument("--check", action="store_true", help="Check whether docs/deprecations.md is up to date")
    parser.add_argument(
        "--release-notes",
        metavar="VERSION",
        help="Print release-note deprecation sections for a version instead of writing docs",
    )
    return parser.parse_args()


def main() -> int:
    """Script entrypoint."""
    args = parse_args()
    if args.release_notes:
        print(render_release_note_deprecations(args.release_notes), end="")
        return 0
    return build_docs(check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
