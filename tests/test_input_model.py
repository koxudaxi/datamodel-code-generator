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
from tests.main.conftest import run_main_with_args

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

SKIP_PYDANTIC_V1 = pytest.mark.skipif(
    pydantic.VERSION < "2.0.0",
    reason="--input-model with Pydantic models requires Pydantic v2",
)


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
    output_file = tmp_path / "output.py"
    run_main_with_args(
        ["--input-model", pydantic_model_module, "--output", str(output_file)],
        expected_exit=Exit.OK,
    )
    content = output_file.read_text()
    assert "name" in content
    assert "age" in content


@SKIP_PYDANTIC_V1
def test_input_model_pydantic_to_typeddict(
    pydantic_model_module: str,
    tmp_path: Path,
) -> None:
    """Test generating TypedDict from Pydantic model."""
    output_file = tmp_path / "output.py"
    run_main_with_args(
        [
            "--input-model",
            pydantic_model_module,
            "--output-model-type",
            "typing.TypedDict",
            "--output",
            str(output_file),
        ],
        expected_exit=Exit.OK,
    )
    content = output_file.read_text()
    assert "TypedDict" in content


@SKIP_PYDANTIC_V1
def test_input_model_pydantic_with_jsonschema_type(
    pydantic_model_module: str,
    tmp_path: Path,
) -> None:
    """Test --input-model with explicit jsonschema input-file-type."""
    output_file = tmp_path / "output.py"
    run_main_with_args(
        [
            "--input-model",
            pydantic_model_module,
            "--input-file-type",
            "jsonschema",
            "--output",
            str(output_file),
        ],
        expected_exit=Exit.OK,
    )
    assert output_file.exists()


@SKIP_PYDANTIC_V1
def test_input_model_pydantic_non_jsonschema_error(
    pydantic_model_module: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test error when Pydantic model used with non-jsonschema input-file-type."""
    output_file = tmp_path / "output.py"
    return_code = main([
        "--input-model",
        pydantic_model_module,
        "--input-file-type",
        "openapi",
        "--output",
        str(output_file),
    ])
    assert return_code == Exit.ERROR
    captured = capsys.readouterr()
    assert "--input-file-type must be 'jsonschema'" in captured.err


# =============================================================================
# Dict Schema Tests
# =============================================================================


def test_input_model_dict_with_jsonschema(
    dict_schema_module: str,
    tmp_path: Path,
) -> None:
    """Test dict input with --input-file-type jsonschema."""
    output_file = tmp_path / "output.py"
    run_main_with_args(
        [
            "--input-model",
            dict_schema_module,
            "--input-file-type",
            "jsonschema",
            "--output",
            str(output_file),
        ],
        expected_exit=Exit.OK,
    )
    assert output_file.exists()


def test_input_model_dict_without_type_error(
    dict_schema_module: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that dict without --input-file-type raises error."""
    output_file = tmp_path / "output.py"
    return_code = main([
        "--input-model",
        dict_schema_module,
        "--output",
        str(output_file),
    ])
    assert return_code == Exit.ERROR
    captured = capsys.readouterr()
    assert "--input-file-type is required" in captured.err


def test_input_model_dict_openapi(
    openapi_dict_module: str,
    tmp_path: Path,
) -> None:
    """Test dict input as OpenAPI spec."""
    output_file = tmp_path / "output.py"
    run_main_with_args(
        [
            "--input-model",
            openapi_dict_module,
            "--input-file-type",
            "openapi",
            "--output",
            str(output_file),
        ],
        expected_exit=Exit.OK,
    )
    content = output_file.read_text()
    assert "User" in content


# =============================================================================
# Error Handling Tests
# =============================================================================


def test_input_model_invalid_format(capsys: pytest.CaptureFixture[str]) -> None:
    """Test error when colon is missing."""
    return_code = main(["--input-model", "pydantic.BaseModel"])
    assert return_code == Exit.ERROR
    captured = capsys.readouterr()
    assert "Invalid --input-model format" in captured.err


def test_input_model_invalid_module(capsys: pytest.CaptureFixture[str]) -> None:
    """Test error when module doesn't exist."""
    return_code = main(["--input-model", "nonexistent_module_12345:Model"])
    assert return_code == Exit.ERROR
    captured = capsys.readouterr()
    assert "Cannot import module" in captured.err


def test_input_model_invalid_attr(capsys: pytest.CaptureFixture[str]) -> None:
    """Test error when class doesn't exist in module."""
    return_code = main(["--input-model", "pydantic:NonexistentClass12345"])
    assert return_code == Exit.ERROR
    captured = capsys.readouterr()
    assert "has no attribute" in captured.err


def test_input_model_unsupported_type(capsys: pytest.CaptureFixture[str]) -> None:
    """Test error when object is not a Pydantic model or dict."""
    return_code = main(["--input-model", "pathlib:Path"])
    assert return_code == Exit.ERROR
    captured = capsys.readouterr()
    assert "is not a supported type" in captured.err


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

    return_code = main(["--input-model", pydantic_model_module])
    assert return_code == Exit.ERROR
    captured = capsys.readouterr()
    assert "requires Pydantic v2 model" in captured.err


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
    return_code = main([
        "--input-model",
        pydantic_model_module,
        "--input",
        str(tmp_path / "schema.json"),
    ])
    assert return_code == Exit.ERROR
    captured = capsys.readouterr()
    assert "--input-model cannot be used with --input or --url" in captured.err


@SKIP_PYDANTIC_V1
def test_input_model_mutual_exclusion_with_url(
    pydantic_model_module: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test --input-model cannot be used with --url."""
    return_code = main([
        "--input-model",
        pydantic_model_module,
        "--url",
        "https://example.com/schema.json",
    ])
    assert return_code == Exit.ERROR
    captured = capsys.readouterr()
    assert "--input-model cannot be used with --input or --url" in captured.err


@SKIP_PYDANTIC_V1
def test_input_model_mutual_exclusion_with_watch(
    pydantic_model_module: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test --input-model cannot be used with --watch."""
    return_code = main([
        "--input-model",
        pydantic_model_module,
        "--watch",
        "--output",
        str(tmp_path / "output.py"),
    ])
    assert return_code == Exit.ERROR
    captured = capsys.readouterr()
    assert "--watch cannot be used with --input-model" in captured.err
