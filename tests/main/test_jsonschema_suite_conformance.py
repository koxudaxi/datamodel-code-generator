"""Validate generated Pydantic v2 models against JSON-Schema-Test-Suite."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

from .payload_validation import GeneratedModelCache
from .payload_validation.json_schema_suite import (
    EXPECTED_JSON_SCHEMA_SUITE_GROUP_COUNTS,
    EXPECTED_JSON_SCHEMA_SUITE_TEST_COUNTS,
    JSON_SCHEMA_TEST_SUITE_COMMIT,
    JsonSchemaSuiteCase,
    evaluate_json_schema_suite_cases,
    explicit_json_schema_suite_exclusions,
    format_json_schema_suite_failures,
    iter_json_schema_suite_cases,
    json_schema_suite_case_counts,
)


@pytest.fixture(scope="session")
def json_schema_suite_root() -> Path:
    """Return the configured JSON-Schema-Test-Suite checkout path."""
    if not (raw_path := os.environ.get("JSON_SCHEMA_TEST_SUITE_PATH")):
        pytest.skip("JSON_SCHEMA_TEST_SUITE_PATH is required for JSON-Schema-Test-Suite conformance")
    suite_root = Path(raw_path)
    if not suite_root.is_dir():  # pragma: no cover
        pytest.fail(f"JSON-Schema-Test-Suite checkout does not exist: {suite_root}")
    return suite_root


@pytest.fixture(scope="session")
def json_schema_suite_cases(json_schema_suite_root: Path) -> list[JsonSchemaSuiteCase]:
    """Load target draft cases from JSON-Schema-Test-Suite."""
    return list(iter_json_schema_suite_cases(json_schema_suite_root))


@pytest.fixture(scope="session")
def generated_model_cache(tmp_path_factory: pytest.TempPathFactory) -> GeneratedModelCache:
    """Cache generated Payload adapters across suite cases."""
    return GeneratedModelCache({"base": tmp_path_factory.mktemp("json_schema_suite"), "adapters": {}})


def test_json_schema_suite_cases_match_pinned_counts(
    json_schema_suite_cases: list[JsonSchemaSuiteCase],
) -> None:
    """The pinned suite checkout must expose the expected target draft case counts."""
    group_counts, test_counts = json_schema_suite_case_counts(json_schema_suite_cases)
    if group_counts != EXPECTED_JSON_SCHEMA_SUITE_GROUP_COUNTS:  # pragma: no cover
        pytest.fail(
            f"Expected JSON-Schema-Test-Suite commit {JSON_SCHEMA_TEST_SUITE_COMMIT} group counts "
            f"{EXPECTED_JSON_SCHEMA_SUITE_GROUP_COUNTS}, got {dict(group_counts)}"
        )
    if test_counts != EXPECTED_JSON_SCHEMA_SUITE_TEST_COUNTS:  # pragma: no cover
        pytest.fail(
            f"Expected JSON-Schema-Test-Suite commit {JSON_SCHEMA_TEST_SUITE_COMMIT} test counts "
            f"{EXPECTED_JSON_SCHEMA_SUITE_TEST_COUNTS}, got {dict(test_counts)}"
        )


def test_json_schema_suite_exclusions_have_reasons() -> None:
    """Every hand-classified suite exclusion must carry an explanatory reason."""
    missing_reasons = [case_id for case_id, reason in explicit_json_schema_suite_exclusions().items() if not reason]
    if missing_reasons:  # pragma: no cover
        pytest.fail("JSON-Schema-Test-Suite exclusions require reasons:\n" + "\n".join(missing_reasons))


def test_generated_pydantic_v2_models_match_json_schema_test_suite(
    json_schema_suite_cases: list[JsonSchemaSuiteCase],
    generated_model_cache: dict[str, Any],
) -> None:
    """Generated models should accept/reject instances like JSON-Schema-Test-Suite expects."""
    report = evaluate_json_schema_suite_cases(json_schema_suite_cases, generated_model_cache)
    explicit_exclusions = explicit_json_schema_suite_exclusions()
    unused_exclusions = sorted(set(explicit_exclusions) - set(report.excluded))
    if report.failures or unused_exclusions:  # pragma: no cover
        message_parts: list[str] = []
        if report.failures:
            message_parts.append(
                "Unclassified JSON-Schema-Test-Suite conformance mismatches:\n"
                + format_json_schema_suite_failures(report.failures)
            )
        if unused_exclusions:
            message_parts.append("Unused JSON-Schema-Test-Suite exclusions:\n" + "\n".join(unused_exclusions))
        pytest.fail("\n\n".join(message_parts))
