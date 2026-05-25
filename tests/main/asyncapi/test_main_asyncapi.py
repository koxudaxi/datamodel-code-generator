"""Tests for AsyncAPI input file code generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from datamodel_code_generator import InputFileType, inferred_message
from datamodel_code_generator.__main__ import Exit
from tests.main.asyncapi.conftest import assert_file_content
from tests.main.conftest import (
    ASYNC_API_DATA_PATH,
    run_generate_file_and_assert,
    run_main_and_assert,
)

PY310_TARGET_ARGS = ["--target-python-version", "3.10"]

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_main_asyncapi_2_yaml(output_file: Path) -> None:
    """Generate models from an AsyncAPI 2.x YAML document."""
    run_main_and_assert(
        input_path=ASYNC_API_DATA_PATH / "user-events.yaml",
        output_path=output_file,
        input_file_type="asyncapi",
        assert_func=assert_file_content,
        expected_file="user_events.py",
    )


def test_main_asyncapi_3_json(output_file: Path) -> None:
    """Generate models from an AsyncAPI 3.x JSON document."""
    run_main_and_assert(
        input_path=ASYNC_API_DATA_PATH / "order-events.json",
        output_path=output_file,
        input_file_type="asyncapi",
        assert_func=assert_file_content,
        expected_file="order_events.py",
    )


def test_main_asyncapi_auto_inference(output_file: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Infer AsyncAPI input type from the asyncapi field."""
    run_main_and_assert(
        input_path=ASYNC_API_DATA_PATH / "user-events.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="user_events.py",
        capsys=capsys,
        expected_stderr=inferred_message.format("asyncapi") + "\n",
    )


def test_generate_asyncapi(output_file: Path) -> None:
    """Generate models through the public generate() API."""
    run_generate_file_and_assert(
        input_path=ASYNC_API_DATA_PATH / "user-events.yaml",
        output_path=output_file,
        input_file_type=InputFileType.AsyncAPI,
        assert_func=assert_file_content,
        expected_file="user_events.py",
    )


def test_main_asyncapi_schema_version(output_file: Path) -> None:
    """Accept explicit AsyncAPI schema version selection."""
    run_main_and_assert(
        input_path=ASYNC_API_DATA_PATH / "order-events.json",
        output_path=output_file,
        input_file_type="asyncapi",
        assert_func=assert_file_content,
        expected_file="order_events.py",
        extra_args=["--schema-version", "3.0"],
        expected_exit=Exit.OK,
    )


def test_main_asyncapi_unknown_version_falls_back_to_v3(output_file: Path) -> None:
    """Treat unknown AsyncAPI versions as v3-compatible when validation is not requested."""
    run_main_and_assert(
        input_path=ASYNC_API_DATA_PATH / "unknown-version.yaml",
        output_path=output_file,
        input_file_type="asyncapi",
        assert_func=assert_file_content,
        expected_file="unknown_version.py",
        extra_args=[*PY310_TARGET_ARGS, "--schema-version-mode", "strict"],
    )


def test_main_asyncapi_edge_cases(output_file: Path) -> None:
    """Generate models for AsyncAPI schema/reference edge cases through the CLI."""
    run_main_and_assert(
        input_path=ASYNC_API_DATA_PATH / "edge-cases.yaml",
        output_path=output_file,
        input_file_type="asyncapi",
        assert_func=assert_file_content,
        expected_file="edge_cases.py",
        extra_args=PY310_TARGET_ARGS,
    )


def test_main_asyncapi_non_object_components(output_file: Path) -> None:
    """Ignore invalid component containers while still generating channel payloads."""
    run_main_and_assert(
        input_path=ASYNC_API_DATA_PATH / "non-object-components.yaml",
        output_path=output_file,
        input_file_type="asyncapi",
        assert_func=assert_file_content,
        expected_file="non_object_components.py",
        extra_args=PY310_TARGET_ARGS,
    )


def test_main_asyncapi_external_message_ref(output_file: Path) -> None:
    """Resolve external message refs using the referenced document context."""
    run_main_and_assert(
        input_path=ASYNC_API_DATA_PATH / "external-message-ref.yaml",
        output_path=output_file,
        input_file_type="asyncapi",
        assert_func=assert_file_content,
        expected_file="external_message_ref.py",
        extra_args=PY310_TARGET_ARGS,
    )


def test_main_asyncapi_validation_flag(output_file: Path) -> None:
    """Keep validation non-goal explicit while still generating models."""
    run_main_and_assert(
        input_path=ASYNC_API_DATA_PATH / "user-events.yaml",
        output_path=output_file,
        input_file_type="asyncapi",
        assert_func=assert_file_content,
        expected_file="user_events.py",
        extra_args=["--validation"],
    )


def test_main_asyncapi_invalid_schema_version(output_file: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Reject unknown explicit AsyncAPI schema versions through the CLI."""
    run_main_and_assert(
        input_path=ASYNC_API_DATA_PATH / "user-events.yaml",
        output_path=output_file,
        input_file_type="asyncapi",
        extra_args=["--schema-version", "invalid-version"],
        expected_exit=Exit.ERROR,
        expected_stderr_contains="Invalid AsyncAPI version: invalid-version",
        capsys=capsys,
    )
