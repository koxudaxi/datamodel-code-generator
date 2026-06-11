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


def source_schema_validator(case: SchemaCase) -> Validator:
    """Build a JSON Schema validator for the original source schema."""
    validator_class = validators.validator_for(case.source_schema)
    validator_class.check_schema(case.source_schema)
    return validator_class(case.source_schema)


def validate_with_source_schema(case: SchemaCase, payload: Any) -> None:
    """Validate a generated payload against the original source schema."""
    source_schema_validator(case).validate(payload)


def payload_strategy(case: SchemaCase) -> st.SearchStrategy[Any]:
    """Build the deterministic payload strategy for a schema case."""
    validator = source_schema_validator(case)
    return from_schema(_schema_for_payload_generation(deepcopy(case.source_schema))).filter(validator.is_valid)
