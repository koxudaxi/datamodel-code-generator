"""Schema documentation builder.

Generates feature tables from JsonSchemaFeatures and OpenAPISchemaFeatures
metadata for docs/supported_formats.md.

Usage:
    python scripts/build_schema_docs.py          # Generate/update docs
    python scripts/build_schema_docs.py --check  # Check if docs are up to date
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import fields
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datamodel_code_generator.parser.schema_version import (
    FeatureMetadata,
    JsonSchemaFeatures,
    OpenAPISchemaFeatures,
)

DOCS_PATH = Path(__file__).parent.parent / "docs" / "supported_formats.md"

# Markers for auto-generated content
BEGIN_MARKER = "<!-- BEGIN AUTO-GENERATED SUPPORTED FEATURES -->"
END_MARKER = "<!-- END AUTO-GENERATED SUPPORTED FEATURES -->"

# Status emoji mapping
STATUS_EMOJI = {
    "supported": "✅",
    "partial": "⚠️",
    "not_supported": "❌",
}


def get_feature_metadata(cls: type) -> list[tuple[str, FeatureMetadata]]:
    """Extract feature metadata from a dataclass.

    Args:
        cls: JsonSchemaFeatures or OpenAPISchemaFeatures class.

    Returns:
        List of (field_name, metadata) tuples.
    """
    result = []
    for f in fields(cls):
        if f.metadata:
            meta = FeatureMetadata(
                introduced=f.metadata.get("introduced", ""),
                doc_name=f.metadata.get("doc_name", f.name),
                description=f.metadata.get("description", ""),
                status=f.metadata.get("status", "supported"),
            )
            result.append((f.name, meta))
    return result


def generate_feature_table(
    features: list[tuple[str, FeatureMetadata]],
    *,
    include_status: bool = True,
) -> str:
    """Generate a Markdown table from feature metadata.

    Args:
        features: List of (field_name, metadata) tuples.
        include_status: Whether to include the Status column.

    Returns:
        Markdown table string.
    """
    if include_status:
        lines = ["| Feature | Introduced | Status | Description |"]
        lines.append("|---------|------------|--------|-------------|")
        for _name, meta in features:
            emoji = STATUS_EMOJI.get(meta["status"], "")
            status_text = f"{emoji} {meta['status'].replace('_', ' ').title()}"
            lines.append(f"| `{meta['doc_name']}` | {meta['introduced']} | {status_text} | {meta['description']} |")
    else:
        lines = ["| Feature | Introduced | Description |"]
        lines.append("|---------|------------|-------------|")
        for _name, meta in features:
            lines.append(f"| `{meta['doc_name']}` | {meta['introduced']} | {meta['description']} |")

    return "\n".join(lines)


def print_features_summary() -> None:
    """Print a summary of all features with their metadata."""
    print("=" * 60)
    print("JSON Schema Features")
    print("=" * 60)
    for name, meta in get_feature_metadata(JsonSchemaFeatures):
        print(f"  {name}:")
        print(f"    doc_name: {meta['doc_name']}")
        print(f"    introduced: {meta['introduced']}")
        print(f"    status: {meta['status']}")
        print(f"    description: {meta['description']}")
        print()

    print("=" * 60)
    print("OpenAPI Schema Features (additional)")
    print("=" * 60)
    # Get only OpenAPI-specific fields (not inherited from JsonSchemaFeatures)
    json_field_names = {f.name for f in fields(JsonSchemaFeatures)}
    for name, meta in get_feature_metadata(OpenAPISchemaFeatures):
        if name not in json_field_names:
            print(f"  {name}:")
            print(f"    doc_name: {meta['doc_name']}")
            print(f"    introduced: {meta['introduced']}")
            print(f"    status: {meta['status']}")
            print(f"    description: {meta['description']}")
            print()


def generate_supported_features_content() -> str:
    """Generate the supported features content for documentation (without markers)."""
    lines = [
        "",
        "### Supported Features (from code)",
        "",
        "The following features are tracked in the codebase with their implementation status:",
        "",
        "#### JSON Schema Features",
        "",
        generate_feature_table(get_feature_metadata(JsonSchemaFeatures)),
        "",
        "#### OpenAPI-Specific Features",
        "",
    ]

    # Get only OpenAPI-specific fields
    json_field_names = {f.name for f in fields(JsonSchemaFeatures)}
    openapi_features = [
        (name, meta) for name, meta in get_feature_metadata(OpenAPISchemaFeatures) if name not in json_field_names
    ]
    lines.extend((generate_feature_table(openapi_features), ""))

    return "\n".join(lines)


def generate_supported_features_table() -> str:
    """Generate the supported features table with markers for documentation."""
    return f"{BEGIN_MARKER}{generate_supported_features_content()}{END_MARKER}"


def update_docs_file(*, check: bool = False) -> int:
    """Update docs/supported_formats.md with auto-generated content.

    Args:
        check: If True, only check if content would change (returns 1 if different).

    Returns:
        0 on success, 1 on failure or if check mode detects changes.
    """
    if not DOCS_PATH.exists():
        print(f"Error: {DOCS_PATH} does not exist", file=sys.stderr)
        return 1

    current_content = DOCS_PATH.read_text(encoding="utf-8")
    new_generated = generate_supported_features_content()

    # Pattern to match content between markers (including markers)
    pattern = re.compile(
        rf"{re.escape(BEGIN_MARKER)}.*?{re.escape(END_MARKER)}",
        re.DOTALL,
    )

    if pattern.search(current_content):
        # Replace existing auto-generated section
        new_content = pattern.sub(
            f"{BEGIN_MARKER}{new_generated}{END_MARKER}",
            current_content,
        )
    else:
        print(f"Warning: Markers not found in {DOCS_PATH}", file=sys.stderr)
        print("Please add the following markers to the file:", file=sys.stderr)
        print(f"  {BEGIN_MARKER}", file=sys.stderr)
        print(f"  {END_MARKER}", file=sys.stderr)
        return 1

    if check:
        if current_content != new_content:
            print(f"Schema docs are out of date: {DOCS_PATH}", file=sys.stderr)
            print("Run 'python scripts/build_schema_docs.py' to update.", file=sys.stderr)
            return 1
        print("Schema docs are up to date.")
        return 0

    if current_content == new_content:
        print("Schema docs are already up to date.")
        return 0

    DOCS_PATH.write_text(new_content, encoding="utf-8")
    print(f"Updated {DOCS_PATH}")
    return 0


def main() -> int:
    """Parse arguments and build documentation."""
    parser = argparse.ArgumentParser(description="Build schema documentation from code metadata")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if docs would change without modifying files",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print a summary of all features and their metadata",
    )
    args = parser.parse_args()

    if args.summary:
        print_features_summary()
        return 0

    return update_docs_file(check=args.check)


if __name__ == "__main__":
    sys.exit(main())
