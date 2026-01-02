"""Constraint conversion utilities for dynamic model generation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from datamodel_code_generator.util import model_dump

if TYPE_CHECKING:
    from datamodel_code_generator.model.base import ConstraintsBase

CONSTRAINT_FIELD_MAP: dict[str, str] = {
    "ge": "ge",
    "gt": "gt",
    "le": "le",
    "lt": "lt",
    "multiple_of": "multiple_of",
    "min_length": "min_length",
    "max_length": "max_length",
    "regex": "pattern",
    "pattern": "pattern",
    "min_items": "min_length",
    "max_items": "max_length",
}

JSON_SCHEMA_EXTRA_FIELDS: frozenset[str] = frozenset({
    "unique_items",
    "min_properties",
    "max_properties",
})


def constraints_to_field_kwargs(
    constraints: ConstraintsBase | None,
) -> dict[str, Any]:
    """Convert DataModel constraints to Pydantic Field kwargs."""
    if constraints is None:
        return {}

    kwargs: dict[str, Any] = {}
    json_schema_extra: dict[str, Any] = {}

    for field_name, value in model_dump(constraints).items():
        if value is None:
            continue

        if field_name in CONSTRAINT_FIELD_MAP:
            kwargs[CONSTRAINT_FIELD_MAP[field_name]] = value
        elif field_name in JSON_SCHEMA_EXTRA_FIELDS:
            json_schema_extra[_to_camel_case(field_name)] = value

    if json_schema_extra:
        kwargs["json_schema_extra"] = json_schema_extra

    return kwargs


def _to_camel_case(snake_str: str) -> str:
    """Convert snake_case to camelCase."""
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])
