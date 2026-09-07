"""Resolve referenced standard descriptors without generating unused standard types."""

from __future__ import annotations

import json
from enum import Enum
from typing import TYPE_CHECKING

import msgspec
import pytest
from google.protobuf import descriptor_pool, json_format, message_factory
from pydantic import ValidationError

from datamodel_code_generator import DataModelType, InputFileType
from datamodel_code_generator.parser.protobuf import ProtobufParser, convert_protobuf_schema_data
from tests.conftest import assert_output
from tests.main.conftest import (
    DATA_PATH,
    EXPECTED_PROTOBUF_PATH,
    _generated_model,
    _model_json_validator,
    run_generate_file_and_assert,
    run_main_and_assert,
)
from tests.main.protobuf.conftest import assert_file_content

if TYPE_CHECKING:
    from pathlib import Path

CASES = ["nullvalue", "standard_enum", "standard_message", "unused_standard", "user_namespace"]
BACKENDS = [
    DataModelType.PydanticV2BaseModel,
    DataModelType.PydanticV2Dataclass,
    DataModelType.DataclassesDataclass,
    DataModelType.TypingTypedDict,
    DataModelType.MsgspecStruct,
]


@pytest.fixture(scope="module")
def standard_proto_has_editions() -> bool:
    """Select snapshots for the standard descriptors supplied by the real compiler."""
    path = DATA_PATH / "protobuf_referenced_standard/standard_message.proto"
    descriptors, _ = ProtobufParser(path)._compile_descriptor_set()
    return any(
        field.name == "edition"
        for descriptor in descriptors.file
        if descriptor.name == "google/protobuf/api.proto"
        for message in descriptor.message_type
        if message.name == "Api"
        for field in message.field
    )


@pytest.mark.parametrize("name", CASES)
def test_native_referenced_standard_types(name: str) -> None:
    """Confirm actual protoc descriptors and ProtoJSON accept and reject the external cases."""
    path = DATA_PATH / "protobuf_referenced_standard" / f"{name}.proto"
    descriptors, _ = ProtobufParser(path)._compile_descriptor_set()
    pool = descriptor_pool.DescriptorPool()
    for descriptor in descriptors.file:
        pool.Add(descriptor)
    full_name = "google.protobuf.Payload" if name == "user_namespace" else "Payload"
    model = message_factory.GetMessageClass(pool.FindMessageTypeByName(full_name))
    payloads = DATA_PATH / "payloads/protobuf_referenced_standard"
    value = json_format.Parse((payloads / f"{name}_valid.json").read_text(), model())
    with pytest.raises(json_format.ParseError):
        json_format.Parse((payloads / f"{name}_invalid.json").read_text(), model())
    if name == "nullvalue":
        json_format.Parse((payloads / "nullvalue_null.json").read_text(), model())
        assert_output(
            json.dumps(json_format.MessageToDict(value), indent=2) + "\n",
            EXPECTED_PROTOBUF_PATH / "referenced_standard/native_nullvalue.txt",
        )


@pytest.mark.parametrize("name", CASES)
def test_referenced_standard_definition_order(name: str, standard_proto_has_editions: bool) -> None:
    """Materialize exactly the referenced closure and preserve defaults and comments."""
    path = DATA_PATH / "protobuf_referenced_standard" / f"{name}.proto"
    schema = convert_protobuf_schema_data(path.read_text(), base_path=path.parent)
    suffix = "_pre_editions" if name in {"nullvalue", "standard_message"} and not standard_proto_has_editions else ""
    assert_output(
        json.dumps(schema, indent=2) + "\n", EXPECTED_PROTOBUF_PATH / "referenced_standard" / f"{name}{suffix}.txt"
    )


