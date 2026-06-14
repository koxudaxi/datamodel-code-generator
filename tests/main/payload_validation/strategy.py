"""Payload generation and source-schema validation helpers."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any

from hypothesis_jsonschema import from_schema
from jsonschema import validators

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


def payload_strategy(case: SchemaCase) -> st.SearchStrategy[Any]:
    """Build the deterministic payload strategy for a schema case."""
    cache_key = _source_schema_cache_key(case)
    if (strategy := _payload_strategy_cache.get(cache_key)) is not None:
        return strategy

    validator = source_schema_validator(case)
    strategy = from_schema(_schema_for_payload_generation(deepcopy(case.source_schema))).filter(validator.is_valid)
    _payload_strategy_cache[cache_key] = strategy
    return strategy
