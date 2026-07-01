"""Schema documentation builder.

Generates feature tables from JsonSchemaFeatures and OpenAPISchemaFeatures
metadata for schema support documentation.

Usage:
    python scripts/build_schema_docs.py          # Generate/update docs
    python scripts/build_schema_docs.py --check  # Check if docs are up to date
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, fields
from pathlib import Path
from typing import TYPE_CHECKING

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datamodel_code_generator.format import DatetimeClassType
from datamodel_code_generator.model.pydantic_v2.types import DataTypeManager as PydanticV2DataTypeManager
from datamodel_code_generator.parser.schema_version import (
    DataFormatMapping,
    FeatureMetadata,
    JsonSchemaFeatures,
    OpenAPISchemaFeatures,
    get_data_formats,
)

if TYPE_CHECKING:
    from datamodel_code_generator.types import Types

ROOT = Path(__file__).parent.parent
SUPPORTED_FORMATS_DOCS_PATH = ROOT / "docs" / "supported_formats.md"
SUPPORTED_DATA_TYPES_DOCS_PATH = ROOT / "docs" / "supported-data-types.md"

# Markers for auto-generated content
BEGIN_MARKER = "<!-- BEGIN AUTO-GENERATED SUPPORTED FEATURES -->"
END_MARKER = "<!-- END AUTO-GENERATED SUPPORTED FEATURES -->"
DATA_TYPES_BEGIN_MARKER = "<!-- BEGIN AUTO-GENERATED SCHEMA FEATURE SUPPORT -->"
DATA_TYPES_END_MARKER = "<!-- END AUTO-GENERATED SCHEMA FEATURE SUPPORT -->"
DATA_FORMAT_BEGIN_MARKER = "<!-- BEGIN AUTO-GENERATED DATA FORMAT SUPPORT -->"
DATA_FORMAT_END_MARKER = "<!-- END AUTO-GENERATED DATA FORMAT SUPPORT -->"
DATA_TYPES_FORMAT_BEGIN_MARKER = "<!-- BEGIN AUTO-GENERATED DATA TYPE SUPPORT -->"
DATA_TYPES_FORMAT_END_MARKER = "<!-- END AUTO-GENERATED DATA TYPE SUPPORT -->"

# Status emoji mapping
STATUS_EMOJI = {
    "supported": "✅",
    "partial": "⚠️",
    "not_supported": "❌",
}

SCHEMA_TYPE_KEYWORDS = {
    "string": "pattern, minLength, maxLength",
    "number": "maximum, exclusiveMaximum, minimum, exclusiveMinimum, multipleOf",
    "integer": "maximum, exclusiveMaximum, minimum, exclusiveMinimum, multipleOf",
    "boolean": "",
    "array": "items, prefixItems, minItems, maxItems, uniqueItems",
    "object": "properties, required, additionalProperties, patternProperties",
    "null": "",
}

FORMAT_NOTES = {
    ("string", "byte"): "Base64 encoded string",
    ("string", "binary"): "File content",
    ("string", "email"): "Requires email-validator",
    ("string", "idn-email"): "Requires email-validator",
    ("string", "ulid"): "Requires python-ulid",
}


@dataclass(frozen=True, slots=True)
class GeneratedDocsTarget:
    """One Markdown file section generated from schema feature metadata."""

    path: Path
    begin_marker: str
    end_marker: str
    content: str


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


def heading(level: int, title: str) -> str:
    """Return a Markdown heading at the requested level."""
    return f"{'#' * level} {title}"


def get_default_pydantic_v2_data_type_manager() -> PydanticV2DataTypeManager:
    """Return the default Pydantic v2 type manager used for docs labels."""
    return PydanticV2DataTypeManager(target_datetime_class=DatetimeClassType.Awaredatetime)


def get_openapi_specific_feature_metadata() -> list[tuple[str, FeatureMetadata]]:
    """Return OpenAPI feature metadata that is not inherited from JSON Schema."""
    json_field_names = {f.name for f in fields(JsonSchemaFeatures)}
    return [(name, meta) for name, meta in get_feature_metadata(OpenAPISchemaFeatures) if name not in json_field_names]


def iter_data_formats(data_formats: DataFormatMapping) -> list[tuple[str, str, Types]]:
    """Return schema data formats in docs-friendly order."""
    rows = []
    for schema_type, formats in data_formats.items():
        if default_type := formats.get("default"):
            rows.append((schema_type, "default", default_type))
        rows.extend(
            (schema_type, format_name, type_) for format_name, type_ in formats.items() if format_name != "default"
        )
    return rows


def get_openapi_only_data_formats() -> DataFormatMapping:
    """Return OpenAPI formats that do not exist in JSON Schema mappings."""
    common_formats = get_data_formats(is_openapi=False)
    result: DataFormatMapping = {}
    for schema_type, formats in get_data_formats(is_openapi=True).items():
        openapi_only_formats = {
            format_name: type_
            for format_name, type_ in formats.items()
            if common_formats.get(schema_type, {}).get(format_name) != type_
        }
        if openapi_only_formats:
            result[schema_type] = openapi_only_formats
    return result


def get_python_type_label(type_: Types) -> str:
    """Return a Markdown label for the default Pydantic v2 type hint."""
    data_type = get_default_pydantic_v2_data_type_manager().get_data_type(type_)
    return f"`{data_type.base_type_hint}`"


def get_format_label(format_name: str) -> str:
    """Return a Markdown label for a schema format name."""
    if format_name == "default":
        return "`default` (no `format`)"
    return f"`{format_name}`"


def generate_schema_type_table(data_formats: DataFormatMapping) -> str:
    """Generate the supported schema data type table."""
    lines = ["| Schema Type | Default Pydantic v2 Type | Supported Keywords |"]
    lines.append("|-------------|--------------------------|--------------------|")
    for schema_type, formats in data_formats.items():
        if not (type_ := formats.get("default")):
            continue
        keywords = SCHEMA_TYPE_KEYWORDS.get(schema_type, "")
        lines.append(f"| `{schema_type}` | {get_python_type_label(type_)} | {keywords or '-'} |")
    return "\n".join(lines)


def generate_data_format_table(data_formats: DataFormatMapping) -> str:
    """Generate a Markdown table from schema data format mappings."""
    lines = ["| Schema Type | Format | Default Pydantic v2 Type | Notes |"]
    lines.append("|-------------|--------|--------------------------|-------|")
    for schema_type, format_name, type_ in iter_data_formats(data_formats):
        note = FORMAT_NOTES.get((schema_type, format_name), "")
        lines.append(
            f"| `{schema_type}` | {get_format_label(format_name)} | {get_python_type_label(type_)} | {note or '-'} |"
        )
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
    for name, meta in get_openapi_specific_feature_metadata():
        print(f"  {name}:")
        print(f"    doc_name: {meta['doc_name']}")
        print(f"    introduced: {meta['introduced']}")
        print(f"    status: {meta['status']}")
        print(f"    description: {meta['description']}")
        print()


def generate_supported_features_content(
    *,
    heading_level: int = 3,
    title: str = "Supported Features (from code)",
    intro: str = "The following features are tracked in the codebase with their implementation status:",
) -> str:
    """Generate the supported features content for documentation (without markers)."""
    lines = [
        "",
        heading(heading_level, title),
        "",
        intro,
        "",
        heading(heading_level + 1, "JSON Schema Features"),
        "",
        generate_feature_table(get_feature_metadata(JsonSchemaFeatures)),
        "",
        heading(heading_level + 1, "OpenAPI-Specific Features"),
        "",
    ]
    lines.extend((generate_feature_table(get_openapi_specific_feature_metadata()), ""))

    return "\n".join(lines)


def generate_supported_features_table() -> str:
    """Generate the supported features table with markers for documentation."""
    return f"{BEGIN_MARKER}{generate_supported_features_content()}{END_MARKER}"


def generate_supported_data_types_content() -> str:
    """Generate schema feature content for docs/supported-data-types.md."""
    return generate_supported_features_content(
        title="Schema Feature Support (from code)",
        intro=(
            "The JSON Schema and OpenAPI feature matrix below is generated from the same code metadata "
            "used by the schema version support page."
        ),
    )


def generate_data_format_content(
    *,
    heading_level: int = 3,
    title: str = "Data Format Support",
    intro: str = (
        "The schema type, format, and default Pydantic v2 type columns below are generated from the "
        "schema format registry and the default Pydantic v2 type mapping; notes document supplemental details."
    ),
    include_schema_types: bool = True,
) -> str:
    """Generate schema data type and format content for documentation."""
    data_formats = get_data_formats(is_openapi=False)
    lines = [
        "",
        heading(heading_level, title),
        "",
        intro,
        "",
    ]
    if include_schema_types:
        lines.extend((
            heading(heading_level + 1, "Schema Data Types"),
            "",
            generate_schema_type_table(data_formats),
            "",
        ))

    lines.extend((
        heading(heading_level + 1, "Common Formats (JSON Schema + OpenAPI)"),
        "",
        generate_data_format_table(data_formats),
        "",
        heading(heading_level + 1, "OpenAPI-Only Formats"),
        "",
        generate_data_format_table(get_openapi_only_data_formats()),
        "",
    ))
    return "\n".join(lines)


def generate_supported_data_types_format_content() -> str:
    """Generate schema type and format content for docs/supported-data-types.md."""
    return generate_data_format_content(
        title="Implemented Data Types and Formats",
        intro=(
            "The schema type, format, and default Pydantic v2 type columns below are generated from the "
            "parser's schema format registry and the default Pydantic v2 type mapping; keyword and note columns "
            "document supplemental schema details."
        ),
    )


def generated_docs_targets() -> tuple[GeneratedDocsTarget, ...]:
    """Return all schema docs sections generated from feature metadata."""
    return (
        GeneratedDocsTarget(
            path=SUPPORTED_FORMATS_DOCS_PATH,
            begin_marker=BEGIN_MARKER,
            end_marker=END_MARKER,
            content=generate_supported_features_content(),
        ),
        GeneratedDocsTarget(
            path=SUPPORTED_DATA_TYPES_DOCS_PATH,
            begin_marker=DATA_TYPES_BEGIN_MARKER,
            end_marker=DATA_TYPES_END_MARKER,
            content=generate_supported_data_types_content(),
        ),
        GeneratedDocsTarget(
            path=SUPPORTED_FORMATS_DOCS_PATH,
            begin_marker=DATA_FORMAT_BEGIN_MARKER,
            end_marker=DATA_FORMAT_END_MARKER,
            content=generate_data_format_content(include_schema_types=False),
        ),
        GeneratedDocsTarget(
            path=SUPPORTED_DATA_TYPES_DOCS_PATH,
            begin_marker=DATA_TYPES_FORMAT_BEGIN_MARKER,
            end_marker=DATA_TYPES_FORMAT_END_MARKER,
            content=generate_supported_data_types_format_content(),
        ),
    )


def update_docs_target(target: GeneratedDocsTarget, *, check: bool) -> bool:
    """Update or check one generated Markdown section."""
    if not target.path.exists():
        print(f"Error: {target.path} does not exist", file=sys.stderr)
        return False

    current_content = target.path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"{re.escape(target.begin_marker)}.*?{re.escape(target.end_marker)}",
        re.DOTALL,
    )

    if not (match := pattern.search(current_content)):
        print(f"Warning: Markers not found in {target.path}", file=sys.stderr)
        print("Please add the following markers to the file:", file=sys.stderr)
        print(f"  {target.begin_marker}", file=sys.stderr)
        print(f"  {target.end_marker}", file=sys.stderr)
        return False

    new_section = f"{target.begin_marker}{target.content}{target.end_marker}"
    new_content = current_content[: match.start()] + new_section + current_content[match.end() :]

    if check:
        if current_content != new_content:
            print(f"Schema docs are out of date: {target.path}", file=sys.stderr)
            print("Run 'python scripts/build_schema_docs.py' to update.", file=sys.stderr)
            return False
        return True

    if current_content == new_content:
        print(f"Schema docs are already up to date: {target.path}")
        return True

    target.path.write_text(new_content, encoding="utf-8")
    print(f"Updated {target.path}")
    return True


def update_docs_file(*, check: bool = False) -> int:
    """Update generated schema documentation sections."""
    results = [update_docs_target(target, check=check) for target in generated_docs_targets()]
    if all(results):
        if check:
            print("Schema docs are up to date.")
        return 0
    return 1


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
