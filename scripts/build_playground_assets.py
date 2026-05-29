"""Build browser playground assets from Python sources."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from datamodel_code_generator.arguments import arg_parser
from datamodel_code_generator.cli_options import CLI_OPTION_META, OptionCategory
from datamodel_code_generator.enums import InputFileType

ROOT = Path(__file__).resolve().parents[1]
PLAYGROUND_ROOT = ROOT / "docs" / "assets" / "playground"
GENERATED_ROOT = PLAYGROUND_ROOT / "generated"
METADATA_PATH = GENERATED_ROOT / "codegen-ui-metadata.json"
APP_SHELL_PATH = GENERATED_ROOT / "app-shell.html"

BROWSER_SUPPORTED_INPUT_TYPES = {
    InputFileType.Auto.value,
    InputFileType.OpenAPI.value,
    InputFileType.AsyncAPI.value,
    InputFileType.JsonSchema.value,
    InputFileType.XMLSchema.value,
    InputFileType.Avro.value,
    InputFileType.Json.value,
    InputFileType.Yaml.value,
    InputFileType.Dict.value,
    InputFileType.CSV.value,
    InputFileType.GraphQL.value,
}

HIDDEN_OPTIONS = {
    "allow_remote_refs",
    "http_headers",
    "http_ignore_tls",
    "http_local_ref_path",
    "http_query_parameters",
    "http_timeout",
    "input",
    "input_file_type",
    "input_model",
    "output",
    "url",
}

UNSUPPORTED_REASONS = {
    "allow_remote_refs": "Server-only or unsafe in a browser sandbox.",
    "http_headers": "Server-only or unsafe in a browser sandbox.",
    "http_ignore_tls": "Server-only or unsafe in a browser sandbox.",
    "http_local_ref_path": "Server-only or unsafe in a browser sandbox.",
    "http_query_parameters": "Server-only or unsafe in a browser sandbox.",
    "http_timeout": "Server-only or unsafe in a browser sandbox.",
    "input": "Use the schema editor.",
    "input_file_type": "Use the top input selector.",
    "input_model": "Python module imports are not available in the browser playground.",
    "output": "Output is shown in the browser.",
    "url": "Remote input URLs are not fetched by the browser playground.",
}

CATEGORY_ORDER = [
    OptionCategory.GENERAL.value,
    OptionCategory.BASE.value,
    OptionCategory.MODEL.value,
    OptionCategory.TEMPLATE.value,
    OptionCategory.FIELD.value,
    OptionCategory.TYPING.value,
    OptionCategory.OPENAPI.value,
    OptionCategory.GRAPHQL.value,
]


def _long_options(action: argparse.Action) -> list[str]:
    return [option for option in action.option_strings if option.startswith("--")]


def _option_name(action: argparse.Action) -> str | None:
    options = _long_options(action)
    for option in options:
        if not option.startswith("--no-"):
            return option
    return options[0] if options else None


def _negative_name(action: argparse.Action) -> str | None:
    for option in _long_options(action):
        if option.startswith("--no-"):
            return option
    return None


def _choices(action: argparse.Action) -> list[str]:
    if not action.choices:
        return []
    return [getattr(choice, "value", str(choice)) for choice in action.choices]


def _control(action: argparse.Action) -> str:
    store_boolean_actions = (argparse._StoreTrueAction, argparse._StoreFalseAction)  # noqa: SLF001
    if action.choices:
        return "select"
    if isinstance(action, argparse.BooleanOptionalAction):
        return "boolean"
    if isinstance(action, store_boolean_actions):
        return "checkbox"
    if action.nargs in {"+", "*"}:
        return "list"
    if action.type in {int, float}:
        return "number"
    return "text"


def _clean_help(action: argparse.Action) -> str:
    if action.help in {None, argparse.SUPPRESS}:
        return ""
    return str(action.help).replace("%(default)s", str(action.default))


def _category(option_name: str) -> str:
    if option_name in CLI_OPTION_META:
        return CLI_OPTION_META[option_name].category.value
    return OptionCategory.GENERAL.value


def _option_metadata(action: argparse.Action) -> dict[str, Any] | None:
    name = _option_name(action)
    if not name:
        return None

    meta = CLI_OPTION_META.get(name)
    browser_supported = action.dest not in HIDDEN_OPTIONS
    return {
        "name": name,
        "negative_name": _negative_name(action),
        "dest": action.dest,
        "label": name.removeprefix("--"),
        "category": _category(name),
        "control": _control(action),
        "choices": _choices(action),
        "help": _clean_help(action),
        "browser_supported": browser_supported,
        "unsupported_reason": UNSUPPORTED_REASONS.get(action.dest, ""),
        "deprecated": bool(meta and meta.deprecated),
        "deprecated_message": meta.deprecated_message if meta else None,
        "hidden": not browser_supported,
    }


def _input_formats() -> list[dict[str, Any]]:
    formats = []
    for item in InputFileType:
        supported = item.value in BROWSER_SUPPORTED_INPUT_TYPES
        formats.append({
            "name": item.name,
            "value": item.value,
            "label": item.name,
            "browser_supported": supported,
            "unsupported_reason": "" if supported else "Not available in the browser playground.",
        })
    return formats


def build_metadata() -> dict[str, Any]:
    """Return playground metadata derived from the current CLI parser."""
    options = [
        option
        for action in arg_parser._actions  # noqa: SLF001
        if (option := _option_metadata(action)) is not None
    ]
    category_indexes = {category: index for index, category in enumerate(CATEGORY_ORDER)}
    options.sort(key=lambda option: (category_indexes.get(option["category"], len(category_indexes)), option["name"]))
    groups = [
        {
            "category": category,
            "options": [option for option in options if option["category"] == category],
        }
        for category in CATEGORY_ORDER
        if any(option["category"] == category for option in options)
    ]
    return {
        "formats": _input_formats(),
        "options": options,
        "groups": groups,
    }


def _load_playground_app() -> Any:
    spec = importlib.util.spec_from_file_location("playground_app", PLAYGROUND_ROOT / "app.py")
    if spec is None or spec.loader is None:
        message = "Could not load playground app module"
        raise RuntimeError(message)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    """Write generated playground assets."""
    metadata = build_metadata()
    metadata_json = json.dumps(metadata, indent=2, ensure_ascii=False) + "\n"
    GENERATED_ROOT.mkdir(parents=True, exist_ok=True)
    METADATA_PATH.write_text(metadata_json, encoding="utf-8")

    app = _load_playground_app()
    app.set_ui_metadata(metadata_json)
    APP_SHELL_PATH.write_text(
        app.render_app(status="Loading Python runtime...") + "\n",
        encoding="utf-8",
    )

    print(f"Generated {METADATA_PATH.relative_to(ROOT)}")
    print(f"Generated {APP_SHELL_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    if sys.version_info < (3, 14):
        message = "Playground assets must be built with Python 3.14+ for t-string syntax."
        raise SystemExit(message)
    main()
