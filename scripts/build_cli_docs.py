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
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import operator

from datamodel_code_generator.cli_options import (
    MANUAL_DOCS,
    OptionCategory,
    get_canonical_option,
    get_option_meta,
    is_manual_doc,
)


@dataclass
class CLIDocExample:
    """Represents a single CLI documentation example from a test."""

    node_id: str
    docstring: str
    input_schema: str | None = None
    config_content: str | None = None
    cli_args: list[str] = field(default_factory=list)
    golden_output: str | None = None
    comparison_output: str | None = None
    version_outputs: dict[str, str] | None = None
    model_outputs: dict[str, str] | None = None
    expected_stdout: str | None = None
    aliases: list[str] = field(default_factory=list)
    related_options: list[str] = field(default_factory=list)
    is_primary: bool = False

    @classmethod
    def from_item(cls, item: dict[str, Any]) -> CLIDocExample:
        """Create CLIDocExample from collected test item."""
        kwargs = item.get("marker_kwargs", {})
        return cls(
            node_id=item.get("node_id", ""),
            docstring=item.get("docstring", ""),
            input_schema=kwargs.get("input_schema"),
            config_content=kwargs.get("config_content"),
            cli_args=kwargs.get("cli_args", []),
            golden_output=kwargs.get("golden_output"),
            comparison_output=kwargs.get("comparison_output"),
            version_outputs=kwargs.get("version_outputs"),
            model_outputs=kwargs.get("model_outputs"),
            expected_stdout=kwargs.get("expected_stdout"),
            aliases=kwargs.get("aliases", []),
            related_options=kwargs.get("related_options", []),
            is_primary=kwargs.get("primary", False),
        )

    def get_schema_type(self) -> str:
        """Determine schema type from input_schema path."""
        if not self.input_schema:
            return "config" if self.config_content else "unknown"
        path_lower = self.input_schema.lower()
        if path_lower.endswith(".graphql"):
            return "GraphQL"
        prefix_map = {
            "graphql/": "GraphQL",
            "openapi/": "OpenAPI",
            "jsonschema/": "JSON Schema",
            "json/": "JSON",
            "yaml/": "YAML",
            "csv/": "CSV",
        }
        for prefix, schema_type in prefix_map.items():
            if path_lower.startswith(prefix):
                return schema_type
        return "Schema"


@dataclass
class CLIDocOption:
    """Represents a CLI option with all its documentation examples."""

    option_name: str
    examples: list[CLIDocExample] = field(default_factory=list)

    def add_example(self, example: CLIDocExample) -> None:
        """Add an example, maintaining primary example priority."""
        self.examples.append(example)

    def get_primary(self) -> CLIDocExample | None:
        """Get the primary example for this option."""
        for ex in self.examples:
            if ex.is_primary:
                return ex
        return self.examples[0] if self.examples else None

    def get_docstring(self) -> str:
        """Get docstring from primary example."""
        primary = self.get_primary()
        return primary.docstring if primary else ""

    def get_aliases(self) -> list[str]:
        """Get all aliases from all examples."""
        aliases: set[str] = set()
        for ex in self.examples:
            aliases.update(ex.aliases)
        return sorted(aliases)

    def get_related_options(self) -> list[str]:
        """Get all related options from all examples."""
        related: set[str] = set()
        for ex in self.examples:
            related.update(ex.related_options)
        return sorted(related)

    def get_unique_schema_types(self) -> list[str]:
        """Get unique schema types across all examples."""
        types: dict[str, CLIDocExample] = {}
        for ex in self.examples:
            schema_type = ex.get_schema_type()
            if schema_type not in types:
                types[schema_type] = ex
        return list(types.keys())


COLLECTION_PATH = Path(__file__).parent.parent / "tests" / "cli_doc" / ".cli_doc_collection.json"
DATA_PATH = Path(__file__).parent.parent / "tests" / "data"
EXPECTED_BASE_PATH = DATA_PATH / "expected"
EXPECTED_PATH = EXPECTED_BASE_PATH / "main"
DOCS_OUTPUT = Path(__file__).parent.parent / "docs" / "cli-reference"
MANUAL_DOCS_DIR = DOCS_OUTPUT / "manual"
DOCS_ROOT = Path(__file__).parent.parent / "docs"

