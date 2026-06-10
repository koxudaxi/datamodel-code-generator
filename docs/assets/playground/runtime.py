from __future__ import annotations

import json
import tomllib
import traceback
from typing import Any

from datamodel_code_generator import InputFileType, generate
from datamodel_code_generator.__main__ import EXCLUDED_CONFIG_OPTIONS, generate_cli_command
from datamodel_code_generator.format import Formatter

SAMPLE_SCHEMA = """{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Pet",
  "type": "object",
  "properties": {
    "id": { "type": "integer" },
    "name": { "type": "string" },
    "tags": {
      "type": "array",
      "items": { "type": "string" }
    }
  },
  "required": ["id", "name"]
}"""

SAMPLE_SCHEMAS = {
    "auto": SAMPLE_SCHEMA,
    "jsonschema": SAMPLE_SCHEMA,
    "openapi": """{
  "openapi": "3.1.0",
  "info": {
    "title": "Pet API",
    "version": "1.0.0"
  },
  "paths": {},
  "components": {
    "schemas": {
      "Pet": {
        "type": "object",
        "properties": {
          "id": { "type": "integer" },
          "name": { "type": "string" },
          "tags": {
            "type": "array",
            "items": { "type": "string" }
          }
        },
        "required": ["id", "name"]
      }
    }
  }
}""",
    "json": """{
  "id": 1,
  "name": "Milo",
  "tags": ["cat", "indoor"]
}""",
    "yaml": """id: 1
name: Milo
tags:
  - cat
  - indoor
""",
    "dict": """{
  "id": 1,
  "name": "Milo",
  "tags": ["cat", "indoor"]
}""",
    "csv": """id,name,age
1,Milo,3
2,Luna,2
""",
    "graphql": """type Pet {
  id: ID!
  name: String!
  tags: [String!]
}
""",
}

UI_METADATA: dict[str, Any] = {"formats": [], "options": [], "groups": []}
PLAYGROUND_FORMATTERS = [Formatter.BUILTIN]
GENERATE_FORCED_OPTIONS = {
    "output": None,
    "formatters": PLAYGROUND_FORMATTERS,
}
CONFIG_FORCED_OPTIONS = {
    "formatters": [formatter.value for formatter in PLAYGROUND_FORMATTERS],
}
CONFIG_TABLE = "tool.datamodel-codegen"


def set_ui_metadata(metadata_json: str) -> None:
    global UI_METADATA  # noqa: PLW0603
    UI_METADATA = json.loads(metadata_json)


def default_input_type() -> str:
    for item in UI_METADATA["formats"]:
        if item["value"] == "jsonschema":
            return "jsonschema"
    return UI_METADATA["formats"][0]["value"] if UI_METADATA["formats"] else "jsonschema"


def sample_schema(input_type: str = "") -> str:
    return SAMPLE_SCHEMAS.get(input_type or default_input_type(), SAMPLE_SCHEMA)


def export_ui_options() -> str:
    return json.dumps(UI_METADATA, ensure_ascii=False)


def _options_by_dest() -> dict[str, dict[str, Any]]:
    return {option["dest"]: option for option in UI_METADATA["options"] if option["browser_supported"]}


def _options_by_name() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for option in UI_METADATA["options"]:
        if not option["browser_supported"]:
            continue
        result[option["name"]] = option
        if negative_name := option.get("negative_name"):
            result[negative_name] = option
    return result


def _split_delimited(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value).replace(",", "\n").splitlines() if item.strip()]


def _coerce_option_value(option: dict[str, Any], value: Any) -> Any:
    if value == "" or value is None or value == []:
        return None

    result: Any
    match option["control"], value:
        case ("checkbox" | "boolean", True | "true"):
            result = True
        case ("checkbox" | "boolean", False | "false"):
            result = False
        case ("checkbox" | "boolean", _):
            result = None
        case ("list", list()):
            result = value
        case ("list", _):
            result = _split_delimited(value)
        case ("number", _):
            text = str(value)
            result = float(text) if "." in text else int(text)
        case _:
            result = value
    return result


def _coerce_for_generate(option: dict[str, Any], value: Any) -> Any:
    if (coerced := _coerce_option_value(option, value)) is None:
        return None
    match option.get("value_kind"):
        case "json":
            try:
                return json.loads(coerced) if isinstance(coerced, str) else coerced
            except json.JSONDecodeError:
                return None
        case "key_value":
            pairs = (item.partition("=") for item in _split_delimited(coerced))
            return {key: val for key, sep, val in pairs if sep and key} or None
        case "collection":
            return coerced if isinstance(coerced, list) else _split_delimited(coerced)
    return coerced


def _coerce_for_config(option: dict[str, Any], value: Any) -> Any:
    return _coerce_for_generate(option, value)


def _relation_source_matches(value: Any, relation: dict[str, Any]) -> bool:
    value = getattr(value, "value", value)
    if "when" not in relation:
        return bool(value)
    match relation["when"]:
        case list() as values:
            return value in values
        case expected:
            return value == expected


def _apply_generate_option_implications(options: dict[str, Any]) -> None:
    options_by_name = _options_by_name()
    changed = True
    while changed:
        changed = False
        for option in UI_METADATA["options"]:
            if not (relations := option.get("implies")):
                continue
            source_key = option.get("config_dest", option["dest"])
            if source_key not in options:
                continue
            for relation in relations:
                if not _relation_source_matches(options[source_key], relation):
                    continue
                if not (target := options_by_name.get(relation["option"])):
                    continue
                target_key = relation.get("config_dest", target.get("config_dest", target["dest"]))
                target_value = relation.get("value", True)
                if options.get(target_key) == target_value:
                    continue
                options[target_key] = target_value
                changed = True


