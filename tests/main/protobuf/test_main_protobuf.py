"""Tests for Protocol Buffers code generation."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any, cast

import black
import pytest

from datamodel_code_generator import Error, InputFileType, generate, infer_input_type
from datamodel_code_generator.__main__ import Exit
from datamodel_code_generator.parser.protobuf import WELL_KNOWN_SCHEMAS, convert_protobuf_schema_data
from tests.conftest import assert_output
from tests.main.conftest import (
    EXPECTED_PROTOBUF_PATH,
    PROTOBUF_DATA_PATH,
    assert_input_file_type,
    run_generate_and_assert,
    run_generate_file_and_assert,
    run_main_and_assert,
)
from tests.main.protobuf.conftest import assert_file_content

if TYPE_CHECKING:
    from pathlib import Path


def test_main_protobuf_complex_proto3(output_file: Path) -> None:
    """Generate models from a proto3 schema with imports, service, and well-known types."""
    run_main_and_assert(
        input_path=PROTOBUF_DATA_PATH / "complex_proto3.proto",
        output_path=output_file,
        input_file_type="protobuf",
        extra_args=["--use-field-description"],
        assert_func=assert_file_content,
        expected_file="complex_proto3.py",
        importable_module_name="generated_protobuf",
        importable_module_attribute="ExampleShopV1Order",
    )


def test_main_protobuf_infer_input_file_type(output_file: Path) -> None:
    """Infer Protocol Buffers input and generate a model."""
    run_main_and_assert(
        input_path=PROTOBUF_DATA_PATH / "proto3_optional.proto",
        output_path=output_file,
        assert_func=assert_file_content,
        expected_file="proto3_optional.py",
    )


def test_main_protobuf_proto2_schema_version(output_file: Path) -> None:
    """Generate models from proto2 with required, optional, repeated, and defaults."""
    run_main_and_assert(
        input_path=PROTOBUF_DATA_PATH / "proto2.proto",
        output_path=output_file,
        input_file_type="protobuf",
        extra_args=["--schema-version", "proto2"],
        assert_func=assert_file_content,
        expected_file="proto2.py",
    )


def test_main_protobuf_proto3_optional_schema_version(output_file: Path) -> None:
    """Generate models from proto3 optional fields with explicit schema version."""
    run_main_and_assert(
        input_path=PROTOBUF_DATA_PATH / "proto3_optional.proto",
        output_path=output_file,
        input_file_type="protobuf",
        extra_args=["--schema-version", "proto3"],
        assert_func=assert_file_content,
        expected_file="proto3_optional.py",
    )


def test_main_protobuf_well_known_wrappers(output_file: Path) -> None:
    """Generate models for all wrapper well-known types and Empty."""
    run_main_and_assert(
        input_path=PROTOBUF_DATA_PATH / "well_known_wrappers.proto",
        output_path=output_file,
        input_file_type="protobuf",
        assert_func=assert_file_content,
        expected_file="well_known_wrappers.py",
    )


@pytest.mark.allow_direct_assert
def test_convert_protobuf_schema_data_isolates_well_known_schema_templates() -> None:
    """Keep converted well-known schemas independent from module-level templates."""
    original_templates = deepcopy(WELL_KNOWN_SCHEMAS)
    proto = """syntax = "proto3";
package aliasing;
import "google/protobuf/struct.proto";
import "google/protobuf/wrappers.proto";

