"""Tests for --input-model option."""

from __future__ import annotations

import sys
from argparse import Namespace
from textwrap import dedent
from typing import TYPE_CHECKING

import pydantic
import pytest

from datamodel_code_generator import __main__ as main_module
from datamodel_code_generator import arguments
from datamodel_code_generator.__main__ import Exit, main

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence
    from pathlib import Path

SKIP_PYDANTIC_V1 = pytest.mark.skipif(
    pydantic.VERSION < "2.0.0",
    reason="--input-model with Pydantic models requires Pydantic v2",
)


def _assert_exit_code(return_code: Exit, expected_exit: Exit, context: str) -> None:
    """Assert exit code matches expected value."""
    __tracebackhide__ = True
    if return_code != expected_exit:  # pragma: no cover
        pytest.fail(f"Expected exit code {expected_exit!r}, got {return_code!r}\n{context}")


def _assert_stderr_contains(captured_err: str, expected: str) -> None:
    """Assert stderr contains expected string."""
    __tracebackhide__ = True
    if expected not in captured_err:  # pragma: no cover
        pytest.fail(f"Expected stderr to contain: {expected!r}\n\nActual stderr:\n{captured_err}")


def _assert_output_contains(content: str, expected: str) -> None:
    """Assert output contains expected string."""
    __tracebackhide__ = True
    if expected not in content:  # pragma: no cover
        pytest.fail(f"Expected output to contain: {expected!r}\n\nActual output:\n{content}")


def _assert_file_exists(path: Path) -> None:
    """Assert file exists."""
    __tracebackhide__ = True
    if not path.exists():  # pragma: no cover
        pytest.fail(f"Expected file to exist: {path}")


def run_input_model_and_assert(
    *,
    input_model: str,
    output_path: Path,
    extra_args: Sequence[str] | None = None,
    expected_exit: Exit = Exit.OK,
    expected_output_contains: Sequence[str] | None = None,
) -> None:
    """Run main with --input-model and assert results."""
    __tracebackhide__ = True
    args = ["--input-model", input_model, "--output", str(output_path)]
    if extra_args:
        args.extend(extra_args)

    return_code = main(args)
    _assert_exit_code(return_code, expected_exit, f"--input-model {input_model}")
    _assert_file_exists(output_path)

    if expected_output_contains:
        content = output_path.read_text(encoding="utf-8")
        for expected in expected_output_contains:
            _assert_output_contains(content, expected)


def run_input_model_error_and_assert(
    *,
    input_model: str,
    extra_args: Sequence[str] | None = None,
    capsys: pytest.CaptureFixture[str],
    expected_stderr_contains: str,
) -> None:
    """Run main with --input-model expecting error and assert stderr."""
    __tracebackhide__ = True
    args = ["--input-model", input_model]
    if extra_args:
        args.extend(extra_args)

    return_code = main(args)
    _assert_exit_code(return_code, Exit.ERROR, f"--input-model {input_model}")
    captured = capsys.readouterr()
    _assert_stderr_contains(captured.err, expected_stderr_contains)


@pytest.fixture(autouse=True)
def reset_namespace(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset the global namespace before each test."""
    new_namespace = Namespace(no_color=False)
    monkeypatch.setattr(arguments, "namespace", new_namespace)
    monkeypatch.setattr(main_module, "namespace", new_namespace)


@pytest.fixture
def pydantic_model_module(tmp_path: Path) -> Generator[str, None, None]:
    """Create a temporary module with a Pydantic model."""
    module_file = tmp_path / "test_pydantic_models.py"
    module_file.write_text(
        dedent("""
        from pydantic import BaseModel


        class UserModel(BaseModel):
            name: str
            age: int
    """)
    )
    sys.path.insert(0, str(tmp_path))
    try:
        yield "test_pydantic_models:UserModel"
    finally:
        sys.path.remove(str(tmp_path))
        sys.modules.pop("test_pydantic_models", None)


@pytest.fixture
def dict_schema_module(tmp_path: Path) -> Generator[str, None, None]:
    """Create a temporary module with a dict schema."""
    module_file = tmp_path / "test_dict_schema.py"
    module_file.write_text(
        dedent("""
        USER_SCHEMA = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"}
            }
        }
    """)
    )
    sys.path.insert(0, str(tmp_path))
    try:
        yield "test_dict_schema:USER_SCHEMA"
    finally:
        sys.path.remove(str(tmp_path))
        sys.modules.pop("test_dict_schema", None)


@pytest.fixture
def openapi_dict_module(tmp_path: Path) -> Generator[str, None, None]:
    """Create a temporary module with an OpenAPI spec dict."""
    module_file = tmp_path / "test_openapi_spec.py"
    module_file.write_text(
        dedent("""
        OPENAPI_SPEC = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0"},
            "paths": {},
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}}
                    }
                }
            }
        }
    """)
    )
    sys.path.insert(0, str(tmp_path))
    try:
        yield "test_openapi_spec:OPENAPI_SPEC"
    finally:
        sys.path.remove(str(tmp_path))
        sys.modules.pop("test_openapi_spec", None)


# =============================================================================
# Pydantic Model Tests
# =============================================================================


@SKIP_PYDANTIC_V1
@pytest.mark.cli_doc(
    options=["--input-model"],
    cli_args=["--input-model", "mymodule:MyModel"],
    input_model="mymodule:MyModel",
    expected_stdout="",
)
def test_input_model_pydantic_basic(
    pydantic_model_module: str,
    tmp_path: Path,
) -> None:
    """Import a Pydantic v2 model or dict schema from a Python module."""
    run_input_model_and_assert(
        input_model=pydantic_model_module,
        output_path=tmp_path / "output.py",
        expected_output_contains=["name", "age"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_pydantic_to_typeddict(
    pydantic_model_module: str,
    tmp_path: Path,
) -> None:
    """Test generating TypedDict from Pydantic model."""
    run_input_model_and_assert(
        input_model=pydantic_model_module,
        output_path=tmp_path / "output.py",
        extra_args=["--output-model-type", "typing.TypedDict"],
        expected_output_contains=["TypedDict"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_pydantic_with_jsonschema_type(
    pydantic_model_module: str,
    tmp_path: Path,
) -> None:
    """Test --input-model with explicit jsonschema input-file-type."""
    run_input_model_and_assert(
        input_model=pydantic_model_module,
        output_path=tmp_path / "output.py",
        extra_args=["--input-file-type", "jsonschema"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_pydantic_non_jsonschema_error(
    pydantic_model_module: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test error when Pydantic model used with non-jsonschema input-file-type."""
    run_input_model_error_and_assert(
        input_model=pydantic_model_module,
        extra_args=["--input-file-type", "openapi", "--output", str(tmp_path / "output.py")],
        capsys=capsys,
        expected_stderr_contains="--input-file-type must be 'jsonschema'",
    )


