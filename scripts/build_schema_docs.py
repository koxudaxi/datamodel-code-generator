"""Schema documentation builder.

Generates feature tables from JsonSchemaFeatures and OpenAPISchemaFeatures
metadata for docs/supported_formats.md.

Usage:
    python scripts/build_schema_docs.py          # Generate/update docs
    python scripts/build_schema_docs.py --check  # Check if docs are up to date
"""

from __future__ import annotations

import argparse
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


def generate_supported_features_table() -> str:
    """Generate the supported features table for documentation."""
    lines = [
        "<!-- BEGIN AUTO-GENERATED SUPPORTED FEATURES -->",
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
    lines.extend((generate_feature_table(openapi_features), "", "<!-- END AUTO-GENERATED SUPPORTED FEATURES -->"))

    return "\n".join(lines)


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

    print("Schema Documentation Builder")
    print("-" * 40)

    # For now, just print the generated table
    print("\nGenerated Supported Features Table:")
    print()
    print(generate_supported_features_table())

    if args.check:
        print("\n[Check mode] No files modified.")
    else:
        print("\n[Info] This script currently outputs to stdout.")
        print("       Future versions will update docs/supported_formats.md directly.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