DESC_LENGTH_SHORT = 60
DESC_LENGTH_LONG = 80

# Regex pattern for extracting CLI options from markdown files
# Format: <!-- related-cli-options: --option1, --option2, ... -->
CLI_OPTIONS_TAG_PATTERN = re.compile(r"<!--\s*related-cli-options:\s*([^>]+?)\s*-->", re.IGNORECASE)

# Emoji mapping for categories
CATEGORY_EMOJIS = {
    OptionCategory.BASE: "📁",
    OptionCategory.TYPING: "🔧",
    OptionCategory.FIELD: "🏷️",
    OptionCategory.MODEL: "🏗️",
    OptionCategory.TEMPLATE: "🎨",
    OptionCategory.OPENAPI: "📘",
    OptionCategory.GENERAL: "⚙️",
}

# Manual option descriptions for utility options
MANUAL_OPTION_DESCRIPTIONS = {
    "--help": "Show help message and exit",
    "--version": "Show program version and exit",
    "--debug": "Show debug messages during code generation",
    "--profile": "Use a named profile from pyproject.toml",
    "--no-color": "Disable colorized output",
}


def scan_docs_for_cli_option_tags() -> dict[str, list[tuple[str, str]]]:
    """Scan markdown files in docs/ for related-cli-options tags.

    Returns:
        Dictionary mapping CLI option name to list of (page_path, page_title) tuples.
        page_path is relative to docs/ directory.
    """
    option_to_pages: dict[str, list[tuple[str, str]]] = defaultdict(list)

    # Scan all markdown files in docs/ (excluding cli-reference/)
    # Sort to ensure consistent ordering across different environments
    for md_file in sorted(DOCS_ROOT.glob("**/*.md")):
        # Skip cli-reference directory (auto-generated)
        try:
            md_file.relative_to(DOCS_OUTPUT)
            continue
        except ValueError:
            pass  # Not in cli-reference, continue processing

        content = md_file.read_text(encoding="utf-8")
        matches = CLI_OPTIONS_TAG_PATTERN.findall(content)

        if not matches:
            continue

        # Get page title from first H1 heading
        title_match = re.search(r"^#\s+(.+?)$", content, re.MULTILINE)
        if title_match:
            page_title = title_match.group(1).strip()
            # Remove emojis and clean up (preserve dots for filenames like pyproject.toml)
            page_title = re.sub(r"[^\w\s\-/.]", "", page_title).strip()
        else:
            page_title = md_file.stem.replace("-", " ").replace("_", " ").title()

        # Get relative path from docs/
        page_path = str(md_file.relative_to(DOCS_ROOT))

        # Parse all matched tags
        for match in matches:
            options = [opt.strip() for opt in match.split(",")]
            for option in options:
                if option.startswith("--"):
                    canonical = get_canonical_option(option)
                    option_to_pages[canonical].append((page_path, page_title))

    # Sort the page lists for each option to ensure consistent ordering
    return {option: sorted(pages) for option, pages in sorted(option_to_pages.items())}


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
        msg = f"File not found: {relative_path}"
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


def _get_schema_lang(schema_path: str) -> str:
    """Get language identifier for schema file."""
    path_lower = schema_path.lower()
    if path_lower.endswith((".yaml", ".yml")):
        return "yaml"
    if path_lower.endswith(".graphql"):
        return "graphql"
    return "json"


