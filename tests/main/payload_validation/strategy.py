"""Payload generation and source-schema validation helpers."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any

from hypothesis_jsonschema import from_schema
from jsonschema import validators

from .schema import _schema_for_payload_generation

if TYPE_CHECKING:
    from hypothesis import strategies as st

    from .models import SchemaCase


def validate_with_source_schema(case: SchemaCase, payload: Any) -> None:
    """Validate a generated payload against the original source schema."""
    validator_class = validators.validator_for(case.source_schema)
    validator_class.check_schema(case.source_schema)
    validator_class(case.source_schema).validate(payload)


def payload_strategy(case: SchemaCase) -> st.SearchStrategy[Any]:
    """Build the deterministic payload strategy for a schema case."""
    validator_class = validators.validator_for(case.source_schema)
    validator_class.check_schema(case.source_schema)
    validator = validator_class(case.source_schema)
    return from_schema(_schema_for_payload_generation(deepcopy(case.source_schema))).filter(validator.is_valid)
