"""Validate generated Pydantic v2 models with schema-derived payloads."""

from __future__ import annotations

import importlib.util
import json
import math
import re
import sys
import warnings
from collections import UserDict
from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from hypothesis_jsonschema import from_schema
from jsonschema import exceptions, validators
from pydantic import TypeAdapter

from datamodel_code_generator import load_yaml
from datamodel_code_generator.__main__ import Exit

from .conftest import CURRENT_PYTHON_VERSION, JSON_SCHEMA_DATA_PATH, OPEN_API_DATA_PATH, run_main_with_args

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


_PAYLOAD_CLASS_NAME = "Payload"
_MAX_EXAMPLES = 10
_EXCLUDED_FILES: dict[str, str] = {
    "jsonschema/allof_class_hierarchy.json": "intentionally invalid JSON fixture",
    "jsonschema/non_dict_files/list_only.json": "input is JSON data, not a JSON Schema document",
    "jsonschema/non_dict_files/list_only.yaml": "input is YAML data, not a JSON Schema document",
    "jsonschema/non_dict_files/whitespace_only.yaml": "empty YAML fixture",
    "jsonschema/non_json_object.json": "input is JSON data, not a JSON Schema document",
    "jsonschema/null.json": "intentionally invalid JSON fixture",
    "jsonschema/ref_to_json_list/list.json": "referenced JSON data list, not a schema document",
    "jsonschema/unknown_format.json": "unknown format fixture intentionally emits a generator warning",
    "openapi/complex_reference.json": "intentionally invalid JSON fixture",
    "openapi/list.json": "input is JSON data, not an OpenAPI document",
    "openapi/not.json": "intentionally invalid JSON fixture",
    "openapi/subclass_enum.json": "intentionally invalid JSON fixture",
}
_EXCLUDED_CASES: dict[str, str] = {
    "jsonschema/all_of_any_of_base_class_ref.json": "hypothesis-jsonschema cannot satisfy the allOf/anyOf constraints",
    "openapi/allof.yaml::components.schemas.AllOfNested3": (
        "hypothesis-jsonschema cannot satisfy the nested allOf component constraints"
    ),
    "openapi/allof_with_required_inherited_complex_allof.yaml::components.schemas.ProjectedItem": (
        "hypothesis-jsonschema generates this nested allOf schema inconsistently"
    ),
    "openapi/allof_with_required_inherited_comprehensive.yaml::components.schemas.Entity": (
        "hypothesis-jsonschema generates this inherited allOf schema inconsistently"
    ),
    "openapi/allof_with_required_inherited_comprehensive.yaml::components.schemas.ProjectedEntity": (
        "hypothesis-jsonschema generates this inherited allOf schema inconsistently"
    ),
    "openapi/allof_with_required_inherited_coverage.yaml::components.schemas.EdgeCasesCoverage": (
        "hypothesis-jsonschema generates this inherited allOf coverage schema inconsistently"
    ),
    "openapi/allof_with_required_inherited_edge_cases.yaml::components.schemas.EdgeCases": (
        "hypothesis-jsonschema generates this inherited allOf edge-case schema inconsistently"
    ),
    "openapi/allof_with_required_inherited_edge_cases.yaml::components.schemas.ProjectedEdgeCases": (
        "hypothesis-jsonschema generates this allOf edge-case schema inconsistently"
    ),
    "openapi/discriminator.yaml::components.schemas.Demo": (
        "discriminator branches overlap under JSON Schema validation; see payload_validation_future_work.md"
    ),
    "openapi/discriminator_float_mapping.yaml::components.schemas.Base": (
        "numeric discriminator mapping needs an explicit backend compatibility policy; "
        "see payload_validation_future_work.md"
    ),
    "openapi/discriminator_in_array_oneof.yaml::components.schemas.Demo": (
        "array item discriminator tags conflict with inherited JSON Schema constraints; "
        "see payload_validation_future_work.md"
    ),
    "openapi/discriminator_without_mapping.yaml::components.schemas.Demo": (
        "implicit discriminator tags conflict with source enum constraints; see payload_validation_future_work.md"
    ),
    "openapi/ref_nullable.yaml::components.schemas.NullableChild": (
        "top-level nullable object components need a wrapper policy; nullable refs are covered via Parent"
    ),
}


@dataclass(frozen=True)
class SchemaCase:
    """A schema candidate that should generate a model named Payload."""

    id: str
    input_file_type: str
    source_path: Path
    source_schema: dict[str, Any] = field(repr=False)
    codegen_schema: dict[str, Any] = field(repr=False)
    temp_input_suffix: str


class GeneratedModelCache(UserDict[str, Any]):
    """Cache wrapper with compact Hypothesis failure representation."""

    def __repr__(self) -> str:
        """Return a compact representation for Hypothesis failure output."""
        return "GeneratedModelCache(...)"