def _generate_single_example_output(example: CLIDocExample, prefix: str = "    ") -> str:
    """Generate output section for a single example."""
    md = ""
    if example.expected_stdout:
        stdout_value = example.expected_stdout
        if "/" in stdout_value or stdout_value.endswith((".py", ".txt")):
            try:
                content = read_expected_file(stdout_value)
                md += f"{prefix}```\n"
                for line in content.strip().split("\n"):
                    md += f"{prefix}{line}\n" if line else f"{prefix}\n"
                md += f"{prefix}```\n\n"
            except (FileNotFoundError, ValueError) as e:
                md += f"{prefix}> **Error:** {e}\n\n"
        else:
            md += f"{prefix}```\n"
            for line in stdout_value.strip().split("\n"):
                md += f"{prefix}{line}\n" if line else f"{prefix}\n"
            md += f"{prefix}```\n\n"
    elif example.comparison_output and example.model_outputs:
        model_labels = {
            "pydantic_v1": "Pydantic v1",
            "pydantic_v2": "Pydantic v2",
            "dataclass": "dataclass",
            "typeddict": "TypedDict",
            "msgspec": "msgspec",
        }
        order = ["pydantic_v1", "pydantic_v2", "dataclass", "typeddict", "msgspec"]
        sorted_models = sorted(
            example.model_outputs.items(),
            key=lambda x: order.index(x[0]) if x[0] in order else len(order),
        )
        for model_key, output_file in sorted_models:
            label = model_labels.get(model_key, model_key)
            md += f'{prefix}=== "{label}"\n\n'
            try:
                content = read_expected_file(output_file)
                md += indent_code_block(content, prefix + "    ")
            except (FileNotFoundError, ValueError) as e:
                md += f"{prefix}    > **Error:** {e}\n\n"
        md += f'{prefix}=== "Without Option (Baseline)"\n\n'
        try:
            content = read_expected_file(example.comparison_output)
            md += indent_code_block(content, prefix + "    ")
        except (FileNotFoundError, ValueError) as e:
            md += f"{prefix}    > **Error:** {e}\n\n"
    elif example.comparison_output and example.golden_output:
        md += f'{prefix}=== "With Option"\n\n'
        try:
            content = read_expected_file(example.golden_output)
            md += indent_code_block(content, prefix + "    ")
        except (FileNotFoundError, ValueError) as e:
            md += f"{prefix}    > **Error:** {e}\n\n"
        md += f'{prefix}=== "Without Option"\n\n'
        try:
            content = read_expected_file(example.comparison_output)
            md += indent_code_block(content, prefix + "    ")
        except (FileNotFoundError, ValueError) as e:
            md += f"{prefix}    > **Error:** {e}\n\n"
    elif example.version_outputs:
        sorted_versions = sorted(
            example.version_outputs.items(),
            key=lambda x: tuple(map(int, x[0].split("."))),
        )
        for version, output_file in sorted_versions:
            md += f'{prefix}=== "Python {version}"\n\n'
            try:
                content = read_expected_file(output_file)
                md += indent_code_block(content, prefix + "    ")
            except (FileNotFoundError, ValueError) as e:
                md += f"{prefix}    > **Error:** {e}\n\n"
    elif example.model_outputs:
        model_labels = {
            "pydantic_v1": "Pydantic v1",
            "pydantic_v2": "Pydantic v2",
            "dataclass": "dataclass",
            "typeddict": "TypedDict",
            "msgspec": "msgspec",
        }
        order = ["pydantic_v1", "pydantic_v2", "dataclass", "typeddict", "msgspec"]
        sorted_models = sorted(
            example.model_outputs.items(),
            key=lambda x: order.index(x[0]) if x[0] in order else len(order),
        )
        for model_key, output_file in sorted_models:
            label = model_labels.get(model_key, model_key)
            md += f'{prefix}=== "{label}"\n\n'
            try:
                content = read_expected_file(output_file)
                md += indent_code_block(content, prefix + "    ")
            except (FileNotFoundError, ValueError) as e:
                md += f"{prefix}    > **Error:** {e}\n\n"
    elif example.golden_output:
        try:
            content = read_expected_file(example.golden_output)
            md += f"{prefix}```python\n"
            for line in content.strip().split("\n"):
                md += f"{prefix}{line}\n" if line else f"{prefix}\n"
            md += f"{prefix}```\n\n"
        except (FileNotFoundError, ValueError) as e:
            md += f"{prefix}> **Error:** {e}\n\n"
    return md


