"""CLI documentation builder.

Generates Markdown documentation from pytest CLI doc collection.
Groups options by category into single pages for better searchability.

Usage:
    # First, collect CLI doc metadata
    pytest --collect-cli-docs -p no:xdist

    # Then, build documentation
    python scripts/build_cli_docs.py

The generated documentation uses MkDocs Material tabs syntax for
version-specific output examples.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess  # noqa: S404
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import operator

from datamodel_code_generator.cli_options import (
    OptionCategory,
    get_canonical_option,
    get_option_meta,
    is_excluded_from_docs,
)

COLLECTION_PATH = Path(__file__).parent.parent / "tests" / "cli_doc" / ".cli_doc_collection.json"
DATA_PATH = Path(__file__).parent.parent / "tests" / "data"
EXPECTED_BASE_PATH = DATA_PATH / "expected"
EXPECTED_PATH = EXPECTED_BASE_PATH / "main"
DOCS_OUTPUT = Path(__file__).parent.parent / "docs" / "cli-reference"

DESC_LENGTH_SHORT = 60
DESC_LENGTH_LONG = 80


def slugify(text: str) -> str:
    """Convert text to safe slug for filenames and anchors.

    Examples:
        --frozen-dataclasses -> frozen-dataclasses
        Model Customization -> model-customization
    """
    slug = text.lstrip("-").lower()
    slug = re.sub(r"[^a-z0-9-]", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug or "unknown"


def safe_read_file(base_path: Path, relative_path: str, file_types: tuple[str, ...] = ("*.py",)) -> str:
    """Read file or directory with path traversal protection.

    For directories, concatenates all matching files with file headers.

    Args:
        base_path: Base directory for path resolution
        relative_path: Relative path to file or directory
        file_types: Glob patterns for files to include when reading directories
    """
    base_resolved = base_path.resolve()
    full_path = (base_path / relative_path).resolve()

    try:
        full_path.relative_to(base_resolved)
    except ValueError:
        msg = f"Path traversal detected: {relative_path}"
        raise ValueError(msg) from None

    if not full_path.exists():
        msg = f"File not found: {full_path}"
        raise FileNotFoundError(msg)

    if full_path.is_dir():
        # Handle directory - concatenate all matching files
        all_files = []
        for pattern in file_types:
            all_files.extend(full_path.glob(f"**/{pattern}"))
        all_files = sorted(set(all_files))

        if not all_files:
            return "# (empty directory - no matching files)\n"

        parts = []
        for file in all_files:
            rel_name = file.relative_to(full_path)
            parts.extend((f"# {rel_name}", file.read_text(encoding="utf-8").rstrip(), ""))  # blank line separator
        return "\n".join(parts)

    return full_path.read_text(encoding="utf-8")


def read_expected_file(relative_path: str) -> str:
    """Read expected output file, trying main/ then expected/ base for main_kr/ paths.

    This supports both:
    - Paths relative to tests/data/expected/main/ (backward compatible)
    - Paths like main_kr/... relative to tests/data/expected/
    """
    # Try main/ subdirectory first (backward compatibility)
    try:
        return safe_read_file(EXPECTED_PATH, relative_path)
    except FileNotFoundError:
        # Fall back to expected/ base for main_kr/ and other subdirectory paths
        return safe_read_file(EXPECTED_BASE_PATH, relative_path)


def select_primary_test(tests: list[dict[str, Any]]) -> dict[str, Any]:
    """Select the primary test for documentation."""
    for test in tests:
        if test["marker_kwargs"].get("primary", False):
            return test
    return tests[0]


def indent_code_block(content: str, prefix: str) -> str:
    """Indent a code block for MkDocs Material tabs."""
    lines = content.strip().split("\n")
    result = f"{prefix}```python\n"
    for line in lines:
        result += f"{prefix}{line}\n" if line else f"{prefix}\n"
    result += f"{prefix}```\n\n"
    return result


def format_cli_args(cli_args: list[str]) -> list[str]:
    """Format cli_args as proper command line (group option with its value)."""
    formatted = []
    i = 0
    while i < len(cli_args):
        arg = cli_args[i]
        if arg.startswith("-") and i + 1 < len(cli_args) and not cli_args[i + 1].startswith("-"):
            value = cli_args[i + 1]
            if " " in value or not value:
                value = f'"{value}"'
            formatted.append(f"{arg} {value}")
            i += 2
        else:
            formatted.append(arg)
            i += 1
    return formatted


def generate_option_section(option: str, primary: dict[str, Any]) -> str:  # noqa: PLR0912, PLR0914, PLR0915
    """Generate Markdown section for a single CLI option."""
    kwargs = primary["marker_kwargs"]
    meta = get_option_meta(option)

    md = f"## `{option}` {{#{slugify(option)}}}\n\n"

    if primary["docstring"]:
        md += f"{primary['docstring'].strip()}\n\n"

    meta_parts = []
    if meta and meta.since_version:
        meta_parts.append(f"**Since:** {meta.since_version}")
    if meta and meta.deprecated:
        msg = meta.deprecated_message or "Deprecated"
        meta_parts.append(f"**Deprecated:** {msg}")
    if kwargs.get("related_options"):
        related_links = []
        for r in kwargs["related_options"]:
            canonical = get_canonical_option(r)
            r_meta = get_option_meta(canonical)
            if r_meta:
                cat_slug = slugify(r_meta.category.value)
                related_links.append(f"[`{canonical}`]({cat_slug}.md#{slugify(canonical)})")
            else:
                related_links.append(f"`{canonical}`")
        meta_parts.append(f"**Related:** {', '.join(related_links)}")

    if meta_parts:
        md += " | ".join(meta_parts) + "\n\n"

    md += '!!! tip "Usage"\n\n'
    md += "    ```bash\n"
    if "config_content" in kwargs:
        md += "    datamodel-codegen "
    else:
        md += "    datamodel-codegen --input schema.json "
    formatted_args = format_cli_args(kwargs.get("cli_args", []))
    md += " ".join(formatted_args)
    md += " # (1)!\n"
    md += "    ```\n\n"
    md += f"    1. :material-arrow-left: `{option}` - the option documented here\n\n"

    if "config_content" in kwargs:
        md += '??? example "Configuration (pyproject.toml)"\n\n'
        md += "    ```toml\n"
        for line in kwargs["config_content"].strip().split("\n"):
            md += f"    {line}\n"
        md += "    ```\n\n"
    elif "input_schema" in kwargs:
        md += '??? example "Input Schema"\n\n'
        try:
            schema_content = safe_read_file(
                DATA_PATH, kwargs["input_schema"], file_types=("*.json", "*.yaml", "*.yml", "*.graphql")
            )
            schema_path = kwargs["input_schema"].lower()
            if schema_path.endswith((".yaml", ".yml")):
                lang = "yaml"
            elif schema_path.endswith(".graphql"):
                lang = "graphql"
            else:
                lang = "json"
            md += f"    ```{lang}\n"
            for line in schema_content.strip().split("\n"):
                md += f"    {line}\n"
            md += "    ```\n\n"
        except (FileNotFoundError, ValueError) as e:
            md += f"    > **Error:** {e}\n\n"

    md += '??? example "Output"\n\n'
    if "expected_stdout" in kwargs:
        try:
            content = read_expected_file(kwargs["expected_stdout"])
            md += "    ```\n"
            for line in content.strip().split("\n"):
                md += f"    {line}\n" if line else "    \n"
            md += "    ```\n\n"
        except (FileNotFoundError, ValueError) as e:
            md += f"    > **Error:** {e}\n\n"
    elif "comparison_output" in kwargs and "model_outputs" in kwargs:
        model_labels = {
            "pydantic_v1": "Pydantic v1",
            "pydantic_v2": "Pydantic v2",
            "dataclass": "dataclass",
            "typeddict": "TypedDict",
            "msgspec": "msgspec",
        }
        order = ["pydantic_v1", "pydantic_v2", "dataclass", "typeddict", "msgspec"]
        sorted_models = sorted(
            kwargs["model_outputs"].items(),
            key=lambda x: order.index(x[0]) if x[0] in order else len(order),
        )
        for model_key, output_file in sorted_models:
            label = model_labels.get(model_key, model_key)
            md += f'    === "{label}"\n\n'
            try:
                content = read_expected_file(output_file)
                md += indent_code_block(content, "        ")
            except (FileNotFoundError, ValueError) as e:
                md += f"        > **Error:** {e}\n\n"
        md += '    === "Without Option (Baseline)"\n\n'
        try:
            content = read_expected_file(kwargs["comparison_output"])
            md += indent_code_block(content, "        ")
        except (FileNotFoundError, ValueError) as e:
            md += f"        > **Error:** {e}\n\n"
    elif "comparison_output" in kwargs and "golden_output" in kwargs:
        md += '    === "With Option"\n\n'
        try:
            content = read_expected_file(kwargs["golden_output"])
            md += indent_code_block(content, "        ")
        except (FileNotFoundError, ValueError) as e:
            md += f"        > **Error:** {e}\n\n"
        md += '    === "Without Option"\n\n'
        try:
            content = read_expected_file(kwargs["comparison_output"])
            md += indent_code_block(content, "        ")
        except (FileNotFoundError, ValueError) as e:
            md += f"        > **Error:** {e}\n\n"
    elif kwargs.get("version_outputs"):
        sorted_versions = sorted(
            kwargs["version_outputs"].items(),
            key=lambda x: tuple(map(int, x[0].split("."))),
        )
        for version, output_file in sorted_versions:
            md += f'    === "Python {version}"\n\n'
            try:
                content = read_expected_file(output_file)
                md += indent_code_block(content, "        ")
            except (FileNotFoundError, ValueError) as e:
                md += f"        > **Error:** {e}\n\n"
    elif kwargs.get("model_outputs"):
        model_labels = {
            "pydantic_v1": "Pydantic v1",
            "pydantic_v2": "Pydantic v2",
            "dataclass": "dataclass",
            "typeddict": "TypedDict",
            "msgspec": "msgspec",
        }
        order = ["pydantic_v1", "pydantic_v2", "dataclass", "typeddict", "msgspec"]
        sorted_models = sorted(
            kwargs["model_outputs"].items(),
            key=lambda x: order.index(x[0]) if x[0] in order else len(order),
        )
        for model_key, output_file in sorted_models:
            label = model_labels.get(model_key, model_key)
            md += f'    === "{label}"\n\n'
            try:
                content = read_expected_file(output_file)
                md += indent_code_block(content, "        ")
            except (FileNotFoundError, ValueError) as e:
                md += f"        > **Error:** {e}\n\n"
    elif "golden_output" in kwargs:
        try:
            content = read_expected_file(kwargs["golden_output"])
            md += "    ```python\n"
            for line in content.strip().split("\n"):
                md += f"    {line}\n" if line else "    \n"
            md += "    ```\n\n"
        except (FileNotFoundError, ValueError) as e:
            md += f"    > **Error:** {e}\n\n"

    md += "---\n\n"
    return md


def generate_category_page(category: OptionCategory, options: dict[str, dict[str, Any]]) -> str:
    """Generate a category page with all options."""
    md = f"# {category.value}\n\n"
    md += "## Options\n\n"
    md += "| Option | Description |\n"
    md += "|--------|-------------|\n"
    for option in sorted(options.keys()):
        primary = options[option]
        desc = primary["docstring"].split("\n")[0][:DESC_LENGTH_SHORT] if primary["docstring"] else ""
        if len(desc) == DESC_LENGTH_SHORT:
            desc += "..."
        md += f"| [`{option}`](#{slugify(option)}) | {desc} |\n"
    md += "\n---\n\n"

    for option in sorted(options.keys()):
        primary = options[option]
        md += generate_option_section(option, primary)

    return md


def generate_quick_reference(categories: dict[OptionCategory, dict[str, Any]]) -> str:
    """Generate a quick reference page with all options in CLI format for easy searching."""
    md = "# Quick Reference\n\n"
    md += "All CLI options in one page for easy **Ctrl+F** searching.\n\n"
    md += "Click any option to see detailed documentation with examples.\n\n"

    # Collect all options with their descriptions
    all_options: list[tuple[str, str, OptionCategory]] = []
    for category, options in categories.items():
        for option, primary in options.items():
            desc = primary["docstring"].split("\n")[0] if primary["docstring"] else ""
            all_options.append((option, desc, category))

    # Sort alphabetically by option name
    all_options.sort(key=operator.itemgetter(0))

    md += "---\n\n"
    md += "```text\n"
    md += "datamodel-codegen [OPTIONS]\n"
    md += "```\n\n"

    # Group by category for organized display
    md += "## All Options by Category\n\n"

    for category in OptionCategory:
        if category not in categories:
            continue
        options = categories[category]
        if not options:
            continue

        slug_cat = slugify(category.value)
        md += f"### {category.value}\n\n"
        md += "| Option | Description |\n"
        md += "|--------|-------------|\n"

        for option in sorted(options.keys()):
            primary = options[option]
            desc = primary["docstring"].split("\n")[0][:DESC_LENGTH_LONG] if primary["docstring"] else ""
            if len(desc) == DESC_LENGTH_LONG:
                desc += "..."
            slug_opt = slugify(option)
            md += f"| [`{option}`]({slug_cat}.md#{slug_opt}) | {desc} |\n"

        md += "\n"

    # Alphabetical list for Ctrl+F
    md += "---\n\n"
    md += "## Alphabetical Index\n\n"
    md += "All options sorted alphabetically:\n\n"

    for option, desc, category in all_options:
        slug_cat = slugify(category.value)
        slug_opt = slugify(option)
        short_desc = desc[:DESC_LENGTH_SHORT] + "..." if len(desc) > DESC_LENGTH_SHORT else desc
        md += f"- [`{option}`]({slug_cat}.md#{slug_opt}) - {short_desc}\n"

    return md


def generate_index_page(categories: dict[OptionCategory, dict[str, Any]]) -> str:
    """Generate the index page with overview of all categories."""
    md = "# CLI Reference\n\n"
    md += "This documentation is auto-generated from test cases.\n\n"
    md += "**[Quick Reference](quick-reference.md)** - All options on one page for Ctrl+F search\n\n"

    md += "## Categories\n\n"
    md += "| Category | Options | Description |\n"
    md += "|----------|---------|-------------|\n"

    category_descriptions = {
        OptionCategory.BASE: "Input/output configuration",
        OptionCategory.TYPING: "Type annotation and import behavior",
        OptionCategory.FIELD: "Field naming and docstring behavior",
        OptionCategory.MODEL: "Model generation behavior",
        OptionCategory.TEMPLATE: "Output formatting and custom rendering",
        OptionCategory.OPENAPI: "OpenAPI-specific features",
        OptionCategory.GENERAL: "Utilities and meta options",
    }

    for category in OptionCategory:
        if category in categories:
            count = len(categories[category])
            desc = category_descriptions.get(category, "")
            slug = slugify(category.value)
            md += f"| [{category.value}]({slug}.md) | {count} | {desc} |\n"

    md += "\n"
    md += "## All Options\n\n"
    all_options = []
    for category, options in categories.items():
        all_options.extend((option, category) for option in options)

    sorted_options = sorted(all_options)
    letters_with_options = sorted({opt.lstrip("-")[0].upper() for opt, _ in sorted_options})
    md += "**Jump to:** "
    md += " · ".join(f"[{letter}](#{letter.lower()})" for letter in letters_with_options)
    md += "\n\n"

    current_letter = None
    for option, category in sorted_options:
        first_letter = option.lstrip("-")[0].upper()
        if first_letter != current_letter:
            current_letter = first_letter
            md += f"\n### {current_letter} {{#{current_letter.lower()}}}\n\n"
        slug_cat = slugify(category.value)
        slug_opt = slugify(option)
        md += f"- [`{option}`]({slug_cat}.md#{slug_opt})\n"

    return md


def collect_cli_docs() -> int:
    """Run pytest to collect CLI doc metadata."""
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "pytest", "--collect-cli-docs", "-p", "no:xdist", "-q"],
        check=False,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )
    if result.returncode != 0:
        return result.returncode
    return 0


def build_docs(*, check: bool = False) -> int:  # noqa: PLR0912, PLR0915
    """Build CLI documentation from collection data.

    Args:
        check: If True, validate that existing docs match generated content.
               Returns error if any differences found.
    """
    if not COLLECTION_PATH.exists():
        return 1

    with Path(COLLECTION_PATH).open(encoding="utf-8") as f:
        collection = json.load(f)

    schema_version = collection.get("schema_version", 0)
    if schema_version != 1:
        print(f"Warning: Unexpected schema version {schema_version}, expected 1", file=sys.stderr)  # noqa: T201

    items = collection.get("items", [])
    if not items:
        return 0

    # Group by canonical option
    options_map: dict[str, dict[str, Any]] = {}
    for item in items:
        for opt in item["marker_kwargs"].get("options", []):
            canonical = get_canonical_option(opt)
            if is_excluded_from_docs(canonical):
                continue
            if canonical not in options_map:
                options_map[canonical] = select_primary_test([item])
            # If already exists, keep existing (first one wins unless primary)
            elif item["marker_kwargs"].get("primary", False):
                options_map[canonical] = item

    categories: dict[OptionCategory, dict[str, Any]] = defaultdict(dict)

    for option, primary in options_map.items():
        meta = get_option_meta(option)
        if meta:
            categories[meta.category][option] = primary
        else:
            categories[OptionCategory.GENERAL][option] = primary

    if not check:
        DOCS_OUTPUT.mkdir(parents=True, exist_ok=True)
        for old_file in DOCS_OUTPUT.glob("*.md"):
            old_file.unlink()

    generated = 0
    errors = 0
    mismatches: list[str] = []

    def write_or_check(output_path: Path, content: str, label: str) -> bool:
        """Write content to file or check if it matches existing content."""
        nonlocal generated, errors
        if check:
            if not output_path.exists():
                mismatches.append(f"{label}: file does not exist")
                return False
            existing = output_path.read_text(encoding="utf-8")
            if existing != content:
                mismatches.append(f"{label}: content differs")
                return False
            return True
        output_path.write_text(content, encoding="utf-8")
        generated += 1
        return True

    for category, options in categories.items():
        if not options:
            continue
        try:
            md = generate_category_page(category, options)
            output_path = DOCS_OUTPUT / f"{slugify(category.value)}.md"
            write_or_check(output_path, md, f"{output_path.name} ({len(options)} options)")
        except (OSError, ValueError, KeyError):
            errors += 1

    try:
        md = generate_index_page(categories)
        output_path = DOCS_OUTPUT / "index.md"
        write_or_check(output_path, md, "index.md")
    except (OSError, ValueError, KeyError):
        errors += 1

    try:
        md = generate_quick_reference(categories)
        output_path = DOCS_OUTPUT / "quick-reference.md"
        total_options = sum(len(opts) for opts in categories.values())
        write_or_check(output_path, md, f"quick-reference.md ({total_options} options)")
    except (OSError, ValueError, KeyError):
        errors += 1

    if check:
        if mismatches:
            for m in mismatches:
                print(f"Mismatch: {m}", file=sys.stderr)  # noqa: T201
            return 1
        return 0
    if errors:
        print(f"Errors occurred: {errors}", file=sys.stderr)  # noqa: T201
    return 1 if errors else 0


def main() -> int:
    """Parse CLI arguments and build documentation."""
    parser = argparse.ArgumentParser(description="Build CLI documentation from test cases")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if docs are up to date without modifying files",
    )
    parser.add_argument(
        "--collect",
        action="store_true",
        help="Run pytest to collect CLI doc metadata first",
    )
    args = parser.parse_args()

    if args.collect:
        result = collect_cli_docs()
        if result != 0:
            return result

    return build_docs(check=args.check)


if __name__ == "__main__":
    sys.exit(main())
