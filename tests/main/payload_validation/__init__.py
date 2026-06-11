"""Public helpers for schema-derived payload validation tests."""

from __future__ import annotations

from .cases import SCHEMA_CASES, discover_unaccounted_files
from .codegen import (
    PayloadAdapterError,
    PayloadRuntime,
    generate_payload_adapter,
    generate_payload_runtime,
    load_generated_payload_adapter,
    load_generated_payload_runtime,
)
from .conformance import (
    BACKEND_REJECTED_MUTATION_CONSTRAINTS,
    BACKEND_UNASSERTED_MUTATION_CONSTRAINTS,
    PAYLOAD_VALIDATION_BACKENDS,
    PYDANTIC_V2_REJECTED_MUTATION_CONSTRAINTS,
    PYDANTIC_V2_UNASSERTED_MUTATION_CONSTRAINTS,
)
from .models import GeneratedModelCache, InvalidPayloadMutation, PayloadBackend, SchemaCase
from .mutation import (
    PAYLOAD_MUTATION_CONSTRAINTS,
    has_rejection_oracle_constraints,
    invalid_payload_mutations,
    rejection_constraint_ids,
)
from .strategy import payload_strategy, source_schema_validator, validate_with_source_schema

__all__ = [
    "BACKEND_REJECTED_MUTATION_CONSTRAINTS",
    "BACKEND_UNASSERTED_MUTATION_CONSTRAINTS",
    "PAYLOAD_MUTATION_CONSTRAINTS",
    "PAYLOAD_VALIDATION_BACKENDS",
    "PYDANTIC_V2_REJECTED_MUTATION_CONSTRAINTS",
    "PYDANTIC_V2_UNASSERTED_MUTATION_CONSTRAINTS",
    "SCHEMA_CASES",
    "GeneratedModelCache",
    "InvalidPayloadMutation",
    "PayloadAdapterError",
    "PayloadBackend",
    "PayloadRuntime",
    "SchemaCase",
    "discover_unaccounted_files",
    "generate_payload_adapter",
    "generate_payload_runtime",
    "has_rejection_oracle_constraints",
    "invalid_payload_mutations",
    "load_generated_payload_adapter",
    "load_generated_payload_runtime",
    "payload_strategy",
    "rejection_constraint_ids",
    "source_schema_validator",
    "validate_with_source_schema",
]
