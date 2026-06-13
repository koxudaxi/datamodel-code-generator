"""Validate generated Pydantic v2 models with schema-derived payloads."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from typing import Any, Literal, TypeAlias

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st
from packaging.version import Version
from pydantic import VERSION as PYDANTIC_VERSION
from pydantic import ValidationError

from .payload_validation import (
    BACKEND_ACCEPTANCE_EXCLUDED_CASES,
    BACKEND_REJECTED_MUTATION_CONSTRAINTS,
    BACKEND_REJECTION_EXCLUDED_CASES,
    BACKEND_UNASSERTED_MUTATION_CONSTRAINTS,
    PAYLOAD_MUTATION_CONSTRAINTS,
    PAYLOAD_VALIDATION_BACKENDS,
    PYDANTIC_V2_FULL_PAYLOAD_RUNTIME_MIN_VERSION,
    PYDANTIC_V2_LEGACY_RUNTIME_EXCLUDED_CASES,
    PYDANTIC_V2_LEGACY_RUNTIME_ROUND_TRIP_EXCLUDED_CASES,
    ROUND_TRIP_EXCLUDED_CASES,
    SCHEMA_CASES,
    GeneratedModelCache,
    PayloadBackend,
    SchemaCase,
    backend_acceptance_exclusion_reason,
    backend_rejection_exclusion_reason,
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


def _max_examples_from_env(raw_examples: str | None = None) -> int:
    if raw_examples is None:
        raw_examples = os.environ.get("DCG_PAYLOAD_MAX_EXAMPLES")
    if raw_examples is None:
        return 10
    try:
        max_examples = int(raw_examples)
    except ValueError as exc:
        msg = "DCG_PAYLOAD_MAX_EXAMPLES must be a positive integer"
        raise ValueError(msg) from exc
    if max_examples < 1:
        msg = "DCG_PAYLOAD_MAX_EXAMPLES must be a positive integer"
        raise ValueError(msg)
    return max_examples


BackendCaseMode = Literal["representative", "all"]


def _backend_case_mode_from_env(raw_mode: str | None = None) -> BackendCaseMode:
    if raw_mode is None:
        raw_mode = os.environ.get("DCG_PAYLOAD_BACKEND_CASES")
    match raw_mode:
        case None | "" | "representative":
            return "representative"
        case "all":
            return "all"
        case _:
            msg = "DCG_PAYLOAD_BACKEND_CASES must be either 'representative' or 'all'"
            raise ValueError(msg)


MAX_EXAMPLES = _max_examples_from_env()
BACKEND_CASE_MODE = _backend_case_mode_from_env()
PYDANTIC_RUNTIME_VERSION = Version(PYDANTIC_VERSION)
PYDANTIC_V2_FULL_PAYLOAD_RUNTIME_MIN = Version(PYDANTIC_V2_FULL_PAYLOAD_RUNTIME_MIN_VERSION)
PydanticV2LegacyRuntimeExclusions: TypeAlias = Mapping[PayloadBackend, Mapping[str, str]]
PYDANTIC_V2_LEGACY_RUNTIME_EXCLUSION_SETS = (PYDANTIC_V2_LEGACY_RUNTIME_EXCLUDED_CASES,)
PYDANTIC_V2_LEGACY_RUNTIME_ROUND_TRIP_EXCLUSION_SETS = (
    PYDANTIC_V2_LEGACY_RUNTIME_EXCLUDED_CASES,
    PYDANTIC_V2_LEGACY_RUNTIME_ROUND_TRIP_EXCLUDED_CASES,
)
REJECTION_ORACLE_CASES = [case for case in SCHEMA_CASES if has_rejection_oracle_constraints(case)]
SCHEMA_CASE_BY_ID = {case.id: case for case in SCHEMA_CASES}
ROUND_TRIP_CASES = [case for case in SCHEMA_CASES if case.id not in ROUND_TRIP_EXCLUDED_CASES]
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


def _backend_acceptance_case_ids(
    backend: PayloadBackend,
    case_mode: BackendCaseMode = BACKEND_CASE_MODE,
) -> tuple[str, ...]:
    if case_mode == "representative" or backend is PayloadBackend.DATACLASSES:
        return BACKEND_ACCEPTANCE_CASE_IDS[backend]
    representative_cases = set(BACKEND_ACCEPTANCE_CASE_IDS[backend])
    return tuple(
        case.id
        for case in SCHEMA_CASES
        if case.id in representative_cases or backend_acceptance_exclusion_reason(case, backend) is None
    )


def _backend_rejection_case_ids(
    backend: PayloadBackend,
    case_mode: BackendCaseMode = BACKEND_CASE_MODE,
) -> tuple[str, ...]:
    if case_mode == "representative":
        return BACKEND_REJECTION_CASE_IDS[backend]
    representative_cases = set(BACKEND_REJECTION_CASE_IDS[backend])
    return tuple(
        case.id
        for case in SCHEMA_CASES
        if (case.id in representative_cases or backend_rejection_exclusion_reason(case, backend) is None)
        and has_rejection_oracle_constraints(case, backend)
    )


def _pydantic_v2_legacy_runtime_exclusion_reason(
    case: SchemaCase,
    backend: PayloadBackend,
    runtime_version: Version = PYDANTIC_RUNTIME_VERSION,
    exclusion_sets: Sequence[PydanticV2LegacyRuntimeExclusions] = PYDANTIC_V2_LEGACY_RUNTIME_EXCLUSION_SETS,
) -> str | None:
    if runtime_version >= PYDANTIC_V2_FULL_PAYLOAD_RUNTIME_MIN:
        return None
    for excluded_cases in exclusion_sets:
        if reason := excluded_cases.get(backend, {}).get(case.id):
            return reason
    return None


def _pydantic_v2_legacy_runtime_skip_marks(
    case: SchemaCase,
    backend: PayloadBackend,
    runtime_version: Version = PYDANTIC_RUNTIME_VERSION,
    exclusion_sets: Sequence[PydanticV2LegacyRuntimeExclusions] = PYDANTIC_V2_LEGACY_RUNTIME_EXCLUSION_SETS,
) -> tuple[pytest.MarkDecorator, ...]:
    if reason := _pydantic_v2_legacy_runtime_exclusion_reason(case, backend, runtime_version, exclusion_sets):
        return (pytest.mark.skip(reason=reason),)
    return ()


def _pydantic_v2_case_param(case: SchemaCase) -> pytest.ParameterSet:
    return pytest.param(
        case,
        id=case.id,
        marks=_pydantic_v2_legacy_runtime_skip_marks(case, PayloadBackend.PYDANTIC_V2),
    )


def _pydantic_v2_round_trip_case_param(case: SchemaCase) -> pytest.ParameterSet:
    return pytest.param(
        case,
        id=case.id,
        marks=_pydantic_v2_legacy_runtime_skip_marks(
            case,
            PayloadBackend.PYDANTIC_V2,
            exclusion_sets=PYDANTIC_V2_LEGACY_RUNTIME_ROUND_TRIP_EXCLUSION_SETS,
        ),
    )


def _backend_case_param(backend: PayloadBackend, case: SchemaCase) -> pytest.ParameterSet:
    return pytest.param(
        backend,
        case,
        id=f"{backend.value}:{case.id}",
        marks=_pydantic_v2_legacy_runtime_skip_marks(case, backend),
    )


PYDANTIC_V2_ACCEPTANCE_CASES = [_pydantic_v2_case_param(case) for case in SCHEMA_CASES]
PYDANTIC_V2_ROUND_TRIP_CASES = [_pydantic_v2_round_trip_case_param(case) for case in ROUND_TRIP_CASES]
PYDANTIC_V2_REJECTION_CASES = [_pydantic_v2_case_param(case) for case in REJECTION_ORACLE_CASES]
BACKEND_ACCEPTANCE_CASES = [
    _backend_case_param(backend, SCHEMA_CASE_BY_ID[case_id])
    for backend in BACKEND_ACCEPTANCE_CASE_IDS
    for case_id in _backend_acceptance_case_ids(backend)
]
BACKEND_REJECTION_CASES = [
    _backend_case_param(backend, SCHEMA_CASE_BY_ID[case_id])
    for backend in BACKEND_REJECTION_CASE_IDS
    for case_id in _backend_rejection_case_ids(backend)
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


def test_payload_backend_full_matrix_exclusions_are_classified() -> None:
    """Full backend matrix exclusions must reference existing cases and carry reasons."""
    known_cases = set(SCHEMA_CASE_BY_ID)
    exclusion_sets = {
        "acceptance": BACKEND_ACCEPTANCE_EXCLUDED_CASES,
        "rejection": BACKEND_REJECTION_EXCLUDED_CASES,
    }
    for exclusion_type, backend_exclusions in exclusion_sets.items():
        for backend, excluded_cases in backend_exclusions.items():
            if missing_reasons := sorted(  # pragma: no cover
                case_id for case_id, reason in excluded_cases.items() if not reason
            ):
                pytest.fail(
                    f"{backend.value}: {exclusion_type} exclusions require reasons:\n" + "\n".join(missing_reasons)
                )
            if unknown_cases := sorted(set(excluded_cases) - known_cases):  # pragma: no cover
                pytest.fail(
                    f"{backend.value}: {exclusion_type} exclusions reference unknown cases:\n"
                    + "\n".join(unknown_cases)
                )

    representative_dataclass_cases = set(BACKEND_ACCEPTANCE_CASE_IDS[PayloadBackend.DATACLASSES])
    if unclassified_dataclasses := [  # pragma: no cover
        case.id
        for case in SCHEMA_CASES
        if case.id not in representative_dataclass_cases
        and not backend_acceptance_exclusion_reason(case, PayloadBackend.DATACLASSES)
    ]:
        pytest.fail(
            f"{PayloadBackend.DATACLASSES.value}: full-matrix exclusions require reasons:\n"
            + "\n".join(unclassified_dataclasses)
        )

    for backend in (PayloadBackend.PYDANTIC_V2_DATACLASS, PayloadBackend.MSGSPEC):
        representative_acceptance_cases = set(BACKEND_ACCEPTANCE_CASE_IDS[backend])
        if unclassified_acceptance := sorted(  # pragma: no cover
            case.id
            for case in SCHEMA_CASES
            if case.input_file_type == "openapi"
            and case.id not in representative_acceptance_cases
            and not backend_acceptance_exclusion_reason(case, backend)
        ):
            pytest.fail(
                f"{backend.value}: OpenAPI acceptance exclusions require reasons:\n"
                + "\n".join(unclassified_acceptance)
            )

        representative_rejection_cases = set(BACKEND_REJECTION_CASE_IDS.get(backend, ()))
        if unclassified_rejection := sorted(  # pragma: no cover
            case.id
            for case in SCHEMA_CASES
            if case.input_file_type == "openapi"
            and case.id not in representative_rejection_cases
            and has_rejection_oracle_constraints(case, backend)
            and not backend_rejection_exclusion_reason(case, backend)
        ):
            pytest.fail(
                f"{backend.value}: OpenAPI rejection exclusions require reasons:\n" + "\n".join(unclassified_rejection)
            )


def test_payload_round_trip_exclusions_are_classified() -> None:
    """Round-trip dump exclusions must name existing cases and carry reasons."""
    if missing_reasons := sorted(  # pragma: no cover
        case_id for case_id, reason in ROUND_TRIP_EXCLUDED_CASES.items() if not reason
    ):
        pytest.fail("Payload round-trip exclusions require reasons:\n" + "\n".join(missing_reasons))

    if unknown_cases := sorted(set(ROUND_TRIP_EXCLUDED_CASES) - set(SCHEMA_CASE_BY_ID)):  # pragma: no cover
        pytest.fail("Payload round-trip exclusions reference unknown cases:\n" + "\n".join(unknown_cases))


def test_pydantic_v2_legacy_runtime_exclusions_are_classified() -> None:
    """Pydantic-version-specific payload exclusions must name existing cases and carry reasons."""
    known_cases = set(SCHEMA_CASE_BY_ID)
    supported_backends = {PayloadBackend.PYDANTIC_V2, PayloadBackend.PYDANTIC_V2_DATACLASS}
    exclusion_sets = {
        "payload": PYDANTIC_V2_LEGACY_RUNTIME_EXCLUDED_CASES,
        "round-trip": PYDANTIC_V2_LEGACY_RUNTIME_ROUND_TRIP_EXCLUDED_CASES,
    }
    for exclusion_kind, exclusion_set in exclusion_sets.items():
        if unsupported_backends := sorted(
            backend.value for backend in exclusion_set if backend not in supported_backends
        ):  # pragma: no cover
            pytest.fail(
                f"Pydantic legacy runtime {exclusion_kind} exclusions reference unsupported backends:\n"
                + "\n".join(unsupported_backends)
            )

        for backend, excluded_cases in exclusion_set.items():
            if missing_reasons := sorted(  # pragma: no cover
                case_id for case_id, reason in excluded_cases.items() if not reason
            ):
                pytest.fail(
                    f"{backend.value}: Pydantic legacy runtime {exclusion_kind} exclusions require reasons:\n"
                    + "\n".join(missing_reasons)
                )
            if unknown_cases := sorted(set(excluded_cases) - known_cases):  # pragma: no cover
                pytest.fail(
                    f"{backend.value}: Pydantic legacy runtime {exclusion_kind} exclusions reference unknown cases:\n"
                    + "\n".join(unknown_cases)
                )


@pytest.mark.allow_direct_assert
def test_pydantic_v2_legacy_runtime_exclusions_are_version_gated() -> None:
    """Pydantic 2.0 keeps only version-specific skips; newer runtimes keep full coverage."""
    case = SCHEMA_CASE_BY_ID["jsonschema/lookaround_anyof_nullable.json"]
    assert _pydantic_v2_legacy_runtime_exclusion_reason(case, PayloadBackend.PYDANTIC_V2, Version("2.0.3"))
    assert (
        _pydantic_v2_legacy_runtime_exclusion_reason(
            case, PayloadBackend.PYDANTIC_V2, PYDANTIC_V2_FULL_PAYLOAD_RUNTIME_MIN
        )
        is None
    )
    assert _pydantic_v2_legacy_runtime_exclusion_reason(case, PayloadBackend.MSGSPEC, Version("2.0.3")) is None
    assert _pydantic_v2_legacy_runtime_skip_marks(case, PayloadBackend.PYDANTIC_V2, Version("2.0.3"))
    assert not _pydantic_v2_legacy_runtime_skip_marks(
        case, PayloadBackend.PYDANTIC_V2, PYDANTIC_V2_FULL_PAYLOAD_RUNTIME_MIN
    )
    round_trip_case = SCHEMA_CASE_BY_ID["jsonschema/property_names_ref_enum.json"]
    assert _pydantic_v2_legacy_runtime_exclusion_reason(
        round_trip_case,
        PayloadBackend.PYDANTIC_V2,
        Version("2.0.3"),
        PYDANTIC_V2_LEGACY_RUNTIME_ROUND_TRIP_EXCLUSION_SETS,
    )
    assert (
        _pydantic_v2_legacy_runtime_exclusion_reason(
            round_trip_case,
            PayloadBackend.PYDANTIC_V2,
            Version("2.0.3"),
        )
        is None
    )


@pytest.mark.parametrize(
    ("raw_examples", "expected_examples"),
    [
        (None, 10),
        ("1", 1),
        ("100", 100),
    ],
)
@pytest.mark.allow_direct_assert
def test_payload_max_examples_env_is_configurable(
    monkeypatch: pytest.MonkeyPatch,
    raw_examples: str | None,
    expected_examples: int,
) -> None:
    """Nightly runs can raise Hypothesis examples without changing PR defaults."""
    monkeypatch.delenv("DCG_PAYLOAD_MAX_EXAMPLES", raising=False)
    assert _max_examples_from_env(raw_examples) == expected_examples
    monkeypatch.setenv("DCG_PAYLOAD_MAX_EXAMPLES", "50")
    assert _max_examples_from_env(None) == 50


@pytest.mark.parametrize("raw_examples", ["", "0", "-1", "not-an-int"])
def test_payload_max_examples_env_rejects_invalid_values(raw_examples: str) -> None:
    """Invalid example-count overrides fail before test settings are created."""
    with pytest.raises(ValueError, match="positive integer"):
        _max_examples_from_env(raw_examples)


@pytest.mark.parametrize(
    ("raw_mode", "expected_mode"),
    [
        (None, "representative"),
        ("", "representative"),
        ("representative", "representative"),
        ("all", "all"),
    ],
)
@pytest.mark.allow_direct_assert
def test_payload_backend_case_mode_env_is_configurable(
    monkeypatch: pytest.MonkeyPatch,
    raw_mode: str | None,
    expected_mode: str,
) -> None:
    """Nightly runs can widen non-default backend coverage without changing PR defaults."""
    monkeypatch.delenv("DCG_PAYLOAD_BACKEND_CASES", raising=False)
    assert _backend_case_mode_from_env(raw_mode) == expected_mode
    monkeypatch.setenv("DCG_PAYLOAD_BACKEND_CASES", "all")
    assert _backend_case_mode_from_env(None) == "all"


def test_payload_backend_case_mode_env_rejects_invalid_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid backend matrix modes fail before parametrization."""
    with pytest.raises(ValueError, match="representative"):
        _backend_case_mode_from_env("everything")
    monkeypatch.setenv("DCG_PAYLOAD_BACKEND_CASES", "everything")
    with pytest.raises(ValueError, match="representative"):
        _backend_case_mode_from_env(None)


