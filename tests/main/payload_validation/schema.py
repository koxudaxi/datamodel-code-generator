"""Schema normalization helpers for payload validation tests."""

from __future__ import annotations

import json
import math
import warnings
from fractions import Fraction
from itertools import combinations
from typing import TYPE_CHECKING, Any

from jsonschema import exceptions, validators

from .constants import (
    ARRAY_SCHEMA_KEYWORDS,
    COMBINED_SCHEMA_KEYS,
    OBJECT_SCHEMA_KEYWORDS,
    PAYLOAD_FORMAT_ENUMS,
    SIMPLE_ALLOF_IGNORED_KEYS,
    SIMPLE_ALLOF_SUPPORTED_KEYS,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

MAX_EXACT_PROPERTY_NAME_DEPENDENCY_COUNT = 12


def _any_schema_node(value: Any, predicate: Callable[[dict[str, Any]], bool]) -> bool:
    result = False
    match value:
        case dict():
            result = predicate(value) or any(_any_schema_node(child, predicate) for child in value.values())
        case list():
            result = any(_any_schema_node(child, predicate) for child in value)
    return result


def _has_external_ref(value: Any) -> bool:
    def is_external_ref(schema: dict[str, Any]) -> bool:
        ref = schema.get("$ref")
        return isinstance(ref, str) and not ref.startswith("#/")

    return _any_schema_node(value, is_external_ref)


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
    def has_unsupported_keyword(schema: dict[str, Any]) -> bool:
        if "$dynamicAnchor" in schema or "$dynamicRef" in schema:
            return True
        if any(key.startswith("x-python-") for key in schema):
            return True
        return "customBasePath" in schema or "customTypePath" in schema or "patternProperties" in schema

    return _any_schema_node(value, has_unsupported_keyword)


def _has_dotted_definition_name(schema: dict[str, Any]) -> bool:
    for definitions_key in ("definitions", "$defs"):
        definitions = schema.get(definitions_key)
        if isinstance(definitions, dict) and any("." in key for key in definitions):
            return True
    return False


def _has_allof_property_override(value: Any) -> bool:
    def has_allof_property_override(schema: dict[str, Any]) -> bool:
        properties = schema.get("properties")
        all_of = schema.get("allOf")
        return isinstance(properties, dict) and bool(properties) and isinstance(all_of, list)

    return _any_schema_node(value, has_allof_property_override)


def _find_internal_refs(value: Any) -> set[str]:
    refs: set[str] = set()
    match value:
        case dict():
            if isinstance(ref := value.get("$ref"), str) and ref.startswith("#/"):
                refs.add(ref)
            for child in value.values():
                refs.update(_find_internal_refs(child))
        case list():
            for child in value:
                refs.update(_find_internal_refs(child))
    return refs


def _normalize_openapi_component_ref(ref: str) -> str:
    if ref.startswith("#/") or "/" in ref or "#" in ref:
        return ref
    return f"#/components/schemas/{ref}"


def _find_openapi_component_refs(value: Any) -> set[str]:
    refs = _find_internal_refs(value)
    match value:
        case {"discriminator": {"mapping": mapping}, **rest} if isinstance(mapping, dict):
            refs.update(
                normalized_ref
                for ref in mapping.values()
                if isinstance(ref, str) and (normalized_ref := _normalize_openapi_component_ref(ref)).startswith("#/")
            )
            for child in rest.values():
                refs.update(_find_openapi_component_refs(child))
        case dict():
            for child in value.values():
                refs.update(_find_openapi_component_refs(child))
        case list():
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
    return _any_schema_node(
        value,
        lambda schema: "default" in schema and any(key in schema for key in ("allOf", "anyOf", "oneOf")),
    )


def _has_object_keywords_without_object_type(value: Any) -> bool:
    return _any_schema_node(
        value,
        lambda schema: "type" not in schema and bool(OBJECT_SCHEMA_KEYWORDS & schema.keys()),
    )


def _has_array_keywords_without_array_type(value: Any) -> bool:
    return _any_schema_node(value, lambda schema: "type" not in schema and bool(ARRAY_SCHEMA_KEYWORDS & schema.keys()))


def _has_unsatisfiable_contains_false(value: Any) -> bool:
    def has_unsatisfiable_contains_false(schema: dict[str, Any]) -> bool:
        min_contains = schema.get("minContains", 1)
        return schema.get("contains") is False and (not isinstance(min_contains, int) or min_contains > 0)

    return _any_schema_node(value, has_unsatisfiable_contains_false)


def _has_unsatisfiable_contains_bounds(value: Any) -> bool:
    def has_unsatisfiable_contains_bounds(schema: dict[str, Any]) -> bool:
        min_contains = schema.get("minContains", 1)
        max_contains = schema.get("maxContains")
        return (
            "contains" in schema
            and isinstance(min_contains, int)
            and isinstance(max_contains, int)
            and max_contains < min_contains
        )

    return _any_schema_node(value, has_unsatisfiable_contains_bounds)


def _type_values(type_value: Any) -> set[str] | None:
    if type_value is None:
        return None
    if isinstance(type_value, str):
        return {type_value}
    if isinstance(type_value, list):
        return {value for value in type_value if isinstance(value, str)}
    return None


def _type_intersection(left: set[str], right: set[str]) -> set[str]:
    intersections: set[str] = set()
    for left_type in left:
        for right_type in right:
            if left_type == right_type:
                intersections.add(left_type)
            elif {left_type, right_type} == {"integer", "number"}:
                intersections.add("integer")
    return _simplify_types(intersections)


def _simplify_types(types: set[str]) -> set[str]:
    return types - {"integer"} if "number" in types else types


def _schema_implies_type_filter(schema: Any, filter_schema: Any) -> bool:
    if not isinstance(schema, dict) or not isinstance(filter_schema, dict):
        return False
    schema_types = _type_values(schema.get("type"))
    filter_types = _type_values(filter_schema.get("type"))
    return (
        schema_types is not None
        and filter_types is not None
        and _type_intersection(schema_types, filter_types) == _simplify_types(schema_types)
    )


def _has_unsatisfiable_closed_tuple_contains_max(value: Any) -> bool:
    def closed_tuple_items(schema: dict[str, Any]) -> list[Any] | None:
        prefix_items = schema.get("prefixItems")
        if isinstance(prefix_items, list):
            return prefix_items if schema.get("items") is False else None
        items = schema.get("items")
        return items if isinstance(items, list) and schema.get("additionalItems") is False else None

    def has_unsatisfiable_closed_tuple_contains_max(schema: dict[str, Any]) -> bool:
        if schema.get("type") != "array":
            return False
        contains = schema.get("contains")
        max_contains = schema.get("maxContains")
        min_items = schema.get("minItems")
        if not isinstance(contains, dict) or not isinstance(max_contains, int) or isinstance(max_contains, bool):
            return False
        if not isinstance(min_items, int) or isinstance(min_items, bool):
            return False
        tuple_items = closed_tuple_items(schema)
        if tuple_items is None:
            return False
        guaranteed_matches = sum(
            _schema_implies_type_filter(item, contains) for item in tuple_items[: min(min_items, len(tuple_items))]
        )
        return guaranteed_matches > max_contains

    return _any_schema_node(value, has_unsatisfiable_closed_tuple_contains_max)


def _fraction_value(value: Any) -> Fraction | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return Fraction(str(value))
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _effective_numeric_bound(
    schema: dict[str, Any], inclusive_key: str, exclusive_key: str, *, lower: bool
) -> (
    tuple[
        Fraction,
        bool,
    ]
    | None
):
    inclusive_value = _fraction_value(schema.get(inclusive_key))
    exclusive_value = _fraction_value(schema.get(exclusive_key))
    if inclusive_value is None:
        return (exclusive_value, True) if exclusive_value is not None else None
    if exclusive_value is None:
        return inclusive_value, False
    if inclusive_value == exclusive_value:
        return inclusive_value, True
    if lower:
        return (exclusive_value, True) if exclusive_value > inclusive_value else (inclusive_value, False)
    return (exclusive_value, True) if exclusive_value < inclusive_value else (inclusive_value, False)


def _has_unsatisfiable_numeric_multiple_bounds(value: Any) -> bool:
    def has_unsatisfiable_numeric_multiple_bounds(schema: dict[str, Any]) -> bool:
        multiple = _fraction_value(schema.get("multipleOf"))
        if multiple is None or multiple <= 0:
            return False
        type_values = _type_values(schema.get("type"))
        if type_values is None or not type_values <= {"integer", "number"}:
            return False
        lower_bound = _effective_numeric_bound(schema, "minimum", "exclusiveMinimum", lower=True)
        upper_bound = _effective_numeric_bound(schema, "maximum", "exclusiveMaximum", lower=False)
        if lower_bound is None or upper_bound is None:
            return False

        step = multiple if "number" in type_values else Fraction(abs(multiple.numerator), 1)
        lower_value, lower_exclusive = lower_bound
        upper_value, upper_exclusive = upper_bound

        min_factor = math.ceil(lower_value / step)
        if lower_exclusive and min_factor * step == lower_value:
            min_factor += 1

        max_factor = math.floor(upper_value / step)
        if upper_exclusive and max_factor * step == upper_value:
            max_factor -= 1

        return min_factor > max_factor

    return _any_schema_node(value, has_unsatisfiable_numeric_multiple_bounds)


def _literal_schema_values(schema: dict[str, Any]) -> Iterator[Any]:
    if "const" in schema:
        yield schema["const"]
        return
    enum_values = schema.get("enum")
    if isinstance(enum_values, list):
        yield from enum_values


def _json_value_matches_type(value: Any, type_value: Any) -> bool:
    types = _type_values(type_value)
    if types is None:
        return True

    matches = True
    if value is None:
        matches = "null" in types
    elif isinstance(value, bool):
        matches = "boolean" in types
    elif isinstance(value, int):
        matches = "integer" in types or "number" in types
    elif isinstance(value, float):
        matches = "number" in types
    elif isinstance(value, str):
        matches = "string" in types
    elif isinstance(value, list):
        matches = "array" in types
    elif isinstance(value, dict):
        matches = "object" in types
    return matches


def _json_literal_matches_schema(value: Any, schema: dict[str, Any]) -> bool:
    if not _json_value_matches_type(value, schema.get("type")):
        return False
    if "const" in schema and value != schema["const"]:
        return False
    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and value not in enum_values:
        return False
    if isinstance(value, str):
        min_length = schema.get("minLength")
        max_length = schema.get("maxLength")
        if isinstance(min_length, int) and len(value) < min_length:
            return False
        if isinstance(max_length, int) and len(value) > max_length:
            return False
    return True


def _has_unsatisfiable_anyof_literal_constraints(value: Any) -> bool:
    supported_keys = {
        "$comment",
        "$id",
        "$schema",
        "anyOf",
        "const",
        "description",
        "enum",
        "examples",
        "maxLength",
        "minLength",
        "title",
        "type",
    }

    def has_unsatisfiable_anyof_literal_constraints(schema: dict[str, Any]) -> bool:
        any_of = schema.get("anyOf")
        if not isinstance(any_of, list) or set(schema) - supported_keys:
            return False

        candidates: list[Any] = []
        for branch in any_of:
            if branch is False:
                continue
            if branch is True or not isinstance(branch, dict) or set(branch) - supported_keys:
                return False
            if "const" not in branch and not isinstance(branch.get("enum"), list):
                return False
            candidates.extend(
                candidate
                for candidate in _literal_schema_values(branch)
                if _json_literal_matches_schema(candidate, branch)
            )

        return bool(candidates) and not any(_json_literal_matches_schema(candidate, schema) for candidate in candidates)

    return _any_schema_node(value, has_unsatisfiable_anyof_literal_constraints)


def _subtract_not_type_values(type_values: set[str], not_type_values: set[str]) -> set[str] | None:
    filtered_types: set[str] = set()
    for type_value in type_values:
        if type_value == "integer":
            if "integer" not in not_type_values and "number" not in not_type_values:
                filtered_types.add(type_value)
        elif type_value == "number":
            if "number" in not_type_values:
                continue
            if "integer" in not_type_values:
                return None
            filtered_types.add(type_value)
        elif type_value not in not_type_values:
            filtered_types.add(type_value)
    return _simplify_types(filtered_types)


def _has_unsatisfiable_not_type_constraints(value: Any) -> bool:
    def has_unsatisfiable_not_type_constraints(schema: dict[str, Any]) -> bool:
        not_schema = schema.get("not")
        if not not_schema or not isinstance(not_schema, dict):
            return False
        type_values = _type_values(schema.get("type"))
        not_type_values = _type_values(not_schema.get("type"))
        if type_values is None or not_type_values is None:
            return False
        filtered_types = _subtract_not_type_values(type_values, not_type_values)
        return filtered_types == set()

    return _any_schema_node(value, has_unsatisfiable_not_type_constraints)


def _has_unsatisfiable_conditional_type_constraints(value: Any) -> bool:
    def has_unsatisfiable_conditional_type_constraints(schema: dict[str, Any]) -> bool:
        condition = schema.get("if")
        if not isinstance(condition, dict) or set(condition) - {"type"}:
            return False
        then_schema = schema.get("then", True)
        if then_schema is not False:
            return False
        type_values = _type_values(schema.get("type"))
        condition_types = _type_values(condition.get("type"))
        if type_values is None or condition_types is None:
            return False
        return _type_intersection(type_values, condition_types) == _simplify_types(type_values)

    return _any_schema_node(value, has_unsatisfiable_conditional_type_constraints)


def _has_unsatisfiable_conditional_required_constraints(value: Any) -> bool:
    def has_unsatisfiable_conditional_required_constraints(schema: dict[str, Any]) -> bool:
        condition = schema.get("if")
        if not isinstance(condition, dict) or set(condition) - {"required"}:
            return False
        then_schema = schema.get("then", True)
        if then_schema is not False:
            return False
        if _type_values(schema.get("type")) != {"object"}:
            return False
        return set(condition.get("required", [])) <= set(schema.get("required", []))

    return _any_schema_node(value, has_unsatisfiable_conditional_required_constraints)


def _has_unsatisfiable_array_length(value: Any) -> bool:
    def max_item_counts(schema: dict[str, Any]) -> list[int]:
        counts: list[int] = []
        prefix_items = schema.get("prefixItems")
        if isinstance(prefix_items, list):
            false_prefix_index = next((index for index, item in enumerate(prefix_items) if item is False), None)
            if false_prefix_index is not None:
                counts.append(false_prefix_index)

        items = schema.get("items")
        if items is False:
            counts.append(len(prefix_items) if isinstance(prefix_items, list) else 0)
        elif isinstance(items, list):
            false_item_index = next((index for index, item in enumerate(items) if item is False), None)
            if false_item_index is not None:
                counts.append(false_item_index)
            if schema.get("additionalItems") is False:
                counts.append(len(items))
        elif schema.get("unevaluatedItems") is False and items is None and "contains" not in schema:
            counts.append(len(prefix_items) if isinstance(prefix_items, list) else 0)

        contains = schema.get("contains")
        max_contains = schema.get("maxContains")
        if (contains is True or contains == {}) and isinstance(max_contains, int):
            counts.append(max_contains)
        return counts

    def has_unsatisfiable_array_length(schema: dict[str, Any]) -> bool:
        if schema.get("type") != "array":
            return False
        min_items = schema.get("minItems")
        contains = schema.get("contains")
        min_contains = schema.get("minContains", 1)
        if (contains is True or contains == {}) and isinstance(min_contains, int):
            min_items = max(min_items, min_contains) if isinstance(min_items, int) else min_contains
        counts = max_item_counts(schema)
        max_items = schema.get("maxItems")
        if isinstance(max_items, int):
            counts.append(max_items)
        return isinstance(min_items, int) and bool(counts) and min_items > min(counts)

    return _any_schema_node(value, has_unsatisfiable_array_length)


def _schema_accepts_every_property_name(schema: Any) -> bool:  # noqa: PLR0911
    if schema is True or schema == {}:
        return True
    if not isinstance(schema, dict):
        return False
    any_of = schema.get("anyOf")
    if isinstance(any_of, list) and not any(_schema_accepts_every_property_name(item) for item in any_of):
        return False
    all_of = schema.get("allOf")
    if isinstance(all_of, list) and not all(_schema_accepts_every_property_name(item) for item in all_of):
        return False
    one_of = schema.get("oneOf")
    if isinstance(one_of, list) and not _oneof_property_names_accepts_all_names(one_of):
        return False
    not_schema = schema.get("not")
    if not_schema is not None and not _property_names_forbids_all_names(not_schema):
        return False
    metadata_keys = {
        "$comment",
        "$id",
        "$schema",
        "description",
        "examples",
        "title",
    }
    supported_keys = metadata_keys | {"allOf", "anyOf", "minLength", "not", "oneOf", "type"}
    if not set(schema) <= supported_keys:
        return False
    type_values = _type_values(schema.get("type"))
    if type_values is not None and "string" not in type_values:
        return False
    min_length = schema.get("minLength")
    return not isinstance(min_length, int) or min_length <= 0


def _oneof_property_names_accepts_all_names(one_of: list[Any]) -> bool:
    return sum(_schema_accepts_every_property_name(item) for item in one_of) == 1 and all(
        _schema_accepts_every_property_name(item) or _property_names_forbids_all_names(item) for item in one_of
    )


def _property_names_forbids_all_names(property_names: Any) -> bool:  # noqa: PLR0911
    if property_names is False:
        return True
    if not isinstance(property_names, dict):
        return False
    any_of = property_names.get("anyOf")
    if isinstance(any_of, list) and all(_property_names_forbids_all_names(item) for item in any_of):
        return True
    all_of = property_names.get("allOf")
    if isinstance(all_of, list) and any(_property_names_forbids_all_names(item) for item in all_of):
        return True
    one_of = property_names.get("oneOf")
    if isinstance(one_of, list) and _oneof_property_names_forbids_all_names(one_of):
        return True
    if _schema_accepts_every_property_name(property_names.get("not")):
        return True
    type_values = _type_values(property_names.get("type"))
    if type_values is not None and "string" not in type_values:
        return True
    enum_values = property_names.get("enum")
    if isinstance(enum_values, list) and not any(isinstance(item, str) for item in enum_values):
        return True
    if "const" in property_names and not isinstance(property_names["const"], str):
        return True
    min_length = property_names.get("minLength")
    max_length = property_names.get("maxLength")
    return isinstance(min_length, int) and isinstance(max_length, int) and min_length > max_length


def _oneof_property_names_forbids_all_names(one_of: list[Any]) -> bool:
    return (
        all(_property_names_forbids_all_names(item) for item in one_of)
        or sum(_schema_accepts_every_property_name(item) for item in one_of) > 1
    )


def _property_name_accepts_name(property_names: Any, name: str) -> bool:
    return _property_name_acceptance(property_names, name) is not False


def _property_name_acceptance(property_names: Any, name: str) -> bool | None:  # noqa: PLR0911, PLR0912
    if property_names is None or property_names is True:
        return True
    if property_names is False:
        return False
    if not isinstance(property_names, dict):
        return None

    combined_result: bool | None = True
    any_of = property_names.get("anyOf")
    if isinstance(any_of, list):
        branch_results = [_property_name_acceptance(branch, name) for branch in any_of]
        if any(result is True for result in branch_results):
            combined_result = True
        elif all(result is False for result in branch_results):
            combined_result = False
        else:
            combined_result = None

    all_of = property_names.get("allOf")
    if isinstance(all_of, list):
        branch_results = [_property_name_acceptance(branch, name) for branch in all_of]
        if any(result is False for result in branch_results):
            combined_result = False
        elif any(result is None for result in branch_results):
            combined_result = None if combined_result is not False else False

    one_of = property_names.get("oneOf")
    if isinstance(one_of, list):
        branch_results = [_property_name_acceptance(branch, name) for branch in one_of]
        true_count = sum(result is True for result in branch_results)
        if true_count > 1:
            combined_result = False
        elif any(result is None for result in branch_results):
            combined_result = None if combined_result is not False else False
        else:
            combined_result = (true_count == 1) if combined_result is not False else False
    if combined_result is False:
        return False

    not_schema = property_names.get("not")
    if not_schema is not None:
        not_result = _property_name_acceptance(not_schema, name)
        if not_result is True:
            return False
        if not_result is None:
            combined_result = None

    type_values = _type_values(property_names.get("type"))
    if type_values is not None and "string" not in type_values:
        return False
    enum_values = property_names.get("enum")
    if isinstance(enum_values, list) and name not in enum_values:
        return False
    if "const" in property_names and property_names["const"] != name:
        return False
    min_length = property_names.get("minLength")
    max_length = property_names.get("maxLength")
    if (isinstance(min_length, int) and len(name) < min_length) or (
        isinstance(max_length, int) and len(name) > max_length
    ):
        return False
    return combined_result


def _finite_property_name_values(property_names: Any) -> set[str] | None:
    if not isinstance(property_names, dict):
        return None
    combined_values = _finite_combined_property_name_values(property_names)
    if combined_values is not None:
        return combined_values
    enum_values = property_names.get("enum")
    if isinstance(enum_values, list):
        return {
            name for name in enum_values if isinstance(name, str) and _property_name_accepts_name(property_names, name)
        }
    if "const" not in property_names:
        return None
    const_value = property_names["const"]
    return (
        {const_value}
        if isinstance(const_value, str) and _property_name_accepts_name(property_names, const_value)
        else set()
    )


def _finite_combined_property_name_values(property_names: dict[str, Any]) -> set[str] | None:  # noqa: PLR0911
    any_of = property_names.get("anyOf")
    one_of = property_names.get("oneOf")
    all_of = property_names.get("allOf")

    combined_key_count = sum(isinstance(value, list) for value in (any_of, one_of, all_of))
    if combined_key_count != 1:
        return None

    if isinstance(any_of, list):
        branch_values = [_finite_property_name_branch_values(branch) for branch in any_of]
        if any(values is None for values in branch_values):
            return None
        return {
            name
            for values in branch_values
            for name in values or set()
            if _property_name_accepts_name(property_names, name)
        }

    if isinstance(one_of, list):
        branch_values = [_finite_property_name_branch_values(branch) for branch in one_of]
        if any(values is None for values in branch_values):
            return None
        return {
            name
            for values in branch_values
            for name in values or set()
            if _property_name_accepts_name(property_names, name)
        }

    if isinstance(all_of, list):
        branch_values = [_finite_property_name_branch_values(branch) for branch in all_of]
        finite_values = [values for values in branch_values if values is not None]
        if not finite_values:
            return None
        candidate_names = set.intersection(*finite_values) if len(finite_values) > 1 else set(finite_values[0])
        return {name for name in candidate_names if _property_name_accepts_name(property_names, name)}

    return None


def _finite_property_name_branch_values(property_names: Any) -> set[str] | None:
    if property_names is False:
        return set()
    return _finite_property_name_values(property_names)


def _iter_allof_object_schemas(schema: dict[str, Any]) -> Iterator[dict[str, Any]]:
    yield schema
    all_of = schema.get("allOf")
    if not isinstance(all_of, list):
        return
    for item in all_of:
        if isinstance(item, dict):
            yield from _iter_allof_object_schemas(item)


def _finite_allof_property_name_values(schema: dict[str, Any]) -> set[str] | None:
    object_schemas = list(_iter_allof_object_schemas(schema))
    finite_values = [
        values
        for item in object_schemas
        if (values := _finite_property_name_values(item.get("propertyNames"))) is not None
    ]
    if not finite_values:
        return None
    candidate_names = set.intersection(*finite_values) if len(finite_values) > 1 else set(finite_values[0])
    return {
        name
        for name in candidate_names
        if all(_property_name_accepts_name(item.get("propertyNames"), name) for item in object_schemas)
    }


def _dependency_required_names(dependency: Any) -> list[str]:
    if isinstance(dependency, list):
        return [name for name in dependency if isinstance(name, str)]
    if not isinstance(dependency, dict):
        return []
    required = dependency.get("required")
    return [name for name in required if isinstance(name, str)] if isinstance(required, list) else []


def _iter_dependencies(schema: dict[str, Any]) -> Iterator[tuple[str, Any]]:
    for key in ("dependentRequired", "dependentSchemas", "dependencies"):
        dependencies = schema.get(key)
        if isinstance(dependencies, dict):
            yield from (
                (dependency_name, dependency)
                for dependency_name, dependency in dependencies.items()
                if isinstance(dependency_name, str)
            )


def _dependency_allowed_property_name_values(dependency: dict[str, Any], allowed_names: set[str]) -> set[str]:
    dependency_properties = dependency.get("properties")
    declared_names = set(dependency_properties) if isinstance(dependency_properties, dict) else set()
    additional_properties = dependency.get("additionalProperties")

    return {
        name
        for name in allowed_names
        if _property_name_accepts_name(dependency.get("propertyNames"), name)
        and not (isinstance(dependency_properties, dict) and dependency_properties.get(name) is False)
        and (additional_properties is not False or name in declared_names)
    }


def _dependency_excludes_property_name(dependency: Any, name: str, allowed_names: set[str]) -> bool:  # noqa: PLR0911
    if dependency is False:
        return True
    if isinstance(dependency, dict):
        dependency_types = _type_values(dependency.get("type"))
        if dependency_types is not None and "object" not in dependency_types:
            return True
        if not _property_name_accepts_name(dependency.get("propertyNames"), name):
            return True
        dependency_properties = dependency.get("properties")
        if isinstance(dependency_properties, dict) and dependency_properties.get(name) is False:
            return True
        if dependency.get("additionalProperties") is False:
            declared_names = set(dependency_properties) if isinstance(dependency_properties, dict) else set()
            if name not in declared_names:
                return True
        min_properties = dependency.get("minProperties")
        if isinstance(min_properties, int) and not isinstance(min_properties, bool):
            dependency_allowed_names = _dependency_allowed_property_name_values(dependency, allowed_names)
            if min_properties > len(dependency_allowed_names):
                return True
        max_properties = dependency.get("maxProperties")
        if isinstance(max_properties, int) and not isinstance(max_properties, bool) and max_properties < 1:
            return True
    return any(required_name not in allowed_names for required_name in _dependency_required_names(dependency))


def _dependency_pruned_property_name_values(schema: dict[str, Any], property_name_values: set[str]) -> set[str]:
    dependencies = [
        dependency for item in _iter_allof_object_schemas(schema) for dependency in _iter_dependencies(item)
    ]
    remaining_names = set(property_name_values)
    while True:
        removed_names = {
            name
            for name in remaining_names
            if any(
                _dependency_excludes_property_name(dependency, name, remaining_names)
                for dependency_name, dependency in dependencies
                if dependency_name == name
            )
        }
        if not removed_names:
            return remaining_names
        remaining_names -= removed_names


def _dependency_accepts_property_count(dependency: Any, property_count: int) -> bool:
    if not isinstance(dependency, dict):
        return True
    max_properties = dependency.get("maxProperties")
    return not isinstance(max_properties, int) or isinstance(max_properties, bool) or property_count <= max_properties


def _property_name_set_satisfies_dependencies(
    selected_names: set[str],
    dependencies: list[tuple[str, Any]],
) -> bool:
    return all(
        not _dependency_excludes_property_name(dependency, name, selected_names)
        and _dependency_accepts_property_count(dependency, len(selected_names))
        and (not isinstance(dependency, dict) or _property_name_set_satisfies_object_schema(selected_names, dependency))
        for name in selected_names
        for dependency_name, dependency in dependencies
        if dependency_name == name
    )


def _property_name_set_conditional_result(selected_names: set[str], condition_schema: Any) -> bool | None:
    if condition_schema is True or condition_schema == {}:
        return True
    if condition_schema is False:
        return False
    if not isinstance(condition_schema, dict):
        return None
    if not _property_name_set_schema_is_key_only(condition_schema):
        return None
    return _property_name_set_satisfies_object_schema(selected_names, condition_schema)


def _property_name_set_accepts_name(schema: dict[str, Any], name: str) -> bool:
    if not _property_name_accepts_name(schema.get("propertyNames"), name):
        return False
    properties = schema.get("properties")
    if isinstance(properties, dict) and properties.get(name) is False:
        return False
    if schema.get("additionalProperties") is not False:
        return True
    declared_names = set(properties) if isinstance(properties, dict) else set()
    return name in declared_names


def _property_name_set_satisfies_object_schema(selected_names: set[str], schema: Any) -> bool:  # noqa: PLR0911
    if schema is True or schema == {}:
        return True
    if schema is False:
        return False
    if not isinstance(schema, dict):
        return True
    schema_types = _type_values(schema.get("type"))
    if schema_types is not None and "object" not in schema_types:
        return False
    min_properties = schema.get("minProperties")
    if (
        isinstance(min_properties, int)
        and not isinstance(min_properties, bool)
        and len(selected_names) < min_properties
    ):
        return False
    max_properties = schema.get("maxProperties")
    if (
        isinstance(max_properties, int)
        and not isinstance(max_properties, bool)
        and len(selected_names) > max_properties
    ):
        return False
    if not set(schema.get("required", [])) <= selected_names:
        return False
    if not all(_property_name_set_accepts_name(schema, name) for name in selected_names):
        return False
    all_of = schema.get("allOf")
    if isinstance(all_of, list) and not all(
        _property_name_set_satisfies_object_schema(selected_names, item) for item in all_of
    ):
        return False
    not_schema = schema.get("not")
    if not_schema is not None and not _property_name_set_satisfies_not_schemas(selected_names, [not_schema]):
        return False
    any_of = schema.get("anyOf")
    if isinstance(any_of, list) and not _property_name_set_satisfies_anyof_schema(selected_names, any_of):
        return False
    one_of = schema.get("oneOf")
    if isinstance(one_of, list) and not _property_name_set_satisfies_oneof_schema(selected_names, one_of):
        return False
    return _property_name_set_satisfies_conditionals(
        selected_names,
        [(schema.get("if"), schema.get("then", True), schema.get("else", True))] if "if" in schema else [],
    )


def _property_name_set_satisfies_conditionals(
    selected_names: set[str],
    conditionals: list[tuple[Any, Any, Any]],
) -> bool:
    for condition_schema, then_schema, else_schema in conditionals:
        condition_result = _property_name_set_conditional_result(selected_names, condition_schema)
        if condition_result is None:
            continue
        active_schema = then_schema if condition_result else else_schema
        if not _property_name_set_satisfies_object_schema(selected_names, active_schema):
            return False
    return True


def _property_name_set_schema_is_key_only(schema: dict[str, Any]) -> bool:
    metadata_keys = {
        "$comment",
        "$id",
        "$schema",
        "description",
        "examples",
        "title",
    }
    key_only_keys = {
        "additionalProperties",
        "allOf",
        "anyOf",
        "else",
        "if",
        "maxProperties",
        "minProperties",
        "not",
        "oneOf",
        "propertyNames",
        "required",
        "then",
        "type",
    }
    if not set(schema) <= metadata_keys | key_only_keys:
        return False
    all_of = schema.get("allOf")
    if isinstance(all_of, list) and not all(_property_name_set_subschema_is_key_only(item) for item in all_of):
        return False
    any_of = schema.get("anyOf")
    if isinstance(any_of, list) and not all(_property_name_set_subschema_is_key_only(item) for item in any_of):
        return False
    one_of = schema.get("oneOf")
    if isinstance(one_of, list) and not all(_property_name_set_subschema_is_key_only(item) for item in one_of):
        return False
    return (
        _property_name_set_subschema_is_key_only(schema.get("not", True))
        and _property_name_set_subschema_is_key_only(schema.get("if", True))
        and _property_name_set_subschema_is_key_only(schema.get("then", True))
        and _property_name_set_subschema_is_key_only(schema.get("else", True))
    )


def _property_name_set_subschema_is_key_only(schema: Any) -> bool:
    return (
        schema is True
        or schema is False
        or (isinstance(schema, dict) and _property_name_set_schema_is_key_only(schema))
    )


def _property_name_set_satisfies_not_schemas(selected_names: set[str], not_schemas: list[Any]) -> bool:
    for not_schema in not_schemas:
        if not_schema is False:
            continue
        if not_schema is True or not_schema == {}:
            return False
        if not isinstance(not_schema, dict):
            continue
        if _property_name_set_schema_is_key_only(not_schema) and _property_name_set_satisfies_object_schema(
            selected_names,
            not_schema,
        ):
            return False
    return True


def _property_name_set_satisfies_anyof_schema(selected_names: set[str], any_of: list[Any]) -> bool:
    known_branch_results: list[bool] = []
    for branch in any_of:
        if branch is True or branch == {}:
            return True
        if branch is False:
            known_branch_results.append(False)
            continue
        if not isinstance(branch, dict) or not _property_name_set_schema_is_key_only(branch):
            return True
        known_branch_results.append(_property_name_set_satisfies_object_schema(selected_names, branch))
    return any(known_branch_results)


def _property_name_set_satisfies_anyof_schemas(
    selected_names: set[str],
    anyof_schemas: list[list[Any]],
) -> bool:
    return all(_property_name_set_satisfies_anyof_schema(selected_names, any_of) for any_of in anyof_schemas)


def _property_name_set_satisfies_oneof_schema(selected_names: set[str], one_of: list[Any]) -> bool:
    known_branch_results: list[bool] = []
    for branch in one_of:
        if branch is True or branch == {}:
            known_branch_results.append(True)
            continue
        if branch is False:
            known_branch_results.append(False)
            continue
        if not isinstance(branch, dict) or not _property_name_set_schema_is_key_only(branch):
            return True
        known_branch_results.append(_property_name_set_satisfies_object_schema(selected_names, branch))
    return sum(known_branch_results) == 1


def _property_name_set_satisfies_oneof_schemas(
    selected_names: set[str],
    oneof_schemas: list[list[Any]],
) -> bool:
    return all(_property_name_set_satisfies_oneof_schema(selected_names, one_of) for one_of in oneof_schemas)


def _max_dependency_satisfiable_property_count(
    schema: dict[str, Any],
    property_name_values: set[str],
) -> int | None:
    if len(property_name_values) > MAX_EXACT_PROPERTY_NAME_DEPENDENCY_COUNT:
        return None

    names = sorted(property_name_values)
    dependencies = [
        dependency for item in _iter_allof_object_schemas(schema) for dependency in _iter_dependencies(item)
    ]
    conditionals = [
        (item.get("if"), item.get("then", True), item.get("else", True))
        for item in _iter_allof_object_schemas(schema)
        if "if" in item
    ]
    not_schemas = [item["not"] for item in _iter_allof_object_schemas(schema) if "not" in item]
    anyof_schemas = [
        item["anyOf"] for item in _iter_allof_object_schemas(schema) if isinstance(item.get("anyOf"), list)
    ]
    oneof_schemas = [
        item["oneOf"] for item in _iter_allof_object_schemas(schema) if isinstance(item.get("oneOf"), list)
    ]
    for count in range(len(names), -1, -1):
        if any(
            _property_name_set_satisfies_dependencies(set(candidate_names), dependencies)
            and _property_name_set_satisfies_conditionals(set(candidate_names), conditionals)
            and _property_name_set_satisfies_not_schemas(set(candidate_names), not_schemas)
            and _property_name_set_satisfies_anyof_schemas(set(candidate_names), anyof_schemas)
            and _property_name_set_satisfies_oneof_schemas(set(candidate_names), oneof_schemas)
            for candidate_names in combinations(names, count)
        ):
            return count
    return 0


def _has_unsatisfiable_property_count(value: Any) -> bool:
    def has_unsatisfiable_property_count(schema: dict[str, Any]) -> bool:
        properties = schema.get("properties")
        property_count = len(properties) if isinstance(properties, dict) else 0
        min_properties = schema.get("minProperties")
        max_properties = schema.get("maxProperties")
        object_schemas = list(_iter_allof_object_schemas(schema))
        if any(_property_names_forbids_all_names(item.get("propertyNames")) for item in object_schemas):
            return isinstance(min_properties, int) and min_properties > 0
        property_name_values = _finite_allof_property_name_values(schema)
        if property_name_values is not None:
            property_name_values = _dependency_pruned_property_name_values(schema, property_name_values)
            max_possible_properties = _max_dependency_satisfiable_property_count(schema, property_name_values)
            if max_possible_properties is None:
                max_possible_properties = len(property_name_values)
            if isinstance(min_properties, int) and min_properties > max_possible_properties:
                return True
        if schema.get("additionalProperties") is False:
            if isinstance(min_properties, int) and min_properties > property_count:
                return True
            if isinstance(max_properties, int) and max_properties < len(schema.get("required", [])):
                return True
        return False

    return _any_schema_node(value, has_unsatisfiable_property_count)


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
    if _has_unsatisfiable_closed_tuple_contains_max(schema):
        return "closed tuple contains maxContains bounds have no valid array payloads"
    if _has_unsatisfiable_numeric_multiple_bounds(schema):
        return "numeric multipleOf bounds have no valid payloads"
    if _has_unsatisfiable_anyof_literal_constraints(schema):
        return "anyOf literal constraints have no valid payloads"
    if _has_unsatisfiable_not_type_constraints(schema):
        return "not type constraints have no valid payloads"
    if _has_unsatisfiable_conditional_type_constraints(schema):
        return "conditional type constraints have no valid payloads"
    if _has_unsatisfiable_conditional_required_constraints(schema):
        return "conditional required constraints have no valid payloads"
    if _has_unsatisfiable_array_length(schema):
        return "array length constraints have no valid payloads"
    if _has_unsatisfiable_property_count(schema):
        return "object property count constraints have no valid payloads"
    if not is_openapi and _has_object_keywords_without_object_type(schema):
        return "JSON Schema object keywords without type object allow non-object payloads"
    if not is_openapi and _has_array_keywords_without_array_type(schema):
        return "JSON Schema array keywords without type array allow non-array payloads"
    return None


def _apply_nullable(schema: dict[str, Any]) -> None:
    match schema.get("type"):
        case str(schema_type):
            schema["type"] = [schema_type, "null"]
        case list(schema_types):
            schema["type"] = [*schema_types, "null"] if "null" not in schema_types else schema_types
        case _ if "oneOf" in schema:
            schema["oneOf"] = [*schema["oneOf"], {"type": "null"}]
        case _ if "anyOf" in schema:
            schema["anyOf"] = [*schema["anyOf"], {"type": "null"}]
        case _:
            schema["anyOf"] = [{"type": "null"}, {}]


def _set_default_openapi_object_type(schema: dict[str, Any]) -> None:
    if (
        "type" not in schema
        and any(key in schema for key in ("properties", "required", "additionalProperties"))
        and not any(key in schema for key in (*COMBINED_SCHEMA_KEYS, "$ref"))
    ):
        schema["type"] = "object"


def _set_discriminator_mapping_enum(schema: dict[str, Any], source_schema: dict[str, Any]) -> None:
    discriminator = source_schema.get("discriminator")
    if not isinstance(discriminator, dict) or not isinstance(discriminator.get("mapping"), dict):
        return
    property_name = discriminator.get("propertyName")
    properties = schema.get("properties")
    if not isinstance(property_name, str) or not isinstance(properties, dict):
        return
    property_schema = properties.get(property_name)
    if isinstance(property_schema, dict) and property_schema.get("type") == "string":
        property_schema.setdefault("enum", list(discriminator["mapping"]))
    return


def _to_json_schema(value: Any) -> Any:
    """Convert common OpenAPI schema extensions to JSON Schema-compatible shape."""
    converted_value = value
    match value:
        case dict():
            converted = {key: _to_json_schema(child) for key, child in value.items() if key != "nullable"}
            if (property_names := converted.get("x-propertyNames")) is not None:
                converted.setdefault("propertyNames", property_names)
            _set_discriminator_mapping_enum(converted, value)
            _set_default_openapi_object_type(converted)
            if value.get("nullable") is True:
                _apply_nullable(converted)
            converted_value = converted
        case list():
            converted_value = [_to_json_schema(child) for child in value]
    return converted_value


def _normalize_schema_dialect(schema: dict[str, Any]) -> dict[str, Any]:
    normalized = json.loads(json.dumps(schema))
    if normalized.get("$schema") == "http://json-schema.org/draft/2019-09/schema#":
        normalized["$schema"] = "https://json-schema.org/draft/2019-09/schema"
    elif normalized.get("$schema") == "http://json-schema.org/schema#":
        normalized["$schema"] = "http://json-schema.org/draft-07/schema#"
    return normalized


def _openapi_components(document: dict[str, Any]) -> dict[str, Any]:
    if isinstance(components := document.get("components"), dict) and isinstance(
        schemas := components.get("schemas"),
        dict,
    ):
        return schemas
    return {}


def _has_dotted_openapi_component_name(document: dict[str, Any]) -> bool:
    return any("." in name for name in _openapi_components(document))


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


def _openapi_component_mapping_tags(mapping: Any) -> dict[str, str]:
    if not isinstance(mapping, dict):
        return {}
    return {
        normalized_ref.removeprefix("#/components/schemas/"): tag
        for tag, ref in mapping.items()
        if isinstance(tag, str)
        and isinstance(ref, str)
        and (normalized_ref := _normalize_openapi_component_ref(ref)).startswith("#/components/schemas/")
    }


def _iter_branch_component_refs(schema: dict[str, Any], *keys: str) -> Iterator[str]:
    for key in keys:
        for item in schema.get(key, []):
            if (
                isinstance(item, dict)
                and isinstance(ref := item.get("$ref"), str)
                and ref.startswith("#/components/schemas/")
            ):
                yield ref.removeprefix("#/components/schemas/")


def _apply_discriminator_payload_constraints(json_schema: dict[str, Any], schema: dict[str, Any]) -> None:
    discriminator = schema.get("discriminator")
    if not isinstance(discriminator, dict):
        return
    property_name = discriminator.get("propertyName")
    if not isinstance(property_name, str):
        return
    component_schemas = _openapi_components(json_schema)
    if not component_schemas:
        return
    mapped_tags = _openapi_component_mapping_tags(discriminator.get("mapping"))
    branch_refs = set(_iter_branch_component_refs(schema, "anyOf", "oneOf"))
    branch_refs.update(mapped_tags)
    for component_name in branch_refs:
        if not isinstance(component_schema := component_schemas.get(component_name), dict):
            continue
        properties = component_schema.get("properties")
        if not isinstance(properties, dict) or not isinstance(property_schema := properties.get(property_name), dict):
            continue
        _add_required_property(component_schema, property_name)
        tag = mapped_tags.get(component_name, component_name)
        if property_schema.get("type") == "string" and not any(
            key in property_schema for key in ("$ref", "const", "enum")
        ):
            property_schema["enum"] = [tag]
    return


def _add_required_property(schema: dict[str, Any], property_name: str) -> None:
    required = schema.setdefault("required", [])
    if isinstance(required, list) and property_name not in required:
        required.append(property_name)


def _require_discriminator_property(schema: dict[str, Any], property_name: str) -> dict[str, Any] | None:
    schema.setdefault("type", "object")
    properties = schema.setdefault("properties", {})
    if not isinstance(properties, dict):
        return None
    property_schema = properties.setdefault(property_name, {"type": "string"})
    if not isinstance(property_schema, dict):
        return None
    _add_required_property(schema, property_name)
    return property_schema


def _set_discriminator_property_constraint(schema: dict[str, Any], property_name: str, tags: list[str]) -> None:
    if not tags:
        return
    property_schema = _require_discriminator_property(schema, property_name)
    if property_schema is None:
        return
    if property_schema.get("type", "string") == "string" and "$ref" not in property_schema:
        property_schema["enum"] = tags
    return


def _apply_component_discriminator_payload_constraints(json_schema: dict[str, Any]) -> None:
    component_schemas = _openapi_components(json_schema)
    if not component_schemas:
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
        subtype_tags = _openapi_component_mapping_tags(discriminator.get("mapping"))
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
    return


def _merge_equal_constraint(merged: dict[str, Any], schema: dict[str, Any], key: str) -> bool:
    if key not in schema:
        return True
    if key in merged and merged[key] != schema[key]:
        return False
    merged[key] = schema[key]
    return True


def _merge_enum_constraint(merged: dict[str, Any], schema: dict[str, Any]) -> bool:
    if "enum" not in schema:
        return True
    schema_enum = schema["enum"]
    if not isinstance(schema_enum, list):
        return False
    merged["enum"] = [value for value in merged["enum"] if value in schema_enum] if "enum" in merged else schema_enum
    return bool(merged["enum"])


def _merge_multiple_of_constraint(merged: dict[str, Any], schema: dict[str, Any]) -> bool:
    if (multiple_of := schema.get("multipleOf")) is None:
        return True
    if not isinstance(multiple_of, int) or multiple_of <= 0:
        return False
    existing_multiple_of = merged.get("multipleOf")
    merged["multipleOf"] = multiple_of if existing_multiple_of is None else math.lcm(existing_multiple_of, multiple_of)
    return True


def _merge_bound_constraints(
    merged: dict[str, Any],
    schema: dict[str, Any],
    keys: tuple[str, ...],
    merge: Callable[[Any, Any], Any],
) -> None:
    for key in keys:
        if key in schema:
            merged[key] = schema[key] if key not in merged else merge(merged[key], schema[key])


def _merge_simple_allof_for_payload_generation(schema: dict[str, Any]) -> dict[str, Any]:
    all_of = schema.get("allOf")
    if not isinstance(all_of, list) or not all(isinstance(item, dict) for item in all_of):
        return schema

    constraint_schemas = [
        {key: value for key, value in item.items() if key not in SIMPLE_ALLOF_IGNORED_KEYS} for item in all_of
    ]
    if any(set(item) - SIMPLE_ALLOF_SUPPORTED_KEYS for item in constraint_schemas):
        return schema
    if not any(constraint_schemas):
        return schema

    merged = {key: value for key, value in schema.items() if key != "allOf"}
    if set(merged) - SIMPLE_ALLOF_IGNORED_KEYS:
        return schema
    merged = {key: value for key, value in merged.items() if key not in SIMPLE_ALLOF_IGNORED_KEYS}

    is_mergeable = True
    for item in constraint_schemas:
        if not all(_merge_equal_constraint(merged, item, key) for key in ("type", "format", "const")):
            is_mergeable = False
            break
        if not _merge_enum_constraint(merged, item) or not _merge_multiple_of_constraint(merged, item):
            is_mergeable = False
            break
        _merge_bound_constraints(merged, item, ("minimum", "exclusiveMinimum", "minItems", "minLength"), max)
        _merge_bound_constraints(merged, item, ("maximum", "exclusiveMaximum", "maxItems", "maxLength"), min)
        if item.get("uniqueItems") is True:
            merged["uniqueItems"] = True

    return merged if is_mergeable and merged else schema


def _rewrite_prefix_items(schema: dict[str, Any]) -> None:
    if not isinstance(prefix_items := schema.pop("prefixItems", None), list):
        return
    tail_items = schema.pop("items", None)
    schema["items"] = prefix_items
    if tail_items is not None:
        schema["additionalItems"] = tail_items
    return


def _rewrite_contains(schema: dict[str, Any]) -> None:
    match schema.get("contains"):
        case False if schema.get("minContains") == 0:
            schema.pop("contains", None)
            schema.pop("minContains", None)
            schema.pop("maxContains", None)
        case True:
            min_contains = schema.pop("minContains", None)
            max_contains = schema.pop("maxContains", None)
            schema.pop("contains", None)
            if isinstance(min_contains, int):
                schema["minItems"] = max(schema.get("minItems", 0), min_contains)
            if isinstance(max_contains, int):
                schema["maxItems"] = min(schema.get("maxItems", max_contains), max_contains)


def _set_payload_format_enum(schema: dict[str, Any]) -> None:
    if schema.get("type") == "string" and isinstance(
        format_enum := PAYLOAD_FORMAT_ENUMS.get(schema.get("format")),
        list,
    ):
        schema.setdefault("enum", format_enum)


def _schema_for_payload_generation(value: Any) -> Any:
    payload_schema = value
    match value:
        case dict():
            schema = {key: _schema_for_payload_generation(child) for key, child in value.items()}
            schema = _merge_simple_allof_for_payload_generation(schema)
            if schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema":
                schema["$schema"] = "http://json-schema.org/draft-07/schema#"
            _rewrite_prefix_items(schema)
            _rewrite_contains(schema)
            _set_payload_format_enum(schema)
            payload_schema = schema
        case list():
            payload_schema = [_schema_for_payload_generation(child) for child in value]
    return payload_schema