def _generate_example_with_input_output(example: CLIDocExample, prefix: str = "    ") -> str:
    """Generate combined input schema and output for an example."""
    md = ""

    # Input schema section
    if example.config_content:
        md += f"{prefix}**Configuration (pyproject.toml):**\n\n"
        md += f"{prefix}```toml\n"
        for line in example.config_content.strip().split("\n"):
            md += f"{prefix}{line}\n"
        md += f"{prefix}```\n\n"
    elif example.input_schema:
        md += f"{prefix}**Input Schema:**\n\n"
        try:
            schema_content = safe_read_file(
                DATA_PATH, example.input_schema, file_types=("*.json", "*.yaml", "*.yml", "*.graphql")
            )
            lang = _get_schema_lang(example.input_schema)
            md += f"{prefix}```{lang}\n"
            for line in schema_content.strip().split("\n"):
                md += f"{prefix}{line}\n"
            md += f"{prefix}```\n\n"
        except (FileNotFoundError, ValueError) as e:
            md += f"{prefix}> **Error:** {e}\n\n"

    # Output section
    md += f"{prefix}**Output:**\n\n"
    md += _generate_single_example_output(example, prefix)

    return md


def generate_option_section(
    option: str,
    cli_doc_option: CLIDocOption,
    option_related_pages: dict[str, list[tuple[str, str]]] | None = None,
) -> str:
    """Generate Markdown section for a single CLI option."""
    meta = get_option_meta(option)
    primary = cli_doc_option.get_primary()
    if not primary:
        return ""

    md = f"## `{option}` {{#{slugify(option)}}}\n\n"

    docstring = cli_doc_option.get_docstring()
    if docstring:
        md += f"{docstring.strip()}\n\n"

    meta_parts = []
    aliases = cli_doc_option.get_aliases()
    if aliases:
        aliases_str = ", ".join(f"`{a}`" for a in aliases)
        meta_parts.append(f"**Aliases:** {aliases_str}")
    if meta and meta.since_version:
        meta_parts.append(f"**Since:** {meta.since_version}")
    if meta and meta.deprecated:
        msg = meta.deprecated_message or "Deprecated"
        meta_parts.append(f"**Deprecated:** {msg}")
    related_options = cli_doc_option.get_related_options()
    if related_options:
        related_links = []
        for r in related_options:
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

    if option_related_pages and option in option_related_pages:
        related_page_links = []
        for page_path, page_title in option_related_pages[option]:
            related_page_links.append(f"[{page_title}](../{page_path})")
        md += f"**See also:** {', '.join(related_page_links)}\n\n"

    # Usage section (from primary example)
    md += '!!! tip "Usage"\n\n'
    md += "    ```bash\n"
    if primary.config_content:
        md += "    datamodel-codegen "
    else:
        md += "    datamodel-codegen --input schema.json "
    formatted_args = format_cli_args(primary.cli_args)
    md += " ".join(formatted_args)
    md += " # (1)!\n"
    md += "    ```\n\n"
    md += f"    1. :material-arrow-left: `{option}` - the option documented here\n\n"

    # Group examples by schema type
    examples_by_type: dict[str, list[CLIDocExample]] = defaultdict(list)
    for example in cli_doc_option.examples:
        schema_type = example.get_schema_type()
        examples_by_type[schema_type].append(example)

    # Determine if we need tabs (multiple schema types)
    schema_types = list(examples_by_type.keys())
    use_tabs = len(schema_types) > 1

    md += '??? example "Examples"\n\n'

    if use_tabs:
        # Multiple schema types - use tabs with input+output together
        schema_type_order = ["OpenAPI", "JSON Schema", "GraphQL", "JSON", "YAML", "CSV", "config", "Schema", "unknown"]
        sorted_types = sorted(schema_types, key=lambda t: schema_type_order.index(t) if t in schema_type_order else 999)

        for schema_type in sorted_types:
            examples = examples_by_type[schema_type]
            # Use first example of this type (or primary if it's of this type)
            example = next((ex for ex in examples if ex.is_primary), examples[0])

            md += f'    === "{schema_type}"\n\n'
            md += _generate_example_with_input_output(example, "        ")
    else:
        # Single schema type - show input schema and output separately (original behavior)
        example = primary

        if example.config_content:
            md += "    **Configuration (pyproject.toml):**\n\n"
            md += "    ```toml\n"
            for line in example.config_content.strip().split("\n"):
                md += f"    {line}\n"
            md += "    ```\n\n"
        elif example.input_schema:
            md += "    **Input Schema:**\n\n"
            try:
                schema_content = safe_read_file(
                    DATA_PATH, example.input_schema, file_types=("*.json", "*.yaml", "*.yml", "*.graphql")
                )
                lang = _get_schema_lang(example.input_schema)
                md += f"    ```{lang}\n"
                for line in schema_content.strip().split("\n"):
                    md += f"    {line}\n"
                md += "    ```\n\n"
            except (FileNotFoundError, ValueError) as e:
                md += f"    > **Error:** {e}\n\n"

        md += "    **Output:**\n\n"
        md += _generate_single_example_output(example, "    ")

    md += "---\n\n"
    return md


