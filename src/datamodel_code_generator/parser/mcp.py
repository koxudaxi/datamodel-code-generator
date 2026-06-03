"""MCP tool schema profile support."""

from __future__ import annotations

import re
from collections.abc import Mapping
from copy import deepcopy
from typing import Any, Literal

from typing_extensions import NotRequired, TypedDict, TypeIs

from datamodel_code_generator import Error

JSON_SCHEMA_DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"
DEFINITION_KEYS = ("$defs", "definitions")
OPTIONAL_STRING_TOOL_KEYS = ("title", "description")
OPTIONAL_MAPPING_TOOL_KEYS = ("outputSchema", "annotations", "_meta")
SchemaKey = Literal["inputSchema", "outputSchema"]


class MCPTool(TypedDict):
    """Validated MCP tool definition mapping."""

    name: str
    inputSchema: Mapping[str, Any]
    outputSchema: NotRequired[Mapping[str, Any]]
    title: NotRequired[str]
    description: NotRequired[str]
    annotations: NotRequired[Mapping[str, Any]]
    _meta: NotRequired[Mapping[str, Any]]


def _is_json_schema_object(value: object) -> TypeIs[Mapping[str, Any]]:
    return isinstance(value, Mapping)


def _has_tool_schema_key(value: Mapping[str, Any]) -> bool:
    return "inputSchema" in value or "outputSchema" in value


def _tool_shape_error(value: Mapping[str, Any], tool_name: str) -> str | None:
    if "inputSchema" not in value:
        return f"MCP tool {tool_name!r} is missing inputSchema"
    if not _is_json_schema_object(value["inputSchema"]):
        return f"MCP tool {tool_name!r} inputSchema must be a JSON Schema object"
    for key in OPTIONAL_MAPPING_TOOL_KEYS:
        if key in value and not _is_json_schema_object(value[key]):
            return f"MCP tool {tool_name!r} {key} must be a JSON Schema object"
    for key in OPTIONAL_STRING_TOOL_KEYS:
        if key in value and not isinstance(value[key], str):
            return f"MCP tool {tool_name!r} {key} must be a string"
    return None


def _is_tool(value: object) -> TypeIs[MCPTool]:
    return (
        _is_json_schema_object(value)
        and isinstance(tool_name := value.get("name"), str)
        and _tool_shape_error(value, tool_name) is None
    )


def _coerce_tool(value: Any, fallback_name: str | None = None) -> MCPTool | None:
    if fallback_name is not None and isinstance(value, Mapping) and _has_tool_schema_key(value):
        value = {"name": fallback_name, **value}
    if _is_tool(value):
        return value
    if (
        isinstance(value, Mapping)
        and _has_tool_schema_key(value)
        and isinstance(tool_name := value.get("name"), str)
        and (error := _tool_shape_error(value, tool_name))
    ):
        raise Error(error)
    return None


def _validate_tools(value: list[Any], context: str) -> list[MCPTool]:
    tools: list[MCPTool] = []
    for item in value:
        if tool := _coerce_tool(item):
            tools.append(tool)
            continue
        msg = f"Invalid MCP tools document: {context} contains a non-tool item"
        raise Error(msg)
    return tools


def _collect_tools_from_servers(value: Any) -> list[MCPTool]:
    match value:
        case Mapping():
            servers = value.values()
        case list():
            servers = value
        case _:
            return []

    tools: list[MCPTool] = []
    for server in servers:
        if isinstance(server, Mapping) and isinstance(server_tools := server.get("tools"), list):
            tools.extend(_validate_tools(server_tools, "server tools"))
    return tools


def _collect_tools_from_definitions(value: Any) -> list[MCPTool]:
    if not isinstance(value, Mapping):
        return []
    return [tool for name, schema in value.items() if (tool := _coerce_tool(schema, str(name)))]


def _extract_tools(data: Any) -> list[MCPTool]:
    match data:
        case Mapping() if tool := _coerce_tool(data):
            tools = [tool]
        case list():
            tools = _validate_tools(data, "top-level list")
        case Mapping() if isinstance(tools := data.get("tools"), list):
            tools = _validate_tools(tools, "tools")
        case Mapping() if isinstance(result := data.get("result"), Mapping):
            tools = _extract_tools(result)
        case Mapping():
            for key in ("mcpServers", "servers"):
                if tools := _collect_tools_from_servers(data.get(key)):
                    break
            for key in DEFINITION_KEYS:
                if tools:
                    break
                tools = _collect_tools_from_definitions(data.get(key))
            if not tools:
                tools = _collect_tools_from_definitions(data)
        case _:
            tools = []
    return tools