message UsesWellKnown {
  google.protobuf.Value value = 1;
  google.protobuf.ListValue list_value = 2;
  google.protobuf.StringValue wrapped = 3;
}
"""

    try:
        first = convert_protobuf_schema_data(proto)
        properties = first["definitions"]["aliasing__UsesWellKnown"]["properties"]
        value_schema = properties["value"]
        list_value_schema = properties["list_value"]
        wrapped_schema = properties["wrapped"]

        assert value_schema["anyOf"] is not WELL_KNOWN_SCHEMAS["google.protobuf.Value"]["anyOf"]
        assert list_value_schema["items"] is not WELL_KNOWN_SCHEMAS["google.protobuf.ListValue"]["items"]
        assert wrapped_schema["anyOf"] is not WELL_KNOWN_SCHEMAS["google.protobuf.StringValue"]["anyOf"]

        value_schema["anyOf"][0]["x-mutated"] = True
        list_value_schema["items"]["x-mutated"] = True
        wrapped_schema["anyOf"].append({"type": "integer"})

        second = convert_protobuf_schema_data(proto)
        second_properties = second["definitions"]["aliasing__UsesWellKnown"]["properties"]

        assert original_templates == WELL_KNOWN_SCHEMAS
        assert second_properties["value"] == original_templates["google.protobuf.Value"]
        assert second_properties["list_value"] == original_templates["google.protobuf.ListValue"]
        assert second_properties["wrapped"] == original_templates["google.protobuf.StringValue"]
    finally:
        WELL_KNOWN_SCHEMAS.clear()
        WELL_KNOWN_SCHEMAS.update(original_templates)


def test_main_protobuf_spec_proto3(output_file: Path) -> None:
    """Generate models for proto3 constructs from the language specification."""
    run_main_and_assert(
        input_path=PROTOBUF_DATA_PATH / "spec_proto3.proto",
        output_path=output_file,
        input_file_type="protobuf",
        extra_args=["--schema-version", "proto3", "--use-field-description"],
        assert_func=assert_file_content,
        expected_file="spec_proto3.py",
    )


def test_main_protobuf_spec_proto2(output_file: Path) -> None:
    """Generate models for proto2 constructs from the language specification."""
    run_main_and_assert(
        input_path=PROTOBUF_DATA_PATH / "spec_proto2.proto",
        output_path=output_file,
        input_file_type="protobuf",
        extra_args=["--schema-version", "proto2"],
        assert_func=assert_file_content,
        expected_file="spec_proto2.py",
    )


def test_main_protobuf_edition_2023_schema_version(output_file: Path) -> None:
    """Infer and generate models for edition 2023 syntax with explicit schema version."""
    run_main_and_assert(
        input_path=PROTOBUF_DATA_PATH / "edition_2023.proto",
        output_path=output_file,
        extra_args=["--schema-version", "2023"],
        assert_func=assert_file_content,
        expected_file="edition_2023.py",
    )


def test_generate_api_protobuf(output_file: Path) -> None:
    """Generate Protocol Buffers models through the public generate() API."""
    run_generate_file_and_assert(
        input_path=PROTOBUF_DATA_PATH / "complex_proto3.proto",
        output_path=output_file,
        input_file_type=InputFileType.Protobuf,
        assert_func=assert_file_content,
        expected_file="complex_proto3_generate.py",
    )


def test_generate_api_protobuf_returns_code() -> None:
    """Return generated code from generate() when output is not provided."""
    result = generate(
        PROTOBUF_DATA_PATH / "proto3_optional.proto",
        input_file_type=InputFileType.Protobuf,
        disable_timestamp=True,
    )

    assert_output(result, EXPECTED_PROTOBUF_PATH / "generate_returns_code.py")


def test_generate_api_protobuf_from_text() -> None:
    """Generate Protocol Buffers models from in-memory .proto text."""
    result = generate(
        'syntax = "proto3";\npackage text.input;\nmessage TextInput { string value = 1; }\n',
        input_file_type=InputFileType.Protobuf,
        disable_timestamp=True,
    )

    assert_output(result, EXPECTED_PROTOBUF_PATH / "text_input.py")


def test_generate_api_protobuf_definition_key_collision() -> None:
    """Keep distinct protobuf symbols when legacy definition keys would collide."""
    result = generate(
        PROTOBUF_DATA_PATH.parent / "protobuf_collision",
        input_file_type=InputFileType.Protobuf,
        disable_timestamp=True,
    )

    assert_output(result, EXPECTED_PROTOBUF_PATH / "collision.py")


def test_generate_api_protobuf_from_path_list() -> None:
    """Generate Protocol Buffers models from a list of .proto file paths."""
    run_generate_and_assert(
        input_=cast(Any, [(PROTOBUF_DATA_PATH / "spec_proto3.proto").resolve()]),  # noqa: TC006
        input_file_type=InputFileType.Protobuf,
        disable_timestamp=True,
        expected_file=EXPECTED_PROTOBUF_PATH / "spec_proto3_list_input.py",
        assert_input_unchanged=True,
    )


def test_generate_api_protobuf_rejects_dict_input() -> None:
    """Reject mapping input because Protocol Buffers requires .proto text."""
    with pytest.raises(Error, match="Dict input is not supported for protobuf"):
        generate({"message": "Invalid"}, input_file_type=InputFileType.Protobuf)


def test_infer_input_file_type_from_message_declaration() -> None:
    """Infer Protocol Buffers from a schema body without an explicit syntax declaration."""
    assert_input_file_type(infer_input_type("message WithoutSyntax { string id = 1; }\n"), InputFileType.Protobuf)


def test_main_protobuf_directory_output_importable(output_dir: Path) -> None:
    """Generate a package from imported .proto files and import the result."""
    expected_directory = (
        EXPECTED_PROTOBUF_PATH / "directory_black_lt_24"
        if int(black.__version__.split(".")[0]) < 24
        else EXPECTED_PROTOBUF_PATH / "directory"
    )
    run_main_and_assert(
        input_path=PROTOBUF_DATA_PATH,
        output_path=output_dir,
        input_file_type="protobuf",
        extra_args=["--module-split-mode", "single"],
        expected_directory=expected_directory,
        force_exec_validation=True,
        importable_module_name="generated_protobuf",
        importable_module_file="__init__.py",
    )


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
        output_should_not_exist=True,
    )


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
        output_should_not_exist=True,
    )


def test_generate_api_protobuf_strict_schema_version_warning(output_file: Path) -> None:
    """Warn when explicit Protocol Buffers schema version conflicts with file syntax in strict mode."""
    run_generate_file_and_assert(
        input_path=PROTOBUF_DATA_PATH / "proto3_optional.proto",
        output_path=output_file,
        input_file_type=InputFileType.Protobuf,
        assert_func=assert_file_content,
        expected_file="proto3_optional_strict_proto2.py",
        schema_version="proto2",
        schema_version_mode="strict",
        expected_warnings=["declares proto3"],
    )


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
        output_should_not_exist=True,
    )