@pytest.mark.allow_direct_assert
def test_payload_backend_all_case_mode_widens_runtime_validating_backends() -> None:
    """Full backend mode widens runtime-validating backends and leaves plain dataclasses representative-only."""
    for backend in (PayloadBackend.PYDANTIC_V2_DATACLASS, PayloadBackend.MSGSPEC):
        representative_acceptance_cases = set(_backend_acceptance_case_ids(backend, "representative"))
        all_acceptance_cases = set(_backend_acceptance_case_ids(backend, "all"))
        assert representative_acceptance_cases < all_acceptance_cases
        assert any(
            case_id.startswith("jsonschema/") for case_id in all_acceptance_cases - representative_acceptance_cases
        )

        representative_rejection_cases = set(_backend_rejection_case_ids(backend, "representative"))
        all_rejection_cases = set(_backend_rejection_case_ids(backend, "all"))
        assert representative_rejection_cases < all_rejection_cases
        assert all(
            has_rejection_oracle_constraints(SCHEMA_CASE_BY_ID[case_id], backend) for case_id in all_rejection_cases
        )

    assert _backend_acceptance_case_ids(PayloadBackend.DATACLASSES, "all") == _backend_acceptance_case_ids(
        PayloadBackend.DATACLASSES,
        "representative",
    )


@pytest.mark.parametrize("case", PYDANTIC_V2_ACCEPTANCE_CASES)
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


@pytest.mark.parametrize("case", PYDANTIC_V2_ROUND_TRIP_CASES)
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
def test_generated_pydantic_v2_model_dumps_schema_valid_payloads(
    case: SchemaCase,
    generated_model_cache: dict[str, Any],
    data: st.DataObject,
) -> None:
    """Payloads accepted by generated pydantic v2 code should dump back to source-valid JSON."""
    payload = data.draw(payload_strategy(case), label=f"{case.id}:round_trip")
    validate_with_source_schema(case, payload)
    adapter = load_generated_payload_adapter(case, generated_model_cache)
    validated_payload = adapter.validate_python(payload)
    dumped_payload = adapter.dump_python(validated_payload, mode="json", by_alias=True, exclude_unset=True)
    validate_with_source_schema(case, dumped_payload)


@pytest.mark.parametrize("case", PYDANTIC_V2_REJECTION_CASES)
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
    runtime.assert_rejects_python(mutation.payload)
