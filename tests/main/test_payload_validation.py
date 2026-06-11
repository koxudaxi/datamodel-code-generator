"""Validate generated Pydantic v2 models with schema-derived payloads."""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from .payload_validation import (
    BACKEND_REJECTED_MUTATION_CONSTRAINTS,
    BACKEND_UNASSERTED_MUTATION_CONSTRAINTS,
    PAYLOAD_MUTATION_CONSTRAINTS,
    PAYLOAD_VALIDATION_BACKENDS,
    SCHEMA_CASES,
    GeneratedModelCache,
    PayloadBackend,
    SchemaCase,
    discover_unaccounted_files,
    has_rejection_oracle_constraints,
    invalid_payload_mutations,
    load_generated_payload_adapter,
    load_generated_payload_runtime,
    payload_strategy,
    rejection_constraint_ids,
    source_schema_validator,
    validate_with_source_schema,
)

MAX_EXAMPLES = 10
REJECTION_ORACLE_CASES = [case for case in SCHEMA_CASES if has_rejection_oracle_constraints(case)]
SCHEMA_CASE_BY_ID = {case.id: case for case in SCHEMA_CASES}
BACKEND_ACCEPTANCE_CASE_IDS = {
    PayloadBackend.PYDANTIC_V2_DATACLASS: (
        "jsonschema/pydantic_v2_runtime_value.json",
        "jsonschema/simple_string.json",
        "jsonschema/extra_fields.json",
        "jsonschema/nested_json_pointer.json",
        "jsonschema/array_field_constraints.json",
        "openapi/api.yaml::components.schemas.Pet",
        "openapi/additional_properties.yaml::components.schemas.Error",
    ),
    PayloadBackend.MSGSPEC: (
        "jsonschema/pydantic_v2_runtime_value.json",
        "jsonschema/simple_string.json",
        "jsonschema/extra_fields.json",
        "jsonschema/array_field_constraints.json",
        "openapi/api.yaml::components.schemas.Pet",
        "openapi/additional_properties.yaml::components.schemas.Error",
    ),
    PayloadBackend.DATACLASSES: (
        "jsonschema/pydantic_v2_runtime_value.json",
        "jsonschema/extra_fields.json",
        "jsonschema/nested_json_pointer.json",
        "openapi/additional_properties.yaml::components.schemas.Error",
    ),
}
BACKEND_REJECTION_CASE_IDS = {
    PayloadBackend.PYDANTIC_V2_DATACLASS: (
        "jsonschema/pydantic_v2_runtime_value.json",
        "jsonschema/extra_fields.json",
        "jsonschema/nested_json_pointer.json",
        "openapi/additional_properties.yaml::components.schemas.Error",
    ),
    PayloadBackend.MSGSPEC: (
        "jsonschema/pydantic_v2_runtime_value.json",
        "jsonschema/extra_fields.json",
        "openapi/additional_properties.yaml::components.schemas.Error",
    ),
}
BACKEND_ACCEPTANCE_CASES = [
    pytest.param(backend, SCHEMA_CASE_BY_ID[case_id], id=f"{backend.value}:{case_id}")
    for backend, case_ids in BACKEND_ACCEPTANCE_CASE_IDS.items()
    for case_id in case_ids
]
BACKEND_REJECTION_CASES = [
    pytest.param(backend, SCHEMA_CASE_BY_ID[case_id], id=f"{backend.value}:{case_id}")
    for backend, case_ids in BACKEND_REJECTION_CASE_IDS.items()
    for case_id in case_ids
]


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
    for backend in PAYLOAD_VALIDATION_BACKENDS:
        rejected_constraints = BACKEND_REJECTED_MUTATION_CONSTRAINTS[backend]
        unasserted_constraints = BACKEND_UNASSERTED_MUTATION_CONSTRAINTS[backend]
        if overlap := sorted(  # pragma: no cover
            set(rejected_constraints) & set(unasserted_constraints)
        ):
            pytest.fail(
                f"{backend.value}: mutation constraints cannot be both asserted and unasserted:\n" + "\n".join(overlap)
            )

        if missing := sorted(  # pragma: no cover
            PAYLOAD_MUTATION_CONSTRAINTS - set(rejected_constraints) - set(unasserted_constraints)
        ):
            pytest.fail(f"{backend.value}: mutation constraints need rejection policy reasons:\n" + "\n".join(missing))

        reasons = {
            **rejected_constraints,
            **unasserted_constraints,
        }
        if unclassified := sorted(  # pragma: no cover
            constraint for constraint, reason in reasons.items() if not reason
        ):
            pytest.fail(f"{backend.value}: mutation policy entries need non-empty reasons:\n" + "\n".join(unclassified))


