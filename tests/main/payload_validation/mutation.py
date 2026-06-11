"""Near-miss invalid payload mutations for schema-derived validation tests."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any

from .conformance import PYDANTIC_V2_REJECTED_MUTATION_CONSTRAINTS, rejected_mutation_reason
from .models import InvalidPayloadMutation
from .strategy import source_schema_validator

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .models import JsonPath, SchemaCase


PAYLOAD_MUTATION_CONSTRAINTS = frozenset(PYDANTIC_V2_REJECTED_MUTATION_CONSTRAINTS)
COMBINED_SCHEMA_KEYS = ("allOf", "anyOf", "oneOf")


def _resolve_internal_ref(root_schema: dict[str, Any], ref: str) -> Any | None:
    if not ref.startswith("#/"):
        return None

    current: Any = root_schema
    for raw_part in ref.removeprefix("#/").split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _object_at_path(payload: Any, path: JsonPath) -> dict[str, Any] | None:
    current = payload
    for part in path:
        match current:
            case dict() if isinstance(part, str) and part in current:
                current = current[part]
            case list() if isinstance(part, int) and 0 <= part < len(current):
                current = current[part]
            case _:
                return None
    return current if isinstance(current, dict) else None


def _extra_property_name(payload: dict[str, Any], properties: dict[str, Any]) -> str:
    base_name = "__payload_validation_extra__"
    if base_name not in payload and base_name not in properties:
        return base_name

    index = 0
    while (candidate := f"{base_name}{index}") in payload or candidate in properties:
        index += 1
    return candidate


def _missing_required_mutation(root_payload: Any, path: JsonPath, property_name: str) -> InvalidPayloadMutation | None:
    mutated = deepcopy(root_payload)
    if (target := _object_at_path(mutated, path)) is None:
        return None
    target.pop(property_name, None)
    reason = rejected_mutation_reason("required")
    if reason is None:
        return None
    return InvalidPayloadMutation(
        constraint="required",
        path=(*path, property_name),
        payload=mutated,
        reason=reason,
    )


def _extra_property_mutation(
    root_payload: Any,
    path: JsonPath,
    properties: dict[str, Any],
) -> InvalidPayloadMutation | None:
    mutated = deepcopy(root_payload)
    if (target := _object_at_path(mutated, path)) is None:
        return None
    property_name = _extra_property_name(target, properties)
    target[property_name] = "payload-validation-extra"
    reason = rejected_mutation_reason("additionalProperties")
    if reason is None:
        return None
    return InvalidPayloadMutation(
        constraint="additionalProperties",
        path=(*path, property_name),
        payload=mutated,
        reason=reason,
    )


def _iter_object_mutations(
    schema: dict[str, Any],
    root_payload: Any,
    payload: Any,
    path: JsonPath,
) -> Iterator[InvalidPayloadMutation]:
    if not isinstance(payload, dict):
        return
    if not isinstance(properties := schema.get("properties"), dict):
        return

    for property_name in schema.get("required", []):
        if (
            isinstance(property_name, str)
            and property_name in payload
            and property_name in properties
            and (mutation := _missing_required_mutation(root_payload, path, property_name))
        ):
            yield mutation

    if schema.get("additionalProperties") is False and (
        mutation := _extra_property_mutation(root_payload, path, properties)
    ):
        yield mutation


def _iter_child_mutations(
    root_schema: dict[str, Any],
    schema: dict[str, Any],
    root_payload: Any,
    payload: Any,
    path: JsonPath,
    seen_refs: frozenset[str],
) -> Iterator[InvalidPayloadMutation]:
    if isinstance(payload, dict) and isinstance(properties := schema.get("properties"), dict):
        for property_name, property_schema in properties.items():
            if property_name in payload:
                yield from _iter_candidate_mutations(
                    root_schema,
                    property_schema,
                    root_payload,
                    payload[property_name],
                    (*path, property_name),
                    seen_refs,
                )

    if isinstance(payload, list):
        match schema.get("items"):
            case dict() as item_schema:
                for index, item in enumerate(payload):
                    yield from _iter_candidate_mutations(
                        root_schema,
                        item_schema,
                        root_payload,
                        item,
                        (*path, index),
                        seen_refs,
                    )
            case list() as item_schemas:
                for index, item_schema in enumerate(item_schemas[: len(payload)]):
                    yield from _iter_candidate_mutations(
                        root_schema,
                        item_schema,
                        root_payload,
                        payload[index],
                        (*path, index),
                        seen_refs,
                    )

    for keyword in COMBINED_SCHEMA_KEYS:
        if isinstance(subschemas := schema.get(keyword), list):
            for subschema in subschemas:
                yield from _iter_candidate_mutations(root_schema, subschema, root_payload, payload, path, seen_refs)


def _iter_candidate_mutations(
    root_schema: dict[str, Any],
    schema: Any,
    root_payload: Any,
    payload: Any,
    path: JsonPath,
    seen_refs: frozenset[str] = frozenset(),
) -> Iterator[InvalidPayloadMutation]:
    match schema:
        case {"$ref": str(ref)} if (
            ref not in seen_refs and (resolved_schema := _resolve_internal_ref(root_schema, ref)) is not None
        ):
            yield from _iter_candidate_mutations(
                root_schema,
                resolved_schema,
                root_payload,
                payload,
                path,
                seen_refs | {ref},
            )
        case dict():
            yield from _iter_object_mutations(schema, root_payload, payload, path)
            yield from _iter_child_mutations(root_schema, schema, root_payload, payload, path, seen_refs)
        case _:
            return


def _iter_schema_constraint_ids(root_schema: dict[str, Any], schema: Any, seen_refs: frozenset[str]) -> Iterator[str]:
    match schema:
        case {"$ref": str(ref)} if (
            ref not in seen_refs and (resolved_schema := _resolve_internal_ref(root_schema, ref)) is not None
        ):
            yield from _iter_schema_constraint_ids(root_schema, resolved_schema, seen_refs | {ref})
        case dict():
            if isinstance(properties := schema.get("properties"), dict):
                if any(isinstance(name, str) and name in properties for name in schema.get("required", [])):
                    yield "required"
                if schema.get("additionalProperties") is False:
                    yield "additionalProperties"
            for child in schema.values():
                yield from _iter_schema_constraint_ids(root_schema, child, seen_refs)
        case list():
            for child in schema:
                yield from _iter_schema_constraint_ids(root_schema, child, seen_refs)
        case _:
            return


def rejection_constraint_ids(case: SchemaCase) -> frozenset[str]:
    """Return supported rejection constraints present in a schema case."""
    return frozenset(_iter_schema_constraint_ids(case.source_schema, case.source_schema, frozenset()))


def has_rejection_oracle_constraints(case: SchemaCase) -> bool:
    """Return whether a case can produce supported invalid-payload mutations."""
    return bool(rejection_constraint_ids(case))


def invalid_payload_mutations(case: SchemaCase, payload: Any) -> tuple[InvalidPayloadMutation, ...]:
    """Return source-invalid near-miss payload mutations for a valid seed payload."""
    validator = source_schema_validator(case)
    return tuple(
        mutation
        for mutation in _iter_candidate_mutations(case.source_schema, case.source_schema, payload, payload, ())
        if not validator.is_valid(mutation.payload)
    )
