"""Validate generated Pydantic v2 models with schema-derived payloads."""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from .payload_validation import (
    SCHEMA_CASES,
    GeneratedModelCache,
    SchemaCase,
    discover_unaccounted_files,
    load_generated_payload_adapter,
    payload_strategy,
    validate_with_source_schema,
)

_MAX_EXAMPLES = 10


@pytest.fixture(scope="session")
def generated_model_cache(tmp_path_factory: pytest.TempPathFactory) -> GeneratedModelCache:
    """Cache generated Payload adapters across Hypothesis examples."""
    return GeneratedModelCache({"base": tmp_path_factory.mktemp("payload_validation"), "adapters": {}})


def test_payload_validation_cases_cover_discovered_schema_files() -> None:
    """Every discovered schema fixture must be validated or explicitly excluded."""
    unaccounted = discover_unaccounted_files(SCHEMA_CASES)
    if unaccounted:  # pragma: no cover
        pytest.fail(
            "Schema files must be covered by payload validation or added to _EXCLUDED_FILES with a reason:\n"
            + "\n".join(unaccounted)
        )


@pytest.mark.parametrize("case", SCHEMA_CASES, ids=lambda case: case.id)
@settings(
    database=None,
    deadline=None,
    derandomize=True,
    max_examples=_MAX_EXAMPLES,
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