def _unique_definition_name(name: str, used_names: set[str]) -> str:
    base_name = _to_definition_name(name)
    if base_name not in used_names:
        used_names.add(base_name)
        return base_name

    index = 2
    while (candidate := f"{base_name}{index}") in used_names:
        index += 1
    used_names.add(candidate)
    return candidate


def _to_definition_name(name: str) -> str:
    parts = [part for part in re.split(r"[^A-Za-z0-9]+", name) if part]
    candidate = "".join(f"{part[:1].upper()}{part[1:]}" for part in parts) or "Model"
    if not candidate[:1].isalpha():
        return f"Model{candidate}"
    return candidate


def _rewrite_local_definition_ref(ref: str, ref_map: Mapping[str, str]) -> str:
    for key in DEFINITION_KEYS:
        prefix = f"#/{key}/"
        if not ref.startswith(prefix):
            continue
        name, separator, suffix = ref[len(prefix) :].partition("/")
        rewritten_name = ref_map.get(name, name)
        return f"#/$defs/{rewritten_name}{separator}{suffix}"
    return ref


def _rewrite_schema_refs(value: Any, ref_map: Mapping[str, str], *, strip_root_definitions: bool = False) -> Any:
    match value:
        case Mapping():
            rewritten: dict[str, Any] = {}
            for key, item in value.items():
                if strip_root_definitions and key in DEFINITION_KEYS:
                    continue
                if key == "$ref" and isinstance(item, str):
                    rewritten[key] = _rewrite_local_definition_ref(item, ref_map)
                    continue
                rewritten[key] = _rewrite_schema_refs(item, ref_map)
            return rewritten
        case list():
            return [_rewrite_schema_refs(item, ref_map) for item in value]
    return value


def _normalize_schema(
    schema: Mapping[str, Any],
    definition_name: str,
    used_names: set[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    schema_copy = dict(deepcopy(schema))
    root_definitions = [
        definitions for key in DEFINITION_KEYS if isinstance(definitions := schema_copy.get(key), Mapping)
    ]
    ref_map: dict[str, str] = {}
    for definitions in root_definitions:
        for name in definitions:
            ref_map[str(name)] = _unique_definition_name(
                f"{definition_name} {_to_definition_name(str(name))}",
                used_names,
            )

    hoisted_definitions: dict[str, Any] = {}
    for definitions in root_definitions:
        for name, inner_schema in definitions.items():
            if not isinstance(inner_schema, Mapping):
                continue
            normalized, nested = _normalize_schema(inner_schema, ref_map[str(name)], used_names)
            hoisted_definitions.update(nested)
            hoisted_definitions[ref_map[str(name)]] = normalized

    normalized_schema = _rewrite_schema_refs(schema_copy, ref_map, strip_root_definitions=True)
    normalized_schema["title"] = definition_name
    return normalized_schema, hoisted_definitions


def _add_tool_schema_definition(
    definitions: dict[str, Any],
    used_names: set[str],
    tool: MCPTool,
    schema_key: SchemaKey,
    suffix: str,
) -> None:
    if schema_key == "outputSchema" and schema_key not in tool:
        return
    base_name = _to_definition_name(str(tool["name"]))
    definition_name = _unique_definition_name(f"{base_name} {suffix}", used_names)
    schema = tool["inputSchema"] if schema_key == "inputSchema" else tool["outputSchema"]
    normalized, hoisted_definitions = _normalize_schema(schema, definition_name, used_names)
    definitions.update(hoisted_definitions)
    definitions[definition_name] = normalized


def convert_mcp_tools_to_jsonschema(data: Any) -> dict[str, Any]:
    """Convert MCP tool definitions into a JSON Schema definitions document."""
    tools = _extract_tools(data)
    if not tools:
        msg = "Invalid MCP tools document: no tool definitions were found"
        raise Error(msg)

    definitions: dict[str, Any] = {}
    used_names: set[str] = set()
    for tool in tools:
        _add_tool_schema_definition(definitions, used_names, tool, "inputSchema", "Input")
        _add_tool_schema_definition(definitions, used_names, tool, "outputSchema", "Output")

    return {
        "$schema": JSON_SCHEMA_DRAFT_2020_12,
        "type": "object",
        "properties": {},
        "$defs": definitions,
    }
