"""Public helpers for schema-derived payload validation tests."""

from __future__ import annotations

from .cases import SCHEMA_CASES, discover_unaccounted_files
from .codegen import PayloadAdapterError, generate_payload_adapter, load_generated_payload_adapter
from .conformance import (
    PYDANTIC_V2_REJECTED_MUTATION_CONSTRAINTS,
    PYDANTIC_V2_UNASSERTED_MUTATION_CONSTRAINTS,
)
from .models import GeneratedModelCache, InvalidPayloadMutation, SchemaCase
from .mutation import (
    PAYLOAD_MUTATION_CONSTRAINTS,
    has_rejection_oracle_constraints,
    invalid_payload_mutations,
    rejection_constraint_ids,
)
from .strategy import payload_strategy, source_schema_validator, validate_with_source_schema

__all__ = [
    "PAYLOAD_MUTATION_CONSTRAINTS",
    "PYDANTIC_V2_REJECTED_MUTATION_CONSTRAINTS",
    "PYDANTIC_V2_UNASSERTED_MUTATION_CONSTRAINTS",
    "SCHEMA_CASES",
    "GeneratedModelCache",
    "InvalidPayloadMutation",
    "PayloadAdapterError",
    "SchemaCase",
    "discover_unaccounted_files",
    "generate_payload_adapter",
    "has_rejection_oracle_constraints",
    "invalid_payload_mutations",
    "load_generated_payload_adapter",
    "payload_strategy",
    "rejection_constraint_ids",
    "source_schema_validator",
    "validate_with_source_schema",
]
