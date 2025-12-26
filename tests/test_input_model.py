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
def pydantic_model_module(tmp_path: Path) -> Path:
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
    return tmp_path


@SKIP_PYDANTIC_V1
class TestInputModelPydantic:
    """Tests for --input-model with Pydantic models."""

    def test_basic_usage(self, pydantic_model_module: Path, tmp_path: Path) -> None:
        """Test basic --input-model usage with Pydantic BaseModel."""
        output_file = tmp_path / "output.py"

        sys.path.insert(0, str(pydantic_model_module))
        try:
            exit_code = main([
                "--ignore-pyproject",
                "--input-model",
                "test_pydantic_models:UserModel",
                "--output",
                str(output_file),
            ])
        finally:
            sys.path.remove(str(pydantic_model_module))
            sys.modules.pop("test_pydantic_models", None)

        assert exit_code == Exit.OK
        assert output_file.exists()
        content = output_file.read_text()
        assert "name" in content
        assert "age" in content

    def test_output_to_typeddict(self, pydantic_model_module: Path, tmp_path: Path) -> None:
        """Test generating TypedDict from Pydantic model."""
        output_file = tmp_path / "output.py"

        sys.path.insert(0, str(pydantic_model_module))
        try:
            exit_code = main([
                "--ignore-pyproject",
                "--input-model",
                "test_pydantic_models:UserModel",
                "--output-model-type",
                "typing.TypedDict",
                "--output",
                str(output_file),
            ])
        finally:
            sys.path.remove(str(pydantic_model_module))
            sys.modules.pop("test_pydantic_models", None)

        assert exit_code == Exit.OK
        content = output_file.read_text()
        assert "TypedDict" in content

    def test_with_jsonschema_input_file_type(self, pydantic_model_module: Path, tmp_path: Path) -> None:
        """Test --input-model with explicit jsonschema input-file-type."""
        output_file = tmp_path / "output.py"

        sys.path.insert(0, str(pydantic_model_module))
        try:
            exit_code = main([
                "--ignore-pyproject",
                "--input-model",
                "test_pydantic_models:UserModel",
                "--input-file-type",
                "jsonschema",
                "--output",
                str(output_file),
            ])
        finally:
            sys.path.remove(str(pydantic_model_module))
            sys.modules.pop("test_pydantic_models", None)

        assert exit_code == Exit.OK
        assert output_file.exists()

    def test_with_non_jsonschema_input_file_type_error(
        self,
        pydantic_model_module: Path,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test error when Pydantic model used with non-jsonschema input-file-type."""
        output_file = tmp_path / "output.py"

        sys.path.insert(0, str(pydantic_model_module))
        try:
            exit_code = main([
                "--ignore-pyproject",
                "--input-model",
                "test_pydantic_models:UserModel",
                "--input-file-type",
                "openapi",
                "--output",
                str(output_file),
            ])
        finally:
            sys.path.remove(str(pydantic_model_module))
            sys.modules.pop("test_pydantic_models", None)

        assert exit_code == Exit.ERROR
        captured = capsys.readouterr()
        assert "--input-file-type must be 'jsonschema'" in captured.err


class TestInputModelDict:
    """Tests for --input-model with dict."""

    def test_dict_with_input_file_type(self, tmp_path: Path) -> None:
        """Test dict input with --input-file-type specified."""
        import importlib
        import uuid

        module_name = f"test_schemas_{uuid.uuid4().hex[:8]}"
        test_module = tmp_path / f"{module_name}.py"
        test_module.write_text(
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

        output_file = tmp_path / "output.py"

        sys.path.insert(0, str(tmp_path))
        importlib.invalidate_caches()
        try:
            exit_code = main([
                "--ignore-pyproject",
                "--input-model",
                f"{module_name}:USER_SCHEMA",
                "--input-file-type",
                "jsonschema",
                "--output",
                str(output_file),
            ])
        finally:
            sys.path.remove(str(tmp_path))
            if module_name in sys.modules:
                del sys.modules[module_name]

        assert exit_code == Exit.OK
        assert output_file.exists()

    def test_dict_without_input_file_type_error(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that dict without --input-file-type raises error."""
        import importlib
        import uuid

        module_name = f"test_schemas_{uuid.uuid4().hex[:8]}"
        test_module = tmp_path / f"{module_name}.py"
        test_module.write_text('SCHEMA = {"type": "object"}')

        output_file = tmp_path / "output.py"

        sys.path.insert(0, str(tmp_path))
        importlib.invalidate_caches()
        try:
            exit_code = main([
                "--ignore-pyproject",
                "--input-model",
                f"{module_name}:SCHEMA",
                "--output",
                str(output_file),
            ])
        finally:
            sys.path.remove(str(tmp_path))
            if module_name in sys.modules:
                del sys.modules[module_name]

        assert exit_code == Exit.ERROR
        captured = capsys.readouterr()
        assert "--input-file-type is required" in captured.err

    def test_dict_openapi(self, tmp_path: Path) -> None:
        """Test dict input as OpenAPI spec."""
        import importlib
        import uuid

        module_name = f"test_specs_{uuid.uuid4().hex[:8]}"
        test_module = tmp_path / f"{module_name}.py"
        test_module.write_text(
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

        output_file = tmp_path / "output.py"

        sys.path.insert(0, str(tmp_path))
        importlib.invalidate_caches()
        try:
            exit_code = main([
                "--ignore-pyproject",
                "--input-model",
                f"{module_name}:OPENAPI_SPEC",
                "--input-file-type",
                "openapi",
                "--output",
                str(output_file),
            ])
        finally:
            sys.path.remove(str(tmp_path))
            if module_name in sys.modules:
                del sys.modules[module_name]

        assert exit_code == Exit.OK
        content = output_file.read_text()
        assert "User" in content


class TestInputModelErrors:
    """Tests for --input-model error handling."""

    @pytest.mark.cli_doc(
        options=["--input-model"],
        cli_args=["--input-model", "module:ObjectName"],
        input_model="module:ObjectName",
        expected_stdout="",
    )
    def test_invalid_format_no_colon(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test error when colon is missing."""
        exit_code = main([
            "--ignore-pyproject",
            "--input-model",
            "pydantic.BaseModel",
        ])

        assert exit_code == Exit.ERROR
        captured = capsys.readouterr()
        assert "Invalid --input-model format" in captured.err

    def test_invalid_module(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test error when module doesn't exist."""
        exit_code = main([
            "--ignore-pyproject",
            "--input-model",
            "nonexistent_module_12345:Model",
        ])

        assert exit_code == Exit.ERROR
        captured = capsys.readouterr()
        assert "Cannot import module" in captured.err

    def test_invalid_class(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test error when class doesn't exist in module."""
        exit_code = main([
            "--ignore-pyproject",
            "--input-model",
            "pydantic:NonexistentClass12345",
        ])

        assert exit_code == Exit.ERROR
        captured = capsys.readouterr()
        assert "has no attribute" in captured.err

    def test_not_pydantic_model_or_dict(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test error when object is not a Pydantic model or dict."""
        exit_code = main([
            "--ignore-pyproject",
            "--input-model",
            "pathlib:Path",
        ])

        assert exit_code == Exit.ERROR
        captured = capsys.readouterr()
        assert "is not a supported type" in captured.err

    @SKIP_PYDANTIC_V1
    def test_pydantic_v1_model_error(
        self,
        pydantic_model_module: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test error when Pydantic v1 model is used."""
        import builtins

        sys.path.insert(0, str(pydantic_model_module))
        try:
            import test_pydantic_models

            original_hasattr = builtins.hasattr

            def mock_hasattr(obj: object, name: str) -> bool:
                if name == "model_json_schema" and obj is test_pydantic_models.UserModel:
                    return False
                return original_hasattr(obj, name)

            monkeypatch.setattr(builtins, "hasattr", mock_hasattr)

            exit_code = main([
                "--ignore-pyproject",
                "--input-model",
                "test_pydantic_models:UserModel",
            ])
        finally:
            sys.path.remove(str(pydantic_model_module))
            sys.modules.pop("test_pydantic_models", None)

        assert exit_code == Exit.ERROR
        captured = capsys.readouterr()
        assert "requires Pydantic v2 model" in captured.err


class TestInputModelMutualExclusion:
    """Tests for --input-model mutual exclusion."""

    def test_mutual_exclusion_with_input(
        self,
        pydantic_model_module: Path,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test --input-model cannot be used with --input."""
        sys.path.insert(0, str(pydantic_model_module))
        try:
            exit_code = main([
                "--ignore-pyproject",
                "--input-model",
                "test_pydantic_models:UserModel",
                "--input",
                str(tmp_path / "schema.json"),
            ])
        finally:
            sys.path.remove(str(pydantic_model_module))
            sys.modules.pop("test_pydantic_models", None)

        assert exit_code == Exit.ERROR
        captured = capsys.readouterr()
        assert "--input-model cannot be used with --input or --url" in captured.err

    def test_mutual_exclusion_with_url(
        self,
        pydantic_model_module: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test --input-model cannot be used with --url."""
        sys.path.insert(0, str(pydantic_model_module))
        try:
            exit_code = main([
                "--ignore-pyproject",
                "--input-model",
                "test_pydantic_models:UserModel",
                "--url",
                "https://example.com/schema.json",
            ])
        finally:
            sys.path.remove(str(pydantic_model_module))
            sys.modules.pop("test_pydantic_models", None)

        assert exit_code == Exit.ERROR
        captured = capsys.readouterr()
        assert "--input-model cannot be used with --input or --url" in captured.err

    def test_mutual_exclusion_with_watch(
        self,
        pydantic_model_module: Path,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test --input-model cannot be used with --watch."""
        sys.path.insert(0, str(pydantic_model_module))
        try:
            exit_code = main([
                "--ignore-pyproject",
                "--input-model",
                "test_pydantic_models:UserModel",
                "--watch",
                "--output",
                str(tmp_path / "output.py"),
            ])
        finally:
            sys.path.remove(str(pydantic_model_module))
            sys.modules.pop("test_pydantic_models", None)

        assert exit_code == Exit.ERROR
        captured = capsys.readouterr()
        assert "--watch cannot be used with --input-model" in captured.err
