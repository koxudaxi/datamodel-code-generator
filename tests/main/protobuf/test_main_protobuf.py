"""Tests for Protocol Buffers code generation."""

from __future__ import annotations

import importlib.util
import sys
import warnings
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from datamodel_code_generator import DataModelType, Error, InputFileType, generate, infer_input_type
from datamodel_code_generator.__main__ import Exit
from tests.main.conftest import PROTOBUF_DATA_PATH, run_generate_file_and_assert, run_main_and_assert
from tests.main.protobuf.conftest import assert_protobuf_snippets

if TYPE_CHECKING:
    from pathlib import Path


def test_main_protobuf_complex_proto3(output_file: Path) -> None:
    """Generate models from a proto3 schema with imports, service, and well-known types."""
    run_main_and_assert(
        input_path=PROTOBUF_DATA_PATH / "complex_proto3.proto",
        output_path=output_file,
        input_file_type="protobuf",
        extra_args=["--use-field-description"],
        assert_func=assert_protobuf_snippets,
        expected_file="complex_proto3.py",
    )
    spec = importlib.util.spec_from_file_location("generated_protobuf_oneof", output_file)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    module.ExampleShopV1Order(email="user@example.com")
    with pytest.raises(ValidationError, match="Only one of"):
        module.ExampleShopV1Order(email="user@example.com", phone="+12025550123")


def test_main_protobuf_infer_input_file_type(output_file: Path) -> None:
    """Infer Protocol Buffers input and generate a model."""
    run_main_and_assert(
        input_path=PROTOBUF_DATA_PATH / "proto3_optional.proto",
        output_path=output_file,
        assert_func=assert_protobuf_snippets,
        expected_file="proto3_optional.py",
    )


def test_main_protobuf_proto2_schema_version(output_file: Path) -> None:
    """Generate models from proto2 with required, optional, repeated, and defaults."""
    run_main_and_assert(
        input_path=PROTOBUF_DATA_PATH / "proto2.proto",
        output_path=output_file,
        input_file_type="protobuf",
        extra_args=["--schema-version", "proto2"],
        assert_func=assert_protobuf_snippets,
        expected_file="proto2.py",
    )


def test_main_protobuf_proto3_optional_schema_version(output_file: Path) -> None:
    """Generate models from proto3 optional fields with explicit schema version."""
    run_main_and_assert(
        input_path=PROTOBUF_DATA_PATH / "proto3_optional.proto",
        output_path=output_file,
        input_file_type="protobuf",
        extra_args=["--schema-version", "proto3"],
        assert_func=assert_protobuf_snippets,
        expected_file="proto3_optional.py",
    )


def test_generate_api_protobuf(output_file: Path) -> None:
    """Generate Protocol Buffers models through the public generate() API."""
    run_generate_file_and_assert(
        input_path=PROTOBUF_DATA_PATH / "complex_proto3.proto",
        output_path=output_file,
        input_file_type=InputFileType.Protobuf,
        assert_func=assert_protobuf_snippets,
        expected_file="complex_proto3.py",
    )


def test_generate_api_protobuf_returns_code() -> None:
    """Return generated code from generate() when output is not provided."""
    result = generate(
        PROTOBUF_DATA_PATH / "proto3_optional.proto",
        input_file_type=InputFileType.Protobuf,
        disable_timestamp=True,
    )

    assert isinstance(result, str)
    assert "class ExamplePresencePresence(BaseModel):" in result


def test_generate_api_protobuf_from_text() -> None:
    """Generate Protocol Buffers models from in-memory .proto text."""
    result = generate(
        'syntax = "proto3";\npackage text.input;\nmessage TextInput { string value = 1; }\n',
        input_file_type=InputFileType.Protobuf,
        disable_timestamp=True,
    )

    assert isinstance(result, str)
    assert "class TextInputTextInput(BaseModel):" in result


def test_generate_api_protobuf_dataclass_skips_oneof_validator() -> None:
    """Generate non-Pydantic v2 models without injecting Pydantic oneof validators."""
    result = generate(
        PROTOBUF_DATA_PATH / "complex_proto3.proto",
        input_file_type=InputFileType.Protobuf,
        output_model_type=DataModelType.DataclassesDataclass,
        disable_timestamp=True,
    )

    assert isinstance(result, str)
    assert "class ExampleShopV1Order:" in result
    assert "model_validator" not in result