def test_payload_rejection_oracle_covers_supported_policy_constraints() -> None:
    """The supported rejection policy must correspond to at least one schema case."""
    for backend, rejected_constraints in BACKEND_REJECTED_MUTATION_CONSTRAINTS.items():
        covered_constraints = frozenset(
            constraint for case in SCHEMA_CASES for constraint in rejection_constraint_ids(case, backend)
        )
        if missing := sorted(  # pragma: no cover
            set(rejected_constraints) - covered_constraints
        ):
            pytest.fail(
                f"{backend.value}: supported rejection constraints are not covered by schema cases:\n"
                + "\n".join(missing)
            )


def test_payload_backend_representative_matrix_is_classified() -> None:
    """Every non-default backend must declare representative cases for its supported oracle shape."""
    missing_acceptance = [
        backend.value
        for backend in (PayloadBackend.PYDANTIC_V2_DATACLASS, PayloadBackend.MSGSPEC, PayloadBackend.DATACLASSES)
        if not BACKEND_ACCEPTANCE_CASE_IDS.get(backend)
    ]
    if missing_acceptance:  # pragma: no cover
        pytest.fail("Payload backend acceptance matrix needs representative cases:\n" + "\n".join(missing_acceptance))

    missing_rejection = [
        backend.value
        for backend in PAYLOAD_VALIDATION_BACKENDS
        if backend is not PayloadBackend.PYDANTIC_V2 and not BACKEND_REJECTION_CASE_IDS.get(backend)
    ]
    if missing_rejection:  # pragma: no cover
        pytest.fail("Payload backend rejection matrix needs representative cases:\n" + "\n".join(missing_rejection))


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


@pytest.mark.parametrize(("backend", "case"), BACKEND_ACCEPTANCE_CASES)
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
def test_generated_payload_backend_accepts_representative_schema_payloads(
    backend: PayloadBackend,
    case: SchemaCase,
    generated_model_cache: dict[str, Any],
    data: st.DataObject,
) -> None:
    """Representative non-default backends should accept source-valid payloads."""
    payload = data.draw(payload_strategy(case), label=f"{backend.value}:{case.id}:valid")
    validate_with_source_schema(case, payload)
    runtime = load_generated_payload_runtime(case, generated_model_cache, backend)
    runtime.validate_python(payload)


@pytest.mark.parametrize(("backend", "case"), BACKEND_REJECTION_CASES)
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
def test_generated_payload_backend_rejects_representative_schema_invalid_payloads(
    backend: PayloadBackend,
    case: SchemaCase,
    generated_model_cache: dict[str, Any],
    data: st.DataObject,
) -> None:
    """Representative runtime-validation backends should reject supported near-miss payloads."""
    payload = data.draw(payload_strategy(case), label=f"{backend.value}:{case.id}:valid")
    validate_with_source_schema(case, payload)
    mutations = invalid_payload_mutations(case, payload, backend)
    assume(bool(mutations))

    mutation = data.draw(st.sampled_from(mutations), label=f"{backend.value}:{case.id}:invalid")
    if source_schema_validator(case).is_valid(mutation.payload):  # pragma: no cover
        pytest.fail(f"{case.id}: mutation stayed source-valid for {mutation.constraint} at {mutation.path}")

    runtime = load_generated_payload_runtime(case, generated_model_cache, backend)
    with pytest.raises(runtime.rejection_exceptions):
        runtime.validate_python(mutation.payload)