@pytest.mark.parametrize("name", CASES)
@pytest.mark.parametrize("strict", [False, True])
@pytest.mark.parametrize("entrypoint", ["cli", "api"])
def test_referenced_standard_generation(
    name: str, strict: bool, entrypoint: str, output_file: Path, standard_proto_has_editions: bool
) -> None:
    """Resolve real CLI/API references while preserving normal output and validation."""
    path = DATA_PATH / "protobuf_referenced_standard" / f"{name}.proto"
    suffix = "_pre_editions" if name == "standard_message" and not standard_proto_has_editions else ""
    expected = f"referenced_standard/{name}{suffix}.py"
    if entrypoint == "cli":
        run_main_and_assert(
            input_path=path,
            output_path=output_file,
            input_file_type="protobuf",
            extra_args=["--disable-timestamp", "--use-field-description", *(["--strict-refs"] if strict else [])],
            assert_func=assert_file_content,
            expected_file=expected,
        )
    else:
        run_generate_file_and_assert(
            input_path=path,
            output_path=output_file,
            input_file_type=InputFileType.Protobuf,
            strict_refs=strict,
            disable_timestamp=True,
            use_field_description=True,
            assert_func=assert_file_content,
            expected_file=expected,
        )
    class_name = "GoogleProtobufPayload" if name == "user_namespace" else "Payload"
    payloads = DATA_PATH / "payloads/protobuf_referenced_standard"
    with _generated_model(output_file, f"standard_{name}_{entrypoint}_{strict}", class_name) as model:
        validate = _model_json_validator(model)
        validate((payloads / f"{name}_valid.json").read_text())
        with pytest.raises(ValidationError):
            validate((payloads / f"{name}_invalid.json").read_text())


@pytest.mark.parametrize("backend", BACKENDS)
@pytest.mark.parametrize("strict", [False, True])
@pytest.mark.parametrize("entrypoint", ["cli", "api"])
def test_nullvalue_enum_backends(backend: DataModelType, strict: bool, entrypoint: str, output_file: Path) -> None:
    """Preserve enum names and backend null handling without claiming ProtoJSON serialization."""
    path = DATA_PATH / "protobuf_referenced_standard/nullvalue.proto"
    expected = f"referenced_standard/nullvalue_{backend.name}.py"
    if entrypoint == "cli":
        run_main_and_assert(
            input_path=path,
            output_path=output_file,
            input_file_type="protobuf",
            extra_args=[
                "--disable-timestamp",
                "--output-model-type",
                backend.value,
                *(["--strict-refs"] if strict else []),
            ],
            assert_func=assert_file_content,
            expected_file=expected,
        )
    else:
        run_generate_file_and_assert(
            input_path=path,
            output_path=output_file,
            input_file_type=InputFileType.Protobuf,
            strict_refs=strict,
            output_model_type=backend,
            disable_timestamp=True,
            assert_func=assert_file_content,
            expected_file=expected,
        )
    payloads = DATA_PATH / "payloads/protobuf_referenced_standard"
    with _generated_model(output_file, f"nullvalue_{backend.name}_{entrypoint}_{strict}", "Payload") as model:
        valid = (payloads / "nullvalue_valid.json").read_text()
        invalid = (payloads / "nullvalue_invalid.json").read_text()
        null = (payloads / "nullvalue_null.json").read_text()
        if backend == DataModelType.MsgspecStruct:
            result = msgspec.json.decode(valid, type=model)
            with pytest.raises(msgspec.ValidationError):
                msgspec.json.decode(null, type=model)
            with pytest.raises(msgspec.ValidationError):
                msgspec.json.decode(invalid, type=model)
        else:
            validate = _model_json_validator(model)
            result = validate(valid)
            if backend == DataModelType.TypingTypedDict:
                with pytest.raises(ValidationError):
                    validate(null)
            else:
                validate(null)
            with pytest.raises(ValidationError):
                validate(invalid)
        value = result["value"] if isinstance(result, dict) else result.value
        assert_output(
            json.dumps(value.value if isinstance(value, Enum) else value) + "\n",
            EXPECTED_PROTOBUF_PATH / "referenced_standard/enum_value.txt",
        )