def generate_category_page(
    category: OptionCategory,
    options: dict[str, CLIDocOption],
    option_related_pages: dict[str, list[tuple[str, str]]] | None = None,
) -> str:
    """Generate a category page with all options."""
    emoji = CATEGORY_EMOJIS.get(category, "📋")
    md = f"# {emoji} {category.value}\n\n"
    md += "## 📋 Options\n\n"
    md += "| Option | Description |\n"
    md += "|--------|-------------|\n"
    for option in sorted(options.keys()):
        cli_doc_option = options[option]
        docstring = cli_doc_option.get_docstring()
        desc = docstring.split("\n")[0][:DESC_LENGTH_SHORT] if docstring else ""
        if len(desc) == DESC_LENGTH_SHORT:
            desc += "..."
        md += f"| [`{option}`](#{slugify(option)}) | {desc} |\n"
    md += "\n---\n\n"

    for option in sorted(options.keys()):
        cli_doc_option = options[option]
        md += generate_option_section(option, cli_doc_option, option_related_pages)

    return md


def generate_quick_reference(
    categories: dict[OptionCategory, dict[str, CLIDocOption]],
    manual_docs: dict[str, str] | None = None,
) -> str:
    """Generate a quick reference page with all options in CLI format for easy searching."""
    md = "# 🔍 Quick Reference\n\n"
    md += "All CLI options in one page for easy **Ctrl+F** searching.\n\n"
    md += "👆 Click any option to see detailed documentation with examples.\n\n"

    # Collect all options with their descriptions
    all_options: list[tuple[str, str, OptionCategory | None]] = []
    for category, options in categories.items():
        for option, cli_doc_option in options.items():
            docstring = cli_doc_option.get_docstring()
            desc = docstring.split("\n")[0] if docstring else ""
            all_options.append((option, desc, category))
    if manual_docs:
        for option in manual_docs:
            desc = MANUAL_OPTION_DESCRIPTIONS.get(option, "")
            all_options.append((option, desc, None))

    # Sort alphabetically by option name
    all_options.sort(key=operator.itemgetter(0))

    md += "---\n\n"
    md += "```text\n"
    md += "datamodel-codegen [OPTIONS]\n"
    md += "```\n\n"

    # Group by category for organized display
    md += "## 📂 All Options by Category\n\n"

    for category in OptionCategory:
        if category not in categories:
            continue
        options = categories[category]
        if not options:
            continue

        slug_cat = slugify(category.value)
        emoji = CATEGORY_EMOJIS.get(category, "📋")
        md += f"### {emoji} {category.value}\n\n"
        md += "| Option | Description |\n"
        md += "|--------|-------------|\n"

        for option in sorted(options.keys()):
            cli_doc_option = options[option]
            docstring = cli_doc_option.get_docstring()
            desc = docstring.split("\n")[0][:DESC_LENGTH_LONG] if docstring else ""
            if len(desc) == DESC_LENGTH_LONG:
                desc += "..."
            slug_opt = slugify(option)
            md += f"| [`{option}`]({slug_cat}.md#{slug_opt}) | {desc} |\n"

        md += "\n"

    if manual_docs:
        md += "### 📝 Utility Options\n\n"
        md += "| Option | Description |\n"
        md += "|--------|-------------|\n"
        for option in sorted(manual_docs.keys()):
            desc = MANUAL_OPTION_DESCRIPTIONS.get(option, "")
            slug_opt = slugify(option)
            md += f"| [`{option}`](utility-options.md#{slug_opt}) | {desc} |\n"
        md += "\n"

    # Alphabetical list for Ctrl+F
    md += "---\n\n"
    md += "## 🔤 Alphabetical Index\n\n"
    md += "All options sorted alphabetically:\n\n"

    for option, desc, category in all_options:
        if category is None:
            md += f"- [`{option}`](utility-options.md#{slugify(option)}) - {desc}\n"
        else:
            slug_cat = slugify(category.value)
            slug_opt = slugify(option)
            short_desc = desc[:DESC_LENGTH_SHORT] + "..." if len(desc) > DESC_LENGTH_SHORT else desc
            md += f"- [`{option}`]({slug_cat}.md#{slug_opt}) - {short_desc}\n"

    return md