def test_generate_api_protobuf_definition_key_collision() -> None:
    """Keep distinct protobuf symbols when legacy definition keys would collide."""
    result = generate(
        PROTOBUF_DATA_PATH.parent / "protobuf_collision",
        input_file_type=InputFileType.Protobuf,
        disable_timestamp=True,
    )

    assert isinstance(result, str)
    assert "left: str | None = ''" in result
    assert "right: str | None = ''" in result


def test_generate_api_protobuf_rejects_dict_input() -> None:
    """Reject mapping input because Protocol Buffers requires .proto text."""
    with pytest.raises(Error, match="Dict input is not supported for protobuf"):
        generate({"message": "Invalid"}, input_file_type=InputFileType.Protobuf)


def test_infer_input_file_type_from_message_declaration() -> None:
    """Infer Protocol Buffers from a schema body without an explicit syntax declaration."""
    assert infer_input_type("message WithoutSyntax { string id = 1; }\n") == InputFileType.Protobuf


def test_main_protobuf_directory_output_importable(output_dir: Path) -> None:
    """Generate a package from imported .proto files and import the result."""
    run_main_and_assert(
        input_path=PROTOBUF_DATA_PATH,
        output_path=output_dir,
        input_file_type="protobuf",
        extra_args=["--module-split-mode", "single"],
        force_exec_validation=True,
    )

    content = (output_dir / "example_shop_v1_order.py").read_text(encoding="utf-8")
    assert "class ExampleShopV1Order(BaseModel):" in content
    spec = importlib.util.spec_from_file_location("generated_protobuf", output_dir / "__init__.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


def test_main_protobuf_parse_error(capsys: pytest.CaptureFixture[str], tmp_path: Path, output_file: Path) -> None:
    """Report invalid Protocol Buffers syntax through the CLI."""
    input_path = tmp_path / "invalid.proto"
    input_path.write_text('syntax = "proto3";\nmessage Broken { string id = 1\n', encoding="utf-8")

    run_main_and_assert(
        input_path=input_path,
        output_path=output_file,
        input_file_type="protobuf",
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains="Invalid Protocol Buffers schema",
        file_should_not_exist=output_file,
    )
    assert not output_file.exists()


def test_main_protobuf_invalid_schema_version(capsys: pytest.CaptureFixture[str], output_file: Path) -> None:
    """Report invalid Protocol Buffers schema version values through the CLI."""
    run_main_and_assert(
        input_path=PROTOBUF_DATA_PATH / "proto3_optional.proto",
        output_path=output_file,
        input_file_type="protobuf",
        extra_args=["--schema-version", "draft-07"],
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains="Invalid Protobuf version",
        file_should_not_exist=output_file,
    )
    assert not output_file.exists()


def test_main_protobuf_non_string_map_key_error(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, output_file: Path
) -> None:
    """Reject protobuf maps whose keys cannot be represented by JSON Schema object keys."""
    input_path = tmp_path / "non_string_map.proto"
    input_path.write_text(
        'syntax = "proto3";\nmessage InvalidMap { map<int32, string> values = 1; }\n',
        encoding="utf-8",
    )

    run_main_and_assert(
        input_path=input_path,
        output_path=output_file,
        input_file_type="protobuf",
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains="unsupported non-string key type",
        file_should_not_exist=output_file,
    )
    assert not output_file.exists()


def test_generate_api_protobuf_strict_schema_version_warning(output_file: Path) -> None:
    """Warn when explicit Protocol Buffers schema version conflicts with file syntax in strict mode."""
    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        generate(
            PROTOBUF_DATA_PATH / "proto3_optional.proto",
            input_file_type=InputFileType.Protobuf,
            output=output_file,
            schema_version="proto2",
            schema_version_mode="strict",
        )

    assert any("declares proto3" in str(record.message) for record in records)


def test_main_protobuf_empty_directory_error(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, output_file: Path
) -> None:
    """Report an empty Protocol Buffers input directory."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    run_main_and_assert(
        input_path=empty_dir,
        output_path=output_file,
        input_file_type="protobuf",
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains="No .proto files found in input",
        file_should_not_exist=output_file,
    )
    assert not output_file.exists()