@pytest.fixture(scope="session")
def generated_model_cache(tmp_path_factory: pytest.TempPathFactory) -> GeneratedModelCache:
    """Cache generated Payload adapters across Hypothesis examples."""
    return GeneratedModelCache({"base": tmp_path_factory.mktemp("payload_validation"), "adapters": {}})


def _load_mapping(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    data = json.loads(text) if path.suffix == ".json" else load_yaml(text)
    if not isinstance(data, dict):
        msg = f"{path} did not contain an object"
        raise TypeError(msg)
    return data


def _is_openapi_document(data: dict[str, Any]) -> bool:
    return isinstance(data.get("openapi"), str) or isinstance(data.get("swagger"), str)


def _looks_like_json_schema(data: dict[str, Any]) -> bool:
    schema_keys = {
        "$defs",
        "$id",
        "$ref",
        "$schema",
        "additionalProperties",
        "allOf",
        "anyOf",
        "definitions",
        "enum",
        "items",
        "oneOf",
        "properties",
        "type",
    }
    return not _is_openapi_document(data) and bool(schema_keys & data.keys())


def _iter_schema_files(base_path: Path) -> Iterator[Path]:
    for path in sorted(base_path.rglob("*")):
        if path.suffix in {".json", ".yaml", ".yml"}:
            yield path


def _relative_case_path(path: Path) -> str:
    for base_name, base_path in (("jsonschema", JSON_SCHEMA_DATA_PATH), ("openapi", OPEN_API_DATA_PATH)):
        if path.is_relative_to(base_path):
            return f"{base_name}/{path.relative_to(base_path).as_posix()}"
    return path.as_posix()


def _has_external_ref(value: Any) -> bool:
    if isinstance(value, dict):
        ref = value.get("$ref")
        if isinstance(ref, str) and not ref.startswith("#/"):
            return True
        return any(_has_external_ref(child) for child in value.values())
    if isinstance(value, list):
        return any(_has_external_ref(child) for child in value)
    return False


def _has_unresolved_internal_ref(schema: dict[str, Any]) -> bool:
    for ref in _find_internal_refs(schema):
        current: Any = schema
        for raw_part in ref.removeprefix("#/").split("/"):
            part = raw_part.replace("~1", "/").replace("~0", "~")
            if not isinstance(current, dict) or part not in current:
                return True
            current = current[part]
    return False


def _has_unsupported_keyword(value: Any) -> bool:
    if isinstance(value, dict):
        if "$dynamicAnchor" in value or "$dynamicRef" in value:
            return True
        if any(key.startswith("x-python-") for key in value):
            return True
        if "customBasePath" in value or "customTypePath" in value or "patternProperties" in value:
            return True
        return any(_has_unsupported_keyword(child) for child in value.values())
    if isinstance(value, list):
        return any(_has_unsupported_keyword(child) for child in value)
    return False


def _has_dotted_definition_name(schema: dict[str, Any]) -> bool:
    for definitions_key in ("definitions", "$defs"):
        definitions = schema.get(definitions_key)
        if isinstance(definitions, dict) and any("." in key for key in definitions):
            return True
    return False


def _has_allof_property_override(value: Any) -> bool:
    if isinstance(value, dict):
        properties = value.get("properties")
        all_of = value.get("allOf")
        if isinstance(properties, dict) and isinstance(all_of, list):
            if properties:
                return True
            property_names = set(properties)
            for child in all_of:
                if (
                    isinstance(child, dict)
                    and isinstance(child.get("properties"), dict)
                    and property_names & set(child["properties"])
                ):
                    return True
        return any(_has_allof_property_override(child) for child in value.values())
    if isinstance(value, list):
        return any(_has_allof_property_override(child) for child in value)
    return False


def _find_internal_refs(value: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, dict):
        ref = value.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/"):
            refs.add(ref)
        for child in value.values():
            refs.update(_find_internal_refs(child))
    elif isinstance(value, list):
        for child in value:
            refs.update(_find_internal_refs(child))
    return refs


def _normalize_openapi_component_ref(ref: str) -> str:
    if ref.startswith("#/") or "/" in ref or "#" in ref:
        return ref
    return f"#/components/schemas/{ref}"


def _find_openapi_component_refs(value: Any) -> set[str]:
    refs = _find_internal_refs(value)
    if isinstance(value, dict):
        discriminator = value.get("discriminator")
        if isinstance(discriminator, dict):
            mapping = discriminator.get("mapping")
            if isinstance(mapping, dict):
                refs.update(
                    normalized_ref
                    for ref in mapping.values()
                    if isinstance(ref, str)
                    and (normalized_ref := _normalize_openapi_component_ref(ref)).startswith("#/")
                )
        for child in value.values():
            refs.update(_find_openapi_component_refs(child))
    elif isinstance(value, list):
        for child in value:
            refs.update(_find_openapi_component_refs(child))
    return refs


def _has_allof_ref(schema: dict[str, Any], ref: str) -> bool:
    all_of = schema.get("allOf")
    return isinstance(all_of, list) and any(isinstance(item, dict) and item.get("$ref") == ref for item in all_of)


def _has_recursive_definition_ref(schema: dict[str, Any]) -> bool:
    definitions: dict[str, Any] = {}
    for definitions_key in ("definitions", "$defs"):
        raw_definitions = schema.get(definitions_key)
        if isinstance(raw_definitions, dict):
            for name, definition in raw_definitions.items():
                if isinstance(definition, dict):
                    definitions[f"#/{definitions_key}/{name}"] = definition
    if not definitions:
        return False

    graph = {
        ref: {child_ref for child_ref in _find_internal_refs(definition) if child_ref in definitions}
        for ref, definition in definitions.items()
    }

    def visit(ref: str, stack: set[str]) -> bool:
        if ref in stack:
            return True
        return any(visit(child_ref, {*stack, ref}) for child_ref in graph[ref])

    return any(visit(ref, set()) for ref in graph)


def _has_recursive_component_ref(schema: dict[str, Any]) -> bool:
    components = schema.get("components")
    if not isinstance(components, dict):
        return False
    raw_schemas = components.get("schemas")
    if not isinstance(raw_schemas, dict):
        return False
    definitions = {
        f"#/components/schemas/{name}": component_schema
        for name, component_schema in raw_schemas.items()
        if isinstance(component_schema, dict)
    }
    graph = {
        ref: {child_ref for child_ref in _find_internal_refs(definition) if child_ref in definitions}
        for ref, definition in definitions.items()
    }

    def visit(ref: str, stack: set[str]) -> bool:
        if ref in stack:
            return True
        return any(visit(child_ref, {*stack, ref}) for child_ref in graph[ref])

    return any(visit(ref, set()) for ref in graph)


def _has_default_on_combined_schema(value: Any) -> bool:
    if isinstance(value, dict):
        if "default" in value and any(key in value for key in ("allOf", "anyOf", "oneOf")):
            return True
        return any(_has_default_on_combined_schema(child) for child in value.values())
    if isinstance(value, list):
        return any(_has_default_on_combined_schema(child) for child in value)
    return False


def _has_object_keywords_without_object_type(value: Any) -> bool:
    object_keywords = {
        "additionalProperties",
        "maxProperties",
        "minProperties",
        "properties",
        "propertyNames",
        "required",
        "unevaluatedProperties",
    }
    if isinstance(value, dict):
        if "type" not in value and bool(object_keywords & value.keys()):
            return True
        return any(_has_object_keywords_without_object_type(child) for child in value.values())
    if isinstance(value, list):
        return any(_has_object_keywords_without_object_type(child) for child in value)
    return False


def _has_array_keywords_without_array_type(value: Any) -> bool:
    array_keywords = {
        "additionalItems",
        "contains",
        "items",
        "maxContains",
        "maxItems",
        "minContains",
        "minItems",
        "prefixItems",
        "unevaluatedItems",
        "uniqueItems",
    }
    if isinstance(value, dict):
        if "type" not in value and bool(array_keywords & value.keys()):
            return True
        return any(_has_array_keywords_without_array_type(child) for child in value.values())
    if isinstance(value, list):
        return any(_has_array_keywords_without_array_type(child) for child in value)
    return False


def _has_unsatisfiable_contains_false(value: Any) -> bool:
    if isinstance(value, dict):
        min_contains = value.get("minContains", 1)
        if value.get("contains") is False and (not isinstance(min_contains, int) or min_contains > 0):
            return True
        return any(_has_unsatisfiable_contains_false(child) for child in value.values())
    if isinstance(value, list):
        return any(_has_unsatisfiable_contains_false(child) for child in value)
    return False


def _has_unsatisfiable_contains_bounds(value: Any) -> bool:
    if isinstance(value, dict):
        min_contains = value.get("minContains", 1)
        max_contains = value.get("maxContains")
        if (
            "contains" in value
            and isinstance(min_contains, int)
            and isinstance(max_contains, int)
            and max_contains < min_contains
        ):
            return True
        return any(_has_unsatisfiable_contains_bounds(child) for child in value.values())
    if isinstance(value, list):
        return any(_has_unsatisfiable_contains_bounds(child) for child in value)
    return False


def _has_unsatisfiable_property_count(value: Any) -> bool:
    if isinstance(value, dict):
        properties = value.get("properties")
        property_count = len(properties) if isinstance(properties, dict) else 0
        min_properties = value.get("minProperties")
        max_properties = value.get("maxProperties")
        if value.get("additionalProperties") is False:
            if isinstance(min_properties, int) and min_properties > property_count:
                return True
            if isinstance(max_properties, int) and max_properties < len(value.get("required", [])):
                return True
        return any(_has_unsatisfiable_property_count(child) for child in value.values())
    if isinstance(value, list):
        return any(_has_unsatisfiable_property_count(child) for child in value)
    return False


def _schema_exclusion_reason(schema: dict[str, Any], *, is_openapi: bool = False) -> str | None:  # noqa: PLR0911, PLR0912
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            validators.validator_for(schema).check_schema(schema)
    except exceptions.SchemaError:
        return "schema is invalid for its declared JSON Schema draft"
    if _has_external_ref(schema):
        return "contains external or non-fragment $ref values"
    if _has_unresolved_internal_ref(schema):
        return "contains unresolved internal $ref values"
    if _has_unsupported_keyword(schema):
        return "uses schema features requiring non-default generator configuration"
    if _has_dotted_definition_name(schema):
        return "dotted definition names require modular output"
    if _has_allof_property_override(schema):
        return "allOf property override emits duplicate-field warnings under warning-as-error tests"
    if _has_recursive_definition_ref(schema):
        return "hypothesis-jsonschema cannot resolve recursive definition references"
    if _has_recursive_component_ref(schema):
        return "hypothesis-jsonschema cannot resolve recursive OpenAPI component references"
    if _has_default_on_combined_schema(schema):
        return "combined schemas with defaults can validate generated defaults before payload input"
    if _has_unsatisfiable_contains_false(schema):
        return "contains false with minContains greater than zero has no valid array payloads"
    if _has_unsatisfiable_contains_bounds(schema):
        return "contains minContains/maxContains bounds have no valid array payloads"
    if _has_unsatisfiable_property_count(schema):
        return "object property count constraints have no valid payloads"
    if not is_openapi and _has_object_keywords_without_object_type(schema):
        return "JSON Schema object keywords without type object allow non-object payloads"
    if not is_openapi and _has_array_keywords_without_array_type(schema):
        return "JSON Schema array keywords without type array allow non-array payloads"
    return None


def _to_json_schema(value: Any) -> Any:  # noqa: PLR0912
    """Convert common OpenAPI schema extensions to JSON Schema-compatible shape."""
    if isinstance(value, dict):
        converted = {key: _to_json_schema(child) for key, child in value.items() if key != "nullable"}
        if "x-propertyNames" in converted and "propertyNames" not in converted:
            converted["propertyNames"] = converted["x-propertyNames"]
        discriminator = value.get("discriminator")
        if isinstance(discriminator, dict):
            property_name = discriminator.get("propertyName")
            mapping = discriminator.get("mapping")
            properties = converted.get("properties")
            if isinstance(property_name, str) and isinstance(mapping, dict) and isinstance(properties, dict):
                property_schema = properties.get(property_name)
                if isinstance(property_schema, dict) and property_schema.get("type") == "string":
                    property_schema.setdefault("enum", list(mapping))
        if (
            "type" not in converted
            and any(key in converted for key in ("properties", "required", "additionalProperties"))
            and not any(key in converted for key in ("allOf", "anyOf", "oneOf", "$ref"))
        ):
            converted["type"] = "object"
        if value.get("nullable") is True:
            schema_type = converted.get("type")
            if isinstance(schema_type, str):
                converted["type"] = [schema_type, "null"]
            elif isinstance(schema_type, list):
                converted["type"] = [*schema_type, "null"] if "null" not in schema_type else schema_type
            elif "oneOf" in converted:
                converted["oneOf"] = [*converted["oneOf"], {"type": "null"}]
            elif "anyOf" in converted:
                converted["anyOf"] = [*converted["anyOf"], {"type": "null"}]
            else:
                converted["anyOf"] = [{"type": "null"}, {}]
        return converted
    if isinstance(value, list):
        return [_to_json_schema(child) for child in value]
    return value


def _normalize_schema_dialect(schema: dict[str, Any]) -> dict[str, Any]:
    normalized = json.loads(json.dumps(schema))
    if normalized.get("$schema") == "http://json-schema.org/draft/2019-09/schema#":
        normalized["$schema"] = "https://json-schema.org/draft/2019-09/schema"
    elif normalized.get("$schema") == "http://json-schema.org/schema#":
        normalized["$schema"] = "http://json-schema.org/draft-07/schema#"
    return normalized


def _openapi_components(document: dict[str, Any]) -> dict[str, Any]:
    components = document.get("components")
    if not isinstance(components, dict):
        return {}
    schemas = components.get("schemas")
    return schemas if isinstance(schemas, dict) else {}


def _has_dotted_openapi_component_name(document: dict[str, Any]) -> bool:
    return any("." in name for name in _openapi_components(document))


def _iter_openapi_json_body_schemas(document: dict[str, Any]) -> Iterator[tuple[str, dict[str, Any]]]:
    paths = document.get("paths")
    if not isinstance(paths, dict):
        return
    for path_name, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.startswith("x-") or not isinstance(operation, dict):
                continue
            request_body = operation.get("requestBody")
            if isinstance(request_body, dict):
                yield from _iter_media_type_schemas(f"paths.{path_name}.{method}.requestBody", request_body)
            responses = operation.get("responses")
            if isinstance(responses, dict):
                for status_code, response in responses.items():
                    if isinstance(response, dict):
                        yield from _iter_media_type_schemas(
                            f"paths.{path_name}.{method}.responses.{status_code}",
                            response,
                        )


def _iter_media_type_schemas(prefix: str, container: dict[str, Any]) -> Iterator[tuple[str, dict[str, Any]]]:
    content = container.get("content")
    if not isinstance(content, dict):
        return
    for media_type, media_type_object in content.items():
        if media_type != "application/json" or not isinstance(media_type_object, dict):
            continue
        schema = media_type_object.get("schema")
        if isinstance(schema, dict):
            yield f"{prefix}.content.application/json", schema


def _make_jsonschema_case(path: Path, schema: dict[str, Any]) -> SchemaCase:
    case_id = _relative_case_path(path)
    normalized_schema = _normalize_schema_dialect(schema)
    return SchemaCase(
        id=case_id,
        input_file_type="jsonschema",
        source_path=path,
        source_schema=deepcopy(normalized_schema),
        codegen_schema=deepcopy(normalized_schema),
        temp_input_suffix=path.suffix,
    )


def _referenced_openapi_components(schema: dict[str, Any], components: dict[str, Any]) -> dict[str, Any]:
    referenced: dict[str, Any] = {}
    pending = [
        ref.removeprefix("#/components/schemas/")
        for ref in _find_openapi_component_refs(schema)
        if ref.startswith("#/components/schemas/")
    ]
    while pending:
        name = pending.pop()
        if name in referenced:
            continue
        component = components.get(name)
        if not isinstance(component, dict):
            continue
        referenced[name] = component
        if isinstance(component.get("discriminator"), dict):
            component_ref = f"#/components/schemas/{name}"
            pending.extend(
                component_name
                for component_name, component_schema in components.items()
                if isinstance(component_schema, dict) and _has_allof_ref(component_schema, component_ref)
            )
        pending.extend(
            ref.removeprefix("#/components/schemas/")
            for ref in _find_openapi_component_refs(component)
            if ref.startswith("#/components/schemas/")
        )
    return referenced


def _apply_discriminator_payload_constraints(json_schema: dict[str, Any], schema: dict[str, Any]) -> None:
    discriminator = schema.get("discriminator")
    if not isinstance(discriminator, dict):
        return
    property_name = discriminator.get("propertyName")
    if not isinstance(property_name, str):
        return
    components = json_schema.get("components")
    component_schemas = components.get("schemas") if isinstance(components, dict) else None
    if not isinstance(component_schemas, dict):
        return
    mapping = discriminator.get("mapping")
    mapped_tags = (
        {
            normalized_ref.removeprefix("#/components/schemas/"): tag
            for tag, ref in mapping.items()
            if isinstance(tag, str)
            and isinstance(ref, str)
            and (normalized_ref := _normalize_openapi_component_ref(ref)).startswith("#/components/schemas/")
        }
        if isinstance(mapping, dict)
        else {}
    )
    branch_refs = {
        item["$ref"].removeprefix("#/components/schemas/")
        for key in ("anyOf", "oneOf")
        for item in schema.get(key, [])
        if isinstance(item, dict)
        and isinstance(item.get("$ref"), str)
        and item["$ref"].startswith("#/components/schemas/")
    }
    branch_refs.update(mapped_tags)
    for component_name in branch_refs:
        component_schema = component_schemas.get(component_name)
        if not isinstance(component_schema, dict):
            continue
        properties = component_schema.get("properties")
        if not isinstance(properties, dict):
            continue
        property_schema = properties.get(property_name)
        if not isinstance(property_schema, dict):
            continue
        required = component_schema.setdefault("required", [])
        if isinstance(required, list) and property_name not in required:
            required.append(property_name)
        tag = mapped_tags.get(component_name, component_name)
        if property_schema.get("type") == "string" and not any(
            key in property_schema for key in ("$ref", "const", "enum")
        ):
            property_schema["enum"] = [tag]


def _set_discriminator_property_constraint(schema: dict[str, Any], property_name: str, tags: list[str]) -> None:
    if not tags:
        return
    schema.setdefault("type", "object")
    properties = schema.setdefault("properties", {})
    if not isinstance(properties, dict):
        return
    property_schema = properties.setdefault(property_name, {"type": "string"})
    if not isinstance(property_schema, dict):
        return
    required = schema.setdefault("required", [])
    if isinstance(required, list) and property_name not in required:
        required.append(property_name)
    if property_schema.get("type", "string") == "string" and "$ref" not in property_schema:
        property_schema["enum"] = tags


def _apply_component_discriminator_payload_constraints(json_schema: dict[str, Any]) -> None:
    components = json_schema.get("components")
    component_schemas = components.get("schemas") if isinstance(components, dict) else None
    if not isinstance(component_schemas, dict):
        return
    for base_name, base_schema in list(component_schemas.items()):
        if not isinstance(base_schema, dict):
            continue
        discriminator = base_schema.get("discriminator")
        if not isinstance(discriminator, dict):
            continue
        property_name = discriminator.get("propertyName")
        if not isinstance(property_name, str):
            continue
        mapping = discriminator.get("mapping")
        subtype_tags = (
            {
                normalized_ref.removeprefix("#/components/schemas/"): tag
                for tag, ref in mapping.items()
                if isinstance(tag, str)
                and isinstance(ref, str)
                and (normalized_ref := _normalize_openapi_component_ref(ref)).startswith("#/components/schemas/")
            }
            if isinstance(mapping, dict)
            else {}
        )
        if not subtype_tags:
            base_ref = f"#/components/schemas/{base_name}"
            subtype_tags = {
                component_name: component_name
                for component_name, component_schema in component_schemas.items()
                if component_name != base_name
                and isinstance(component_schema, dict)
                and _has_allof_ref(component_schema, base_ref)
            }
        _set_discriminator_property_constraint(base_schema, property_name, list(subtype_tags.values()))
        for component_name, tag in subtype_tags.items():
            component_schema = component_schemas.get(component_name)
            if isinstance(component_schema, dict):
                _set_discriminator_property_constraint(component_schema, property_name, [tag])


def _make_openapi_case(path: Path, document: dict[str, Any], candidate_name: str, schema: dict[str, Any]) -> SchemaCase:
    components = _openapi_components(document)
    referenced_components = _referenced_openapi_components(schema, components)
    json_schema = {
        **_to_json_schema(schema),
        "components": {"schemas": _to_json_schema(referenced_components)},
    }
    _apply_discriminator_payload_constraints(json_schema, schema)
    _apply_component_discriminator_payload_constraints(json_schema)
    codegen_schema = {
        "openapi": document.get("openapi", "3.0.0"),
        "info": (
            document.get("info") if isinstance(document.get("info"), dict) else {"title": "Payload", "version": "1"}
        ),
        "paths": {},
        "components": {
            "schemas": {
                _PAYLOAD_CLASS_NAME: schema,
                **referenced_components,
            }
        },
    }
    case_id = f"{_relative_case_path(path)}::{candidate_name}"
    return SchemaCase(
        id=case_id,
        input_file_type="openapi",
        source_path=path,
        source_schema=json_schema,
        codegen_schema=codegen_schema,
        temp_input_suffix=".yaml",
    )


def _iter_cases() -> Iterator[SchemaCase]:  # noqa: PLR0912
    for path in _iter_schema_files(JSON_SCHEMA_DATA_PATH):
        case_path = _relative_case_path(path)
        if case_path in _EXCLUDED_FILES:
            continue
        schema = _load_mapping(path)
        if _looks_like_json_schema(schema):
            if _schema_exclusion_reason(schema) is not None:
                continue
            case = _make_jsonschema_case(path, schema)
            if case.id not in _EXCLUDED_CASES:
                yield case
    for path in _iter_schema_files(OPEN_API_DATA_PATH):
        case_path = _relative_case_path(path)
        if case_path in _EXCLUDED_FILES:
            continue
        document = _load_mapping(path)
        if not _is_openapi_document(document):
            continue
        if _has_dotted_openapi_component_name(document):
            continue
        cases_for_file = 0
        for name, schema in _openapi_components(document).items():
            if isinstance(schema, dict) and _schema_exclusion_reason(schema, is_openapi=True) is None:
                case = _make_openapi_case(path, document, f"components.schemas.{name}", schema)
                if (
                    case.id not in _EXCLUDED_CASES
                    and _schema_exclusion_reason(case.source_schema, is_openapi=True) is None
                ):
                    cases_for_file += 1
                    yield case
        for name, schema in _iter_openapi_json_body_schemas(document):
            if _schema_exclusion_reason(schema, is_openapi=True) is None:
                case = _make_openapi_case(path, document, name, schema)
                if (
                    case.id not in _EXCLUDED_CASES
                    and _schema_exclusion_reason(case.source_schema, is_openapi=True) is None
                ):
                    cases_for_file += 1
                    yield case


def _discover_unaccounted_files(cases: list[SchemaCase]) -> list[str]:
    accounted = {_relative_case_path(case.source_path) for case in cases} | set(_EXCLUDED_FILES)
    excluded_case_files = {case_id.split("::", 1)[0] for case_id in _EXCLUDED_CASES}
    accounted.update(excluded_case_files)
    unaccounted: list[str] = []
    for base_path in (JSON_SCHEMA_DATA_PATH, OPEN_API_DATA_PATH):
        for path in _iter_schema_files(base_path):
            case_path = _relative_case_path(path)
            if case_path in accounted:
                continue
            data = _load_mapping(path)
            if base_path == JSON_SCHEMA_DATA_PATH and _looks_like_json_schema(data):
                if _schema_exclusion_reason(data) is not None:
                    continue
                unaccounted.append(case_path)
            if base_path == OPEN_API_DATA_PATH and _is_openapi_document(data):
                if _has_dotted_openapi_component_name(data):
                    continue
                schemas = [
                    schema
                    for name, schema in _openapi_components(data).items()
                    if isinstance(schema, dict)
                    and _schema_exclusion_reason(schema, is_openapi=True) is None
                    and _schema_exclusion_reason(
                        _make_openapi_case(path, data, f"components.schemas.{name}", schema).source_schema,
                        is_openapi=True,
                    )
                    is None
                ]
                schemas.extend(
                    schema
                    for name, schema in _iter_openapi_json_body_schemas(data)
                    if _schema_exclusion_reason(schema, is_openapi=True) is None
                    and _schema_exclusion_reason(
                        _make_openapi_case(path, data, name, schema).source_schema,
                        is_openapi=True,
                    )
                    is None
                )
                if schemas:
                    unaccounted.append(case_path)
    return unaccounted


SCHEMA_CASES = list(_iter_cases())


def test_payload_validation_cases_cover_discovered_schema_files() -> None:
    """Every discovered schema fixture must be validated or explicitly excluded."""
    unaccounted = _discover_unaccounted_files(SCHEMA_CASES)
    if unaccounted:
        pytest.fail(
            "Schema files must be covered by payload validation or added to _EXCLUDED_FILES with a reason:\n"
            + "\n".join(unaccounted)
        )


def _safe_filename(case_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", case_id)


def _write_input_schema(case: SchemaCase, directory: Path) -> Path:
    input_path = directory / f"input{case.temp_input_suffix}"
    if case.temp_input_suffix == ".json":
        input_path.write_text(json.dumps(case.codegen_schema), encoding="utf-8")
    else:
        import yaml

        input_path.write_text(yaml.safe_dump(case.codegen_schema, sort_keys=False), encoding="utf-8")
    return input_path


def _load_generated_payload_adapter(case: SchemaCase, generated_model_cache: dict[str, Any]) -> TypeAdapter[Any]:
    adapters: dict[str, TypeAdapter[Any]] = generated_model_cache["adapters"]
    if case.id in adapters:
        return adapters[case.id]

    case_dir = generated_model_cache["base"] / _safe_filename(case.id)
    case_dir.mkdir(exist_ok=True)
    input_path = _write_input_schema(case, case_dir)
    output_path = case_dir / "model.py"
    args = [
        "--input",
        str(input_path),
        "--input-file-type",
        case.input_file_type,
        "--output",
        str(output_path),
        "--output-model-type",
        "pydantic_v2.BaseModel",
        "--target-python-version",
        CURRENT_PYTHON_VERSION,
        "--class-name",
        _PAYLOAD_CLASS_NAME,
        "--disable-timestamp",
    ]
    if case.input_file_type == "openapi":
        args.extend(["--openapi-scopes", "schemas", "--strict-nullable"])
    run_main_with_args(
        args,
        expected_exit=Exit.OK,
    )
    module_name = f"payload_validation_{abs(hash(case.id))}"
    spec = importlib.util.spec_from_file_location(module_name, output_path)
    if spec is None or spec.loader is None:  # pragma: no cover
        pytest.fail(f"Unable to import generated module for {case.id}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    payload_type = getattr(module, _PAYLOAD_CLASS_NAME, None)
    if payload_type is None:
        generated_types = [
            value
            for value in module.__dict__.values()
            if isinstance(value, type) and getattr(value, "__module__", None) == module_name
        ]
        if len(generated_types) != 1:
            pytest.fail(f"Generated module for {case.id} did not contain {_PAYLOAD_CLASS_NAME}")
        payload_type = generated_types[0]
    adapter = TypeAdapter(payload_type)
    adapters[case.id] = adapter
    return adapter


def _validate_with_source_schema(case: SchemaCase, payload: Any) -> None:
    validator_class = validators.validator_for(case.source_schema)
    validator_class.check_schema(case.source_schema)
    validator_class(case.source_schema).validate(payload)


def _merge_simple_allof_for_payload_generation(schema: dict[str, Any]) -> dict[str, Any]:  # noqa: PLR0911, PLR0912
    all_of = schema.get("allOf")
    if not isinstance(all_of, list) or not all(isinstance(item, dict) for item in all_of):
        return schema

    ignored_keys = {"description", "title"}
    supported_keys = {
        "const",
        "enum",
        "exclusiveMaximum",
        "exclusiveMinimum",
        "format",
        "maximum",
        "maxItems",
        "maxLength",
        "minimum",
        "minItems",
        "minLength",
        "multipleOf",
        "type",
        "uniqueItems",
    }
    constraint_schemas = [{key: value for key, value in item.items() if key not in ignored_keys} for item in all_of]
    if any(set(item) - supported_keys for item in constraint_schemas):
        return schema
    if not any(constraint_schemas):
        return schema

    merged = {key: value for key, value in schema.items() if key != "allOf"}
    if set(merged) - ignored_keys:
        return schema
    merged = {key: value for key, value in merged.items() if key not in ignored_keys}

    for item in constraint_schemas:
        item_type = item.get("type")
        if item_type is not None:
            if "type" in merged and merged["type"] != item_type:
                return schema
            merged["type"] = item_type
        item_format = item.get("format")
        if item_format is not None:
            if "format" in merged and merged["format"] != item_format:
                return schema
            merged["format"] = item_format
        if "const" in item:
            if "const" in merged and merged["const"] != item["const"]:
                return schema
            merged["const"] = item["const"]
        if "enum" in item:
            item_enum = item["enum"]
            if not isinstance(item_enum, list):
                return schema
            if "enum" in merged:
                merged["enum"] = [value for value in merged["enum"] if value in item_enum]
            else:
                merged["enum"] = item_enum
            if not merged["enum"]:
                return schema
        multiple_of = item.get("multipleOf")
        if multiple_of is not None:
            if not isinstance(multiple_of, int) or multiple_of <= 0:
                return schema
            existing_multiple_of = merged.get("multipleOf")
            merged["multipleOf"] = (
                multiple_of if existing_multiple_of is None else math.lcm(existing_multiple_of, multiple_of)
            )
        for key in ("minimum", "exclusiveMinimum", "minItems", "minLength"):
            if key in item:
                merged[key] = item[key] if key not in merged else max(merged[key], item[key])
        for key in ("maximum", "exclusiveMaximum", "maxItems", "maxLength"):
            if key in item:
                merged[key] = item[key] if key not in merged else min(merged[key], item[key])
        if item.get("uniqueItems") is True:
            merged["uniqueItems"] = True

    return merged or schema


def _schema_for_payload_generation(value: Any) -> Any:  # noqa: PLR0912
    if isinstance(value, dict):
        schema = {key: _schema_for_payload_generation(child) for key, child in value.items()}
        schema = _merge_simple_allof_for_payload_generation(schema)
        if schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema":
            schema["$schema"] = "http://json-schema.org/draft-07/schema#"
        if isinstance(schema.get("prefixItems"), list):
            prefix_items = schema.pop("prefixItems")
            tail_items = schema.pop("items", None)
            schema["items"] = prefix_items
            if tail_items is not None:
                schema["additionalItems"] = tail_items
        if schema.get("contains") is False and schema.get("minContains") == 0:
            schema.pop("contains", None)
            schema.pop("minContains", None)
            schema.pop("maxContains", None)
        elif schema.get("contains") is True:
            min_contains = schema.pop("minContains", None)
            max_contains = schema.pop("maxContains", None)
            schema.pop("contains", None)
            if isinstance(min_contains, int):
                schema["minItems"] = max(schema.get("minItems", 0), min_contains)
            if isinstance(max_contains, int):
                schema["maxItems"] = min(schema.get("maxItems", max_contains), max_contains)
        if schema.get("type") == "string" and schema.get("format") == "byte":
            schema.setdefault("enum", ["", "MA==", "Zm9v"])
        if schema.get("type") == "string" and schema.get("format") == "duration":
            schema.setdefault("enum", ["P1D", "PT1S"])
        if schema.get("type") == "string" and schema.get("format") == "date-time-local":
            schema.setdefault("enum", ["2023-12-25T10:30:00"])
        if schema.get("type") == "string" and schema.get("format") == "uuid":
            schema.setdefault("enum", ["00000000-0000-4000-8000-000000000000"])
        if schema.get("type") == "string" and schema.get("format") == "ipv4":
            schema.setdefault("enum", ["127.0.0.1"])
        if schema.get("type") == "string" and schema.get("format") == "ipv6":
            schema.setdefault("enum", ["::1"])
        return schema
    if isinstance(value, list):
        return [_schema_for_payload_generation(child) for child in value]
    return value


def _payload_strategy(case: SchemaCase) -> st.SearchStrategy[Any]:
    validator_class = validators.validator_for(case.source_schema)
    validator_class.check_schema(case.source_schema)
    validator = validator_class(case.source_schema)
    return from_schema(_schema_for_payload_generation(deepcopy(case.source_schema))).filter(validator.is_valid)


@pytest.mark.parametrize("case", SCHEMA_CASES, ids=lambda case: case.id)
@settings(
    database=None,
    deadline=None,
    derandomize=True,
    max_examples=_MAX_EXAMPLES,
    suppress_health_check=[
        HealthCheck.filter_too_much,
        HealthCheck.function_scoped_fixture,
        HealthCheck.too_slow,
    ],
)
@given(data=st.data())
def test_generated_pydantic_v2_model_accepts_schema_derived_payloads(
    case: SchemaCase,
    generated_model_cache: dict[str, Any],
    data: st.DataObject,
) -> None:
    """Payloads accepted by the source schema should validate against generated code."""
    payload = data.draw(_payload_strategy(case), label=case.id)
    _validate_with_source_schema(case, payload)
    adapter = _load_generated_payload_adapter(case, generated_model_cache)
    adapter.validate_python(payload)