def generate_index_page(
    categories: dict[OptionCategory, dict[str, CLIDocOption]],
    manual_docs: dict[str, str] | None = None,
) -> str:
    """Generate the index page with overview of all categories."""
    md = "# 🖥️ CLI Reference\n\n"
    md += "This documentation is auto-generated from test cases.\n\n"
    md += "🔍 **[Quick Reference](quick-reference.md)** - All options on one page for Ctrl+F search\n\n"

    md += "## 📂 Categories\n\n"
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
            emoji = CATEGORY_EMOJIS.get(category, "📋")
            md += f"| {emoji} [{category.value}]({slug}.md) | {count} | {desc} |\n"

    if manual_docs:
        md += f"| 📝 [Utility Options](utility-options.md) | {len(manual_docs)} | Help, version, debug options |\n"

    md += "\n"
    md += "## All Options\n\n"
    all_options: list[tuple[str, OptionCategory | None]] = []
    for category, options in categories.items():
        all_options.extend((option, category) for option in options)
    if manual_docs:
        all_options.extend((option, None) for option in manual_docs)

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
        if category is None:
            md += f"- [`{option}`](utility-options.md#{slugify(option)})\n"
        else:
            slug_cat = slugify(category.value)
            slug_opt = slugify(option)
            md += f"- [`{option}`]({slug_cat}.md#{slug_opt})\n"

    return md


def read_manual_docs() -> dict[str, str]:
    """Read manual documentation files from MANUAL_DOCS_DIR.

    Returns:
        Dictionary mapping option name to markdown content.
    """
    manual_docs: dict[str, str] = {}
    if not MANUAL_DOCS_DIR.exists():
        return manual_docs

    for md_file in MANUAL_DOCS_DIR.glob("*.md"):
        option_name = f"--{md_file.stem}"
        if option_name in MANUAL_DOCS:
            manual_docs[option_name] = md_file.read_text(encoding="utf-8")
    return manual_docs


def generate_manual_docs_section(manual_docs: dict[str, str]) -> str:
    """Generate markdown page for manual documentation options."""
    if not manual_docs:
        return ""

    md = "# 📝 Utility Options\n\n"
    md += "## 📋 Options\n\n"
    md += "| Option | Description |\n"
    md += "|--------|-------------|\n"

    for option in sorted(manual_docs.keys()):
        desc = MANUAL_OPTION_DESCRIPTIONS.get(option, "")
        md += f"| [`{option}`](#{slugify(option)}) | {desc} |\n"

    md += "\n---\n\n"

    for option in sorted(manual_docs.keys()):
        content = manual_docs[option]
        md += content
        if not content.endswith("\n"):
            md += "\n"
        md += "\n---\n\n"

    return md