# =============================================================================
# Dict Schema Tests
# =============================================================================


def test_input_model_dict_with_jsonschema(
    dict_schema_module: str,
    tmp_path: Path,
) -> None:
    """Test dict input with --input-file-type jsonschema."""
    run_input_model_and_assert(
        input_model=dict_schema_module,
        output_path=tmp_path / "output.py",
        extra_args=["--input-file-type", "jsonschema"],
    )


def test_input_model_dict_without_type_error(
    dict_schema_module: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that dict without --input-file-type raises error."""
    run_input_model_error_and_assert(
        input_model=dict_schema_module,
        extra_args=["--output", str(tmp_path / "output.py")],
        capsys=capsys,
        expected_stderr_contains="--input-file-type is required",
    )


def test_input_model_dict_openapi(
    openapi_dict_module: str,
    tmp_path: Path,
) -> None:
    """Test dict input as OpenAPI spec."""
    run_input_model_and_assert(
        input_model=openapi_dict_module,
        output_path=tmp_path / "output.py",
        extra_args=["--input-file-type", "openapi"],
        expected_output_contains=["User"],
    )


# =============================================================================
# Error Handling Tests
# =============================================================================


def test_input_model_invalid_format(capsys: pytest.CaptureFixture[str]) -> None:
    """Test error when colon is missing."""
    run_input_model_error_and_assert(
        input_model="pydantic.BaseModel",
        capsys=capsys,
        expected_stderr_contains="Invalid --input-model format",
    )


def test_input_model_invalid_module(capsys: pytest.CaptureFixture[str]) -> None:
    """Test error when module doesn't exist."""
    run_input_model_error_and_assert(
        input_model="nonexistent_module_12345:Model",
        capsys=capsys,
        expected_stderr_contains="Cannot import module",
    )


def test_input_model_invalid_attr(capsys: pytest.CaptureFixture[str]) -> None:
    """Test error when class doesn't exist in module."""
    run_input_model_error_and_assert(
        input_model="pydantic:NonexistentClass12345",
        capsys=capsys,
        expected_stderr_contains="has no attribute",
    )


def test_input_model_unsupported_type(capsys: pytest.CaptureFixture[str]) -> None:
    """Test error when object is not a Pydantic model or dict."""
    run_input_model_error_and_assert(
        input_model="pathlib:Path",
        capsys=capsys,
        expected_stderr_contains="is not a supported type",
    )


@SKIP_PYDANTIC_V1
def test_input_model_pydantic_v1_error(
    pydantic_model_module: str,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test error when Pydantic v1 model is used."""
    import builtins

    import test_pydantic_models

    original_hasattr = builtins.hasattr

    def mock_hasattr(obj: object, name: str) -> bool:
        if name == "model_json_schema" and obj is test_pydantic_models.UserModel:
            return False
        return original_hasattr(obj, name)

    monkeypatch.setattr(builtins, "hasattr", mock_hasattr)

    run_input_model_error_and_assert(
        input_model=pydantic_model_module,
        capsys=capsys,
        expected_stderr_contains="requires Pydantic v2 runtime",
    )


# =============================================================================
# Mutual Exclusion Tests
# =============================================================================


@SKIP_PYDANTIC_V1
def test_input_model_mutual_exclusion_with_input(
    pydantic_model_module: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test --input-model cannot be used with --input."""
    run_input_model_error_and_assert(
        input_model=pydantic_model_module,
        extra_args=["--input", str(tmp_path / "schema.json")],
        capsys=capsys,
        expected_stderr_contains="--input-model cannot be used with --input or --url",
    )


@SKIP_PYDANTIC_V1
def test_input_model_mutual_exclusion_with_url(
    pydantic_model_module: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test --input-model cannot be used with --url."""
    run_input_model_error_and_assert(
        input_model=pydantic_model_module,
        extra_args=["--url", "https://example.com/schema.json"],
        capsys=capsys,
        expected_stderr_contains="--input-model cannot be used with --input or --url",
    )


@SKIP_PYDANTIC_V1
def test_input_model_mutual_exclusion_with_watch(
    pydantic_model_module: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test --input-model cannot be used with --watch."""
    run_input_model_error_and_assert(
        input_model=pydantic_model_module,
        extra_args=["--watch", "--output", str(tmp_path / "output.py")],
        capsys=capsys,
        expected_stderr_contains="--watch cannot be used with --input-model",
    )
