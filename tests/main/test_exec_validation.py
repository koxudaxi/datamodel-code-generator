"""Tests that validate generated code execution on the current Python version.

These tests specifically target the current Python runtime to catch runtime errors
that may not be caught when --target-python-version differs from the test environment.

See: _should_skip_exec() in conftest.py for the skip logic that these tests bypass.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest

from datamodel_code_generator.format import PythonVersion, is_supported_in_black
from datamodel_code_generator.util import is_pydantic_v2

from .conftest import (
    CURRENT_PYTHON_VERSION,
    JSON_SCHEMA_DATA_PATH,
    OPEN_API_DATA_PATH,
    get_current_version_args,
    run_main_and_assert,
)

if TYPE_CHECKING:
    from pathlib import Path

_CURRENT_PY_VERSION = PythonVersion(CURRENT_PYTHON_VERSION)
_SKIP_PYDANTIC = pytest.mark.skipif(not is_pydantic_v2(), reason="Pydantic v2 required")
_SKIP_BLACK = pytest.mark.skipif(
    not is_supported_in_black(_CURRENT_PY_VERSION),
    reason=f"Installed black doesn't support Python {CURRENT_PYTHON_VERSION}",
)


@_SKIP_PYDANTIC
@_SKIP_BLACK
def test_openapi_api_exec_current_version(output_file: Path) -> None:
    """Test that api.yaml schema generates executable code on current Python."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        extra_args=get_current_version_args("--output-model-type", "pydantic_v2.BaseModel"),
        skip_code_validation=False,
        force_exec_validation=True,
    )


@_SKIP_PYDANTIC
@_SKIP_BLACK
def test_openapi_with_refs_exec_current_version(output_file: Path) -> None:
    """Test that OpenAPI schema with $ref generates executable code."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "body_and_parameters.yaml",
        output_path=output_file,
        extra_args=get_current_version_args("--output-model-type", "pydantic_v2.BaseModel"),
        skip_code_validation=False,
        force_exec_validation=True,
    )


@_SKIP_PYDANTIC
@_SKIP_BLACK
def test_openapi_allof_exec_current_version(output_file: Path) -> None:
    """Test that OpenAPI schema with allOf generates executable code."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "allof.yaml",
        output_path=output_file,
        extra_args=get_current_version_args("--output-model-type", "pydantic_v2.BaseModel"),
        skip_code_validation=False,
        force_exec_validation=True,
    )


@_SKIP_PYDANTIC
@_SKIP_BLACK
def test_jsonschema_person_exec_current_version(output_file: Path) -> None:
    """Test that person.json schema generates executable code on current Python."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "person.json",
        output_path=output_file,
        extra_args=get_current_version_args("--output-model-type", "pydantic_v2.BaseModel"),
        skip_code_validation=False,
        force_exec_validation=True,
    )


@_SKIP_PYDANTIC
@_SKIP_BLACK
def test_jsonschema_nested_array_exec_current_version(output_file: Path) -> None:
    """Test that nested array JSON Schema generates executable code."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "nested_array.json",
        output_path=output_file,
        extra_args=get_current_version_args("--output-model-type", "pydantic_v2.BaseModel"),
        skip_code_validation=False,
        force_exec_validation=True,
    )


@_SKIP_PYDANTIC
@_SKIP_BLACK
def test_jsonschema_circular_reference_exec_current_version(output_file: Path) -> None:
    """Test that circular reference JSON Schema generates executable code."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "circular_reference.json",
        output_path=output_file,
        extra_args=get_current_version_args("--output-model-type", "pydantic_v2.BaseModel"),
        skip_code_validation=False,
        force_exec_validation=True,
    )


@_SKIP_PYDANTIC
@_SKIP_BLACK
@pytest.mark.skipif(
    sys.version_info[:2] <= (3, 10),
    reason="Need runtime > target (3.10) to test force_exec_validation behavior",
)
def test_force_exec_with_different_target_version(output_file: Path) -> None:
    """Test that force_exec_validation runs exec even with different target version.

    This test uses --target-python-version 3.10 but force_exec_validation=True
    to verify that exec still runs on the current Python version.

    Requirements for this test to be meaningful:
    - Runtime must be > 3.10 (so target < runtime, allowing compile to proceed)
    - This ensures force_exec_validation can bypass the version mismatch skip
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "person.json",
        output_path=output_file,
        extra_args=["--target-python-version", "3.10", "--output-model-type", "pydantic_v2.BaseModel"],
        skip_code_validation=False,
        force_exec_validation=True,
    )


def test_get_current_version_args_basic() -> None:
    """Test that get_current_version_args returns correct args."""
    args = get_current_version_args()
    assert args == ["--target-python-version", CURRENT_PYTHON_VERSION]


def test_get_current_version_args_with_extra() -> None:
    """Test that get_current_version_args includes extra args."""
    args = get_current_version_args("--use-field-description", "--strict")
    assert args == [
        "--target-python-version",
        CURRENT_PYTHON_VERSION,
        "--use-field-description",
        "--strict",
    ]


def test_current_python_version_format() -> None:
    """Test that CURRENT_PYTHON_VERSION matches expected format."""
    expected = f"{sys.version_info[0]}.{sys.version_info[1]}"
    assert expected == CURRENT_PYTHON_VERSION
