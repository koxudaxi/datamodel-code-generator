"""Constraint conversion utilities for dynamic model generation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datamodel_code_generator.model.base import ConstraintsBase


def constraints_to_field_kwargs(  # noqa: PLR0912, PLR0914, PLR0915
    constraints: ConstraintsBase | None,
) -> dict[str, Any]:
    """Convert DataModel constraints to Pydantic Field kwargs.

    Handles all constraint types from ConstraintsBase.

    Note:
        - In JSON Schema, minItems/maxItems are for arrays while minLength/maxLength
          are for strings. These constraints are mutually exclusive by schema type.
        - Pydantic uses min_length/max_length for both strings and sequences.
        - Constraints like unique_items are stored in json_schema_extra for
          documentation only and are not enforced by Pydantic v2.
    """
    if constraints is None:
        return {}

    kwargs: dict[str, Any] = {}
    json_schema_extra: dict[str, Any] = {}

    min_length = getattr(constraints, "min_length", None)
    if min_length is not None:
        kwargs["min_length"] = min_length

    max_length = getattr(constraints, "max_length", None)
    if max_length is not None:
        kwargs["max_length"] = max_length

    pattern_value = getattr(constraints, "regex", None) or getattr(constraints, "pattern", None)
    if pattern_value is not None:
        kwargs["pattern"] = pattern_value

    ge = getattr(constraints, "ge", None)
    if ge is not None:
        kwargs["ge"] = ge

    gt = getattr(constraints, "gt", None)
    if gt is not None:
        kwargs["gt"] = gt

    le = getattr(constraints, "le", None)
    if le is not None:
        kwargs["le"] = le

    lt = getattr(constraints, "lt", None)
    if lt is not None:
        kwargs["lt"] = lt

    multiple_of = getattr(constraints, "multiple_of", None)
    if multiple_of is not None:
        kwargs["multiple_of"] = multiple_of

    min_items = getattr(constraints, "min_items", None)
    if min_items is not None:
        kwargs["min_length"] = min_items

    max_items = getattr(constraints, "max_items", None)
    if max_items is not None:
        kwargs["max_length"] = max_items

    unique_items = getattr(constraints, "unique_items", None)
    if unique_items is not None:
        json_schema_extra["uniqueItems"] = unique_items

    min_properties = getattr(constraints, "min_properties", None)
    if min_properties is not None:
        json_schema_extra["minProperties"] = min_properties

    max_properties = getattr(constraints, "max_properties", None)
    if max_properties is not None:
        json_schema_extra["maxProperties"] = max_properties

    exclusive_minimum = getattr(constraints, "exclusive_minimum", None)
    if exclusive_minimum is not None:
        kwargs["gt"] = exclusive_minimum

    exclusive_maximum = getattr(constraints, "exclusive_maximum", None)
    if exclusive_maximum is not None:
        kwargs["lt"] = exclusive_maximum

    if json_schema_extra:
        kwargs["json_schema_extra"] = json_schema_extra

    return kwargs