def collect_cli_docs() -> int:
    """Run pytest to collect CLI doc metadata."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-cli-docs", "-p", "no:xdist", "-q"],
        check=False,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )
    if result.returncode != 0:
        return result.returncode
    return 0


def build_docs(*, check: bool = False) -> int:
    """Build CLI documentation from collection data.

    Args:
        check: If True, validate that existing docs match generated content.
               Returns error if any differences found.
    """
    items: list[dict[str, Any]] = []
    if COLLECTION_PATH.exists():
        with Path(COLLECTION_PATH).open(encoding="utf-8") as f:
            collection = json.load(f)

        schema_version = collection.get("schema_version", 0)
        if schema_version != 1:
            pass

        items = collection.get("items", [])

    manual_docs = read_manual_docs()
    if not items and not manual_docs:
        return 0

    # Group by canonical option - collect ALL examples per option
    options_map: dict[str, CLIDocOption] = {}
    for item in items:
        example = CLIDocExample.from_item(item)
        for opt in item["marker_kwargs"].get("options", []):
            canonical = get_canonical_option(opt)
            if is_manual_doc(canonical):
                continue
            if canonical not in options_map:
                options_map[canonical] = CLIDocOption(option_name=canonical)
            options_map[canonical].add_example(example)

    categories: dict[OptionCategory, dict[str, CLIDocOption]] = defaultdict(dict)

    for option, cli_doc_option in options_map.items():
        meta = get_option_meta(option)
        if meta:
            categories[meta.category][option] = cli_doc_option
        else:
            categories[OptionCategory.GENERAL][option] = cli_doc_option

    # Scan markdown files for CLI option tags
    option_related_pages = scan_docs_for_cli_option_tags()

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

    # Iterate in OptionCategory enum order for consistent output
    for category in OptionCategory:
        if category not in categories:
            continue
        options = categories[category]
        if not options:
            continue
        try:
            md = generate_category_page(category, options, option_related_pages)
            output_path = DOCS_OUTPUT / f"{slugify(category.value)}.md"
            write_or_check(output_path, md, f"{output_path.name} ({len(options)} options)")
        except (OSError, ValueError, KeyError) as e:
            print(f"Error generating {category.value}: {e}", file=sys.stderr)
            errors += 1

    if manual_docs:
        try:
            md = generate_manual_docs_section(manual_docs)
            output_path = DOCS_OUTPUT / "utility-options.md"
            write_or_check(output_path, md, f"utility-options.md ({len(manual_docs)} options)")
        except (OSError, ValueError, KeyError) as e:
            print(f"Error generating utility-options.md: {e}", file=sys.stderr)
            errors += 1

    try:
        md = generate_index_page(categories, manual_docs)
        output_path = DOCS_OUTPUT / "index.md"
        write_or_check(output_path, md, "index.md")
    except (OSError, ValueError, KeyError) as e:
        print(f"Error generating index.md: {e}", file=sys.stderr)
        errors += 1

    try:
        md = generate_quick_reference(categories, manual_docs)
        output_path = DOCS_OUTPUT / "quick-reference.md"
        total_options = sum(len(opts) for opts in categories.values()) + len(manual_docs)
        write_or_check(output_path, md, f"quick-reference.md ({total_options} options)")
    except (OSError, ValueError, KeyError) as e:
        print(f"Error generating quick-reference.md: {e}", file=sys.stderr)
        errors += 1

    if check:
        if errors:
            print(f"Generation errors occurred: {errors}", file=sys.stderr)
            return 1
        if mismatches:
            for m in mismatches:
                print(f"Mismatch: {m}", file=sys.stderr)
            return 1
        return 0
    if errors:
        print(f"Errors occurred: {errors}", file=sys.stderr)
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
