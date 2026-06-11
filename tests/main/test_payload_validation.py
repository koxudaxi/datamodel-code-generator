"""Validate generated Pydantic v2 models with schema-derived payloads."""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from .payload_validation import (
    PAYLOAD_MUTATION_CONSTRAINTS,
    PYDANTIC_V2_REJECTED_MUTATION_CONSTRAINTS,
    PYDANTIC_V2_UNASSERTED_MUTATION_CONSTRAINTS,
    SCHEMA_CASES,
    GeneratedModelCache,
    SchemaCase,
    discover_unaccounted_files,
    has_rejection_oracle_constraints,
    invalid_payload_mutations,
    load_generated_payload_adapter,
    payload_strategy,
    rejection_constraint_ids,
    source_schema_validator,
    validate_with_source_schema,
)

MAX_EXAMPLES = 10
REJECTION_ORACLE_CASES = [case for case in SCHEMA_CASES if has_rejection_oracle_constraints(case)]


@pytest.fixture(scope="session")
def generated_model_cache(tmp_path_factory: pytest.TempPathFactory) -> GeneratedModelCache:
    """Cache generated Payload adapters across Hypothesis examples."""
    return GeneratedModelCache({"base": tmp_path_factory.mktemp("payload_validation"), "adapters": {}})


def test_payload_validation_cases_cover_discovered_schema_files() -> None:
    """Every discovered schema fixture must be validated or explicitly excluded."""
    unaccounted = discover_unaccounted_files(SCHEMA_CASES)
    if unaccounted:  # pragma: no cover
        pytest.fail(
            "Schema files must be covered by payload validation or added to EXCLUDED_FILES with a reason:\n"
            + "\n".join(unaccounted)
        )


def test_payload_rejection_oracle_policy_is_classified() -> None:
    """Every invalid-payload mutation constraint must be machine-classified."""
    if overlap := sorted(  # pragma: no cover
        set(PYDANTIC_V2_REJECTED_MUTATION_CONSTRAINTS) & set(PYDANTIC_V2_UNASSERTED_MUTATION_CONSTRAINTS)
    ):
        pytest.fail("Mutation constraints cannot be both asserted and unasserted:\n" + "\n".join(overlap))

    if missing := sorted(  # pragma: no cover
        PAYLOAD_MUTATION_CONSTRAINTS - set(PYDANTIC_V2_REJECTED_MUTATION_CONSTRAINTS)
    ):
        pytest.fail("Mutation constraints need pydantic v2 rejection policy reasons:\n" + "\n".join(missing))

    reasons = {
        **PYDANTIC_V2_REJECTED_MUTATION_CONSTRAINTS,
        **PYDANTIC_V2_UNASSERTED_MUTATION_CONSTRAINTS,
    }
    if unclassified := sorted(  # pragma: no cover
        constraint for constraint, reason in reasons.items() if not reason
    ):
        pytest.fail("Mutation policy entries need non-empty reasons:\n" + "\n".join(unclassified))


def test_payload_rejection_oracle_covers_supported_policy_constraints() -> None:
    """The supported rejection policy must correspond to at least one schema case."""
    covered_constraints = frozenset(
        constraint for case in SCHEMA_CASES for constraint in rejection_constraint_ids(case)
    )
    if missing := sorted(  # pragma: no cover
        set(PYDANTIC_V2_REJECTED_MUTATION_CONSTRAINTS) - covered_constraints
    ):
        pytest.fail("Supported rejection constraints are not covered by schema cases:\n" + "\n".join(missing))


@pytest.mark.parametrize("case", SCHEMA_CASES, ids=lambda case: case.id)
@settings(
    database=None,
    deadline=None,
    derandomize=True,
    max_examples=MAX_EXAMPLES,
    suppress_health_check=[
        HealthCheck.filter_too_much,
        HealthCheck.function_scoped_fixture,
        HealthCheck.too_slow,
    ],
)
@given(data=st.data())
def test_generated_pydantic_v2_model_accepts_schema_derived_payloads(
    case: SchemaCase,
    generated_model_cache: dict[str, Any],
    data: st.DataObject,
) -> None:
    """Payloads accepted by the source schema should validate against generated code."""
    payload = data.draw(payload_strategy(case), label=case.id)
    validate_with_source_schema(case, payload)
    adapter = load_generated_payload_adapter(case, generated_model_cache)
    adapter.validate_python(payload)


@pytest.mark.parametrize("case", REJECTION_ORACLE_CASES, ids=lambda case: case.id)
@settings(
    database=None,
    deadline=None,
    derandomize=True,
    max_examples=MAX_EXAMPLES,
    suppress_health_check=[
        HealthCheck.filter_too_much,
        HealthCheck.function_scoped_fixture,
        HealthCheck.too_slow,
    ],
)
@given(data=st.data())
def test_generated_pydantic_v2_model_rejects_schema_invalid_payloads(
    case: SchemaCase,
    generated_model_cache: dict[str, Any],
    data: st.DataObject,
) -> None:
    """Near-miss payloads rejected by the source schema should fail generated validation."""
    payload = data.draw(payload_strategy(case), label=f"{case.id}:valid")
    validate_with_source_schema(case, payload)
    mutations = invalid_payload_mutations(case, payload)
    assume(bool(mutations))

    mutation = data.draw(st.sampled_from(mutations), label=f"{case.id}:invalid")
    if source_schema_validator(case).is_valid(mutation.payload):  # pragma: no cover
        pytest.fail(f"{case.id}: mutation stayed source-valid for {mutation.constraint} at {mutation.path}")

    adapter = load_generated_payload_adapter(case, generated_model_cache)
    with pytest.raises(ValidationError):
        adapter.validate_python(mutation.payload)
