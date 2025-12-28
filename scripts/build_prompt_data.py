"""Build prompt data from cli_doc collection.

Generates src/datamodel_code_generator/prompt_data.py containing
option descriptions extracted from cli_doc markers.

Usage:
    # First, collect CLI doc metadata
    pytest --collect-cli-docs -p no:xdist

    # Then, build prompt data
    python scripts/build_prompt_data.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

COLLECTION_PATH = Path(__file__).parent.parent / "tests" / "cli_doc" / ".cli_doc_collection.json"
OUTPUT_PATH = Path(__file__).parent.parent / "src" / "datamodel_code_generator" / "prompt_data.py"


def build_prompt_data(*, check: bool = False) -> int:
    """Extract option descriptions and generate Python file.

    Args:
        check: If True, validate that existing file matches generated content.

    Returns:
        0 on success, 1 on mismatch (check mode) or error.
    """
    if not COLLECTION_PATH.exists():
        print(f"Collection file not found: {COLLECTION_PATH}", file=sys.stderr)
        print("Run: pytest --collect-cli-docs -p no:xdist", file=sys.stderr)
        return 1

    with COLLECTION_PATH.open(encoding="utf-8") as f:
        collection = json.load(f)

    descriptions: dict[str, str] = {}
    for item in collection.get("items", []):
        option_description = item.get("option_description", "")
        if not option_description:
            continue
        first_line = option_description.split("\n")[0].strip()
        for opt in item.get("marker_kwargs", {}).get("options", []):
            if opt not in descriptions:
                descriptions[opt] = first_line

    # Generate Python file content
    lines = [
        '"""Auto-generated prompt data from cli_doc collection.',
        "",
        "DO NOT EDIT MANUALLY. Run: python scripts/build_prompt_data.py",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "# Option descriptions extracted from cli_doc markers",
        "OPTION_DESCRIPTIONS: dict[str, str] = {",
    ]
    for opt, desc in sorted(descriptions.items()):
        escaped_desc = desc.replace("\\", "\\\\").replace('"', '\\"')
        # Truncate description if line would exceed 120 characters
        max_desc_len = 120 - len(f'    "{opt}": "",')
        if len(escaped_desc) > max_desc_len:
            truncated = escaped_desc[: max_desc_len - 3]
            # Ensure we don't break escape sequences by checking for trailing backslash
            truncated = truncated.removesuffix("\\")
            escaped_desc = truncated + "..."
        lines.append(f'    "{opt}": "{escaped_desc}",')
    lines.extend(("}", ""))

    content = "\n".join(lines)

    if check:
        if not OUTPUT_PATH.exists():
            print(f"Output file not found: {OUTPUT_PATH}", file=sys.stderr)
            return 1
        existing = OUTPUT_PATH.read_text(encoding="utf-8")
        if existing != content:
            print(f"Content mismatch: {OUTPUT_PATH}", file=sys.stderr)
            return 1
        print(f"OK: {OUTPUT_PATH}")
        return 0

    OUTPUT_PATH.write_text(content, encoding="utf-8")
    print(f"Generated: {OUTPUT_PATH} ({len(descriptions)} options)")
    return 0


def main() -> int:
    """Parse CLI arguments and build prompt data."""
    parser = argparse.ArgumentParser(description="Build prompt data from cli_doc collection")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if prompt data is up to date without modifying files",
    )
    args = parser.parse_args()
    return build_prompt_data(check=args.check)


if __name__ == "__main__":
    sys.exit(main())
