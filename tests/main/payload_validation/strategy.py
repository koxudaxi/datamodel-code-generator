"""Payload generation and source-schema validation helpers."""

from __future__ import annotations

import sys
from copy import deepcopy
from typing import TYPE_CHECKING, Any

from hypothesis_jsonschema import from_schema
from jsonschema import validators

from .conformance import _iter_schema_nodes, _schema_types
from .schema import _schema_for_payload_generation

if TYPE_CHECKING:
    from hypothesis import strategies as st
    from jsonschema.protocols import Validator

    from .models import SchemaCase


_SourceSchemaCacheKey = tuple[str, str, str]
_source_schema_validator_cache: dict[_SourceSchemaCacheKey, Validator] = {}
_payload_strategy_cache: dict[_SourceSchemaCacheKey, st.SearchStrategy[Any]] = {}


def _source_schema_cache_key(case: SchemaCase) -> _SourceSchemaCacheKey:
    return case.input_file_type, case.source_path.as_posix(), case.id


def source_schema_validator(case: SchemaCase) -> Validator:
    """Build a JSON Schema validator for the original source schema."""
    cache_key = _source_schema_cache_key(case)
    if (validator := _source_schema_validator_cache.get(cache_key)) is not None:
        return validator

    validator_class = validators.validator_for(case.source_schema)
    validator_class.check_schema(case.source_schema)
    validator = validator_class(case.source_schema)
    _source_schema_validator_cache[cache_key] = validator
    return validator


def validate_with_source_schema(case: SchemaCase, payload: Any) -> None:
    """Validate a generated payload against the original source schema."""
    source_schema_validator(case).validate(payload)


def _bound_float_multiples(schema: dict[str, Any]) -> None:
    """Bound the copied sampling domain before integer multipliers become floats.

    The original schema remains the validation oracle. Intervals outside this
    sampling domain need a different strategy, even when their schema is valid.
    """
    for node in _iter_schema_nodes(schema):
        if (
            not isinstance(multiple := node.get("multipleOf"), float)
            or multiple.is_integer()
            or "enum" in node
            or "const" in node
        ):
            continue
        if (schema_types := _schema_types(node)) and not schema_types & {"integer", "number"}:
            continue

        # hypothesis-jsonschema multiplies an integer by multipleOf. Bound both
        # that integer's conversion and its product, with room for rounding and
        # subtraction of the two endpoints during divisibility checks.
        limit = sys.float_info.max / 2 * min(1, multiple)
        minimum = node.get("minimum", -limit)
        maximum = node.get("maximum", limit)
        outside_domain = (
            minimum > limit
            or maximum < -limit
            or (minimum == limit and node.get("exclusiveMinimum") is True)
            or (maximum == -limit and node.get("exclusiveMaximum") is True)
        )
        for keyword, outside in (("exclusiveMinimum", limit), ("exclusiveMaximum", -limit)):
            if isinstance(bound := node.get(keyword), (int, float)) and not isinstance(bound, bool):
                outside_domain |= (keyword == "exclusiveMinimum" and bound >= outside) or (
                    keyword == "exclusiveMaximum" and bound <= outside
                )
        if outside_domain:
            msg = "Numeric interval lies outside the finite multipleOf sampling domain"
            raise ValueError(msg)
        node["minimum"] = max(minimum, -limit)
        node["maximum"] = min(maximum, limit)


def payload_strategy(case: SchemaCase) -> st.SearchStrategy[Any]:
    """Build the deterministic payload strategy for a schema case."""
    cache_key = _source_schema_cache_key(case)
    if (strategy := _payload_strategy_cache.get(cache_key)) is not None:
        return strategy

    validator = source_schema_validator(case)
    schema = _schema_for_payload_generation(deepcopy(case.source_schema))
    _bound_float_multiples(schema)
    strategy = from_schema(schema).filter(validator.is_valid)
    _payload_strategy_cache[cache_key] = strategy
    return strategy
