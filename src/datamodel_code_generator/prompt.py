"""Prompt generation for LLM consultation.

This module generates prompts suitable for consulting LLMs (ChatGPT, Claude, etc.)
about appropriate CLI options for datamodel-code-generator.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from datamodel_code_generator.cli_options import CLI_OPTION_META, OptionCategory
from datamodel_code_generator.prompt_data import OPTION_DESCRIPTIONS

if TYPE_CHECKING:
    from argparse import Namespace

# Options to exclude from prompt output
PROMPT_EXCLUDED_OPTIONS: frozenset[str] = frozenset({
    "generate_prompt",
    "generate_pyproject_config",
    "generate_cli_command",
    "version",
    "help",
    "no_color",
})

PROMPT_GUIDANCE_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Agent Task",
        (
            "Recommend a final CLI command for the user's schema and target runtime. Include:",
            "- Final `datamodel-codegen` command in a shell code block.",
            "- Brief explanation for each selected option.",
            "- Rejected alternatives with the reason they do not fit.",
            (
                "- Verification command, such as `datamodel-codegen ... --output models.py --check` "
                "(`--check` requires `--output`) or a diff against expected output."
            ),
        ),
    ),
    (
        "Decision Checklist",
        (
            "- Input type: JSON Schema, OpenAPI, GraphQL, CSV, Python input model, or raw JSON/YAML data.",
            "- Output model type: Pydantic v1/v2, dataclasses, TypedDict, msgspec, or a custom base class.",
            (
                "- Python/Pydantic version: align `--target-python-version`, `--output-model-type`, and "
                "`--target-pydantic-version`."
            ),
            (
                "- Strictness: choose `--strict-types` values, `--strict-nullable`, `--field-constraints`, and "
                "`--extra-fields`."
            ),
            (
                "- Aliases/naming: decide between API-compatible aliases and normalized names such as "
                "`--snake-case-field`."
            ),
            "- Module layout: choose one file or an output directory with `--module-split-mode` and reuse options.",
            "- Validation constraints: prefer `--field-constraints`; add `--use-annotated` for Pydantic v2.",
        ),
    ),
    (
        "Common Recipes",
        (
            (
                "- Strict Pydantic v2: `--output-model-type pydantic_v2.BaseModel --target-pydantic-version 2.11 "
                "--use-annotated --field-constraints`, plus needed `--strict-types` values."
            ),
            (
                "- OpenAPI request/response models: `--input-file-type openapi --openapi-scopes schemas paths "
                "--read-only-write-only-model-type request-response`."
            ),
            (
                "- TypedDict modern syntax: `--output-model-type typing.TypedDict --target-python-version 3.12 "
                "--use-standard-collections --use-union-operator`."
            ),
            (
                "- Multi-module OpenAPI output: set `--output` to a directory and use `--module-split-mode single "
                "--all-exports-scope recursive --use-exact-imports`."
            ),
        ),
    ),
    (
        "Important Option Relationships",
        (
            "- `--use-annotated` also enables `--field-constraints`; prefer it for constrained Pydantic v2 fields.",
            "- `--openapi-include-paths` only has an effect when `--openapi-scopes paths` is included.",
            "- `--strict-types` requires one or more values: `str`, `int`, `float`, `bool`, or `bytes`.",
            "- `--use-specialized-enum` requires `--target-python-version >= 3.11`.",
            "- `--validation` is deprecated; use `--field-constraints` for generated Field constraints.",
        ),
    ),
)


def _format_current_options(args: Namespace) -> str:
    """Format currently set CLI options."""
    lines: list[str] = []
    args_dict = vars(args)

    for key, value in sorted(args_dict.items()):
        if value is None:
            continue
        if key in PROMPT_EXCLUDED_OPTIONS:
            continue

        cli_key = key.replace("_", "-")

        if isinstance(value, bool):
            if value:
                lines.append(f"--{cli_key}")
        elif isinstance(value, list):
            formatted = " ".join(str(v) for v in value)
            lines.append(f"--{cli_key} {formatted}")
        else:
            lines.append(f"--{cli_key} {value}")

    return "\n".join(lines) if lines else "(No options specified)"


def _format_options_by_category() -> str:
    """Format options grouped by category with descriptions."""
    by_category: dict[OptionCategory, list[tuple[str, str]]] = defaultdict(list)

    for option, meta in CLI_OPTION_META.items():
        desc = OPTION_DESCRIPTIONS.get(option, "")
        by_category[meta.category].append((option, desc))

    lines: list[str] = []
    for category in OptionCategory:
        options = by_category[category]
        lines.append(f"### {category.value}")
        for opt, desc in sorted(options):
            if desc:
                lines.append(f"- `{opt}`: {desc}")
            else:  # pragma: no cover
                lines.append(f"- `{opt}`")
        lines.append("")

    return "\n".join(lines)


def _format_guidance_sections() -> str:
    """Format concise agent guidance sections."""
    lines: list[str] = []

    for title, entries in PROMPT_GUIDANCE_SECTIONS:
        lines.extend((f"## {title}", ""))
        lines.extend(entries)
        lines.append("")

    return "\n".join(lines)


def generate_prompt(args: Namespace, help_text: str) -> str:
    """Generate LLM consultation prompt.

    Args:
        args: Parsed command-line arguments.
        help_text: Full help text from arg_parser.format_help().

    Returns:
        Formatted prompt string suitable for LLM consultation.
    """
    lines: list[str] = []

    # Header
    lines.extend(("# datamodel-code-generator CLI Options Consultation", ""))

    # User's question (if provided)
    question = getattr(args, "generate_prompt", "") or ""
    if question:
        lines.extend(("## Your Question", "", question, ""))

    # Current configuration
    lines.extend((
        "## Current CLI Options",
        "",
        "```",
        _format_current_options(args),
        "```",
        "",
        # Options by category with descriptions
        "## Options by Category",
        "",
        _format_options_by_category(),
        # Full help text
        "## All Available Options (Full Help)",
        "",
        "```",
        help_text,
        "```",
        "",
        # Concise guidance for LLM agents choosing option combinations
        _format_guidance_sections(),
        # Instructions for LLM
        "## Instructions",
        "",
        "Based on the above information, please help with the question or suggest",
        "appropriate CLI options for the use case. Consider:",
        "",
        "1. The current options already set",
        "2. Option descriptions and their purposes",
        "3. Potential conflicts between options",
        "4. Best practices for the target output format",
    ))

    return "\n".join(lines)