def _normalize_options(
    options: dict[str, Any], *, include_forced: bool = True, for_config: bool = False, for_generate: bool = False
) -> dict[str, Any]:
    options_by_dest = _options_by_dest()
    normalized: dict[str, Any] = {}
    for key, value in options.items():
        if (option := options_by_dest.get(key)) is None:
            continue
        if for_generate:
            normalized_value = _coerce_for_generate(option, value)
        elif for_config:
            normalized_value = _coerce_for_config(option, value)
        else:
            normalized_value = _coerce_option_value(option, value)
        if normalized_value is None or normalized_value == []:
            continue
        normalized[option.get("config_dest", key) if for_generate else key] = normalized_value
    if for_generate:
        _apply_generate_option_implications(normalized)
    if include_forced:
        normalized.update(GENERATE_FORCED_OPTIONS)
    return normalized


def _config_options(options_json: str = "{}", input_type: str = "") -> dict[str, Any]:
    options = json.loads(options_json) if options_json else {}
    normalized_options = _normalize_options(options, include_forced=False, for_config=True)
    normalized_options.update(CONFIG_FORCED_OPTIONS)
    if input_type and input_type != "auto":
        normalized_options["input_file_type"] = input_type
    return normalized_options


def _cli_options(options_json: str = "{}", input_type: str = "") -> dict[str, Any]:
    options = json.loads(options_json) if options_json else {}
    normalized_options = _normalize_options(options, include_forced=False)
    normalized_options.update(CONFIG_FORCED_OPTIONS)
    if input_type and input_type != "auto":
        normalized_options["input_file_type"] = input_type
    return normalized_options


def _format_toml_value(value: Any) -> str:
    result = json.dumps(str(value), ensure_ascii=False)
    match value:
        case bool():
            result = "true" if value else "false"
        case int() | float():
            result = str(value)
        case str():
            result = json.dumps(value, ensure_ascii=False)
        case list() | tuple():
            result = f"[{', '.join(_format_toml_value(item) for item in value)}]"
        case dict():
            items = ", ".join(
                f"{json.dumps(str(key), ensure_ascii=False)} = {_format_toml_value(item)}"
                for key, item in sorted(value.items())
            )
            result = f"{{ {items} }}"
    return result


def export_config_toml(options_json: str = "{}", input_type: str = "") -> str:
    option_lines = [
        f"{key.replace('_', '-')} = {_format_toml_value(value)}"
        for key, value in sorted(_config_options(options_json, input_type).items())
        if key not in EXCLUDED_CONFIG_OPTIONS
    ]
    return "\n".join((f"[{CONFIG_TABLE}]", *option_lines)) + "\n"


def build_cli_options(options_json: str = "{}", input_type: str = "") -> str:
    return generate_cli_command(_cli_options(options_json, input_type)).strip()


def _json_result(**payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _config_table(data: dict[str, Any]) -> dict[str, Any]:
    tool_config = data.get("tool", {}).get("datamodel-codegen")
    return tool_config if isinstance(tool_config, dict) else data


def _form_option_value(option: dict[str, Any], value: Any) -> Any:
    match option.get("value_kind"), value:
        case "key_value", dict():
            return "\n".join(f"{key}={item}" for key, item in value.items())
        case "json", dict() | list():
            return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        case "collection", list() | tuple() | set():
            separator = "\n" if option["control"] == "list" else ","
            return separator.join(str(item) for item in value)
    return value


def _is_browser_formatter(value: Any) -> bool:
    return _split_delimited(value) == [Formatter.BUILTIN.value]


def import_config_toml(config_toml: str) -> str:
    try:
        config = _config_table(tomllib.loads(config_toml))
        if not isinstance(config, dict):
            return _json_result(ok=False, error=f"[{CONFIG_TABLE}] must be a table")

        options_by_dest = _options_by_dest()
        input_values = {item["value"] for item in UI_METADATA["formats"] if item["browser_supported"]}
        imported_options: dict[str, Any] = {}
        ignored: list[str] = []
        input_type = ""

        for raw_key, value in config.items():
            key = str(raw_key).replace("-", "_")
            match key:
                case "profiles":
                    ignored.append(str(raw_key))
                case "input_file_type" if (text_value := str(value)) in input_values:
                    input_type = text_value
                case "input_file_type":
                    ignored.append(str(raw_key))
                case "formatters" if _is_browser_formatter(value):
                    pass
                case _ if key in EXCLUDED_CONFIG_OPTIONS or key not in options_by_dest:
                    ignored.append(str(raw_key))
                case _:
                    imported_options[key] = _form_option_value(options_by_dest[key], value)

        return _json_result(ok=True, inputType=input_type, options=imported_options, ignored=ignored)
    except Exception as exc:
        return _json_result(ok=False, error=str(exc))


def generate_in_browser(schema: str, input_type: str, options_json: str = "{}") -> str:
    try:
        options = json.loads(options_json) if options_json else {}
        result = generate(
            schema,
            input_file_type=InputFileType(input_type),
            **_normalize_options(options, for_generate=True),
            disable_timestamp=True,
        )
    except Exception:
        return json.dumps({"ok": False, "error": traceback.format_exc()})

    if isinstance(result, dict):
        sections = []
        for path, content in sorted(result.items()):
            name = "/".join(path) if isinstance(path, tuple) else str(path)
            sections.append(f"# file: {name}\n{content}")
        result = "\n\n".join(sections)
    return json.dumps({"ok": True, "output": result or ""})
