"""Regression tests for malformed CLI input diagnostics."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from datamodel_code_generator.__main__ import Exit
from tests.main.conftest import DATA_PATH, InputFileTypeLiteral, run_main_and_assert

if TYPE_CHECKING:
    from pathlib import Path


MALFORMED_DATA_PATH = DATA_PATH / "malformed"
TRACEBACK_HEADER = "Traceback (most recent call last)"

ERROR_CASES: tuple[tuple[str, InputFileTypeLiteral, str], ...] = (
    ("truncated_jsonschema.json", "jsonschema", TRACEBACK_HEADER),
    ("bad_openapi.yaml", "openapi", TRACEBACK_HEADER),
    ("bad.graphql", "graphql", TRACEBACK_HEADER),
    ("non_dict_root.yaml", "openapi", TRACEBACK_HEADER),
    ("pointer_through_scalar_openapi.yaml", "openapi", TRACEBACK_HEADER),
    (
        "pointer_through_scalar.json",
        "jsonschema",
        "Error at schema path 'pointer_through_scalar.json/#/definitions/Name': ValidationError",
    ),
    ("wrong_type_properties.json", "jsonschema", "Error at schema path 'wrong_type_properties.json'"),
    ("required_as_string.json", "jsonschema", "Error at schema path 'required_as_string.json'"),
    ("enum_as_dict.json", "jsonschema", "Error at schema path 'enum_as_dict.json'"),
    ("missing_external_ref.json", "jsonschema", "$ref file not found:"),
    ("empty_jsonschema.json", "jsonschema", "Models not found in the input data"),
)

MISSING_INPUT_CASES: tuple[tuple[InputFileTypeLiteral | None, str], ...] = (
    (None, "File not found"),
    ("jsonschema", TRACEBACK_HEADER),
)

TOLERATED_CASES: tuple[tuple[str, InputFileTypeLiteral], ...] = (("dangling_local_ref.json", "jsonschema"),)


def _input_file_type_id(input_file_type: InputFileTypeLiteral | None) -> str:
    match input_file_type:
        case None:
            return "auto"
        case input_type:
            return input_type


@pytest.mark.parametrize(
    ("fixture_name", "input_file_type", "expected_stderr_contains"),
    ERROR_CASES,
    ids=[fixture_name for fixture_name, _, _ in ERROR_CASES],
)
def test_malformed_input_error_messages(
    fixture_name: str,
    input_file_type: InputFileTypeLiteral,
    expected_stderr_contains: str,
    output_file: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Malformed inputs keep their current stderr signal and non-zero exit code."""
    run_main_and_assert(
        input_path=MALFORMED_DATA_PATH / fixture_name,
        output_path=output_file,
        input_file_type=input_file_type,
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains=expected_stderr_contains,
        output_should_not_exist=True,
    )


@pytest.mark.parametrize(
    ("input_file_type", "expected_stderr_contains"),
    MISSING_INPUT_CASES,
    ids=[_input_file_type_id(input_file_type) for input_file_type, _ in MISSING_INPUT_CASES],
)
def test_missing_input_error_messages(
    input_file_type: InputFileTypeLiteral | None,
    expected_stderr_contains: str,
    output_file: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Missing local input paths keep their current CLI diagnostics."""
    run_main_and_assert(
        input_path=MALFORMED_DATA_PATH / "missing.json",
        output_path=output_file,
        input_file_type=input_file_type,
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains=expected_stderr_contains,
        output_should_not_exist=True,
    )


@pytest.mark.parametrize(
    ("fixture_name", "input_file_type"),
    TOLERATED_CASES,
    ids=[fixture_name for fixture_name, _ in TOLERATED_CASES],
)
def test_malformed_input_tolerated_behavior(
    fixture_name: str,
    input_file_type: InputFileTypeLiteral,
    output_file: Path,
) -> None:
    """Document malformed inputs that are intentionally tolerated until stricter diagnostics exist."""
    run_main_and_assert(
        input_path=MALFORMED_DATA_PATH / fixture_name,
        output_path=output_file,
        input_file_type=input_file_type,
        expected_exit=Exit.OK,
    )
