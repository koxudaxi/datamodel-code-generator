"""Reject lossy XSD property bindings while preserving repeated declarations."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import msgspec
import pytest
from lxml import etree
from pydantic import PydanticUserError, ValidationError

from datamodel_code_generator import DataModelType, Error, InputFileType
from datamodel_code_generator.__main__ import Exit
from tests.conftest import assert_output
from tests.main.conftest import (
    DATA_PATH,
    EXPECTED_XML_SCHEMA_PATH,
    XML_SCHEMA_DATA_PATH,
    _generated_model,
    _model_json_validator,
    run_generate_file_and_assert,
    run_main_and_assert,
)
from tests.main.xmlschema.conftest import assert_file_content

if TYPE_CHECKING:
    from pathlib import Path

COLLISIONS = (
    "mixed_element",
    "mixed_attribute",
    "element_attribute",
    "namespaced_elements",
    "namespaced_attributes",
    "local_forms",
    "simple_content_collision",
    "simple_content_value",
    "default_namespace_distinct",
    "default_namespace_attributes",
)
CONTROLS = (
    "ordinary",
    "repeated_refs",
    "group_reuse",
    "choice_reuse",
    "inherited_override",
    "nested_scope",
    "simple_content",
    "global_elements",
    "global_local_reuse",
    "chameleon_reuse",
    "default_namespace_reuse",
    "default_namespace_alias_reuse",
    "empty_namespace_reuse",
)
BACKENDS = (
    DataModelType.PydanticV2BaseModel,
    DataModelType.PydanticV2Dataclass,
    DataModelType.DataclassesDataclass,
    DataModelType.TypingTypedDict,
    DataModelType.MsgspecStruct,
)


@pytest.mark.parametrize("name", [*COLLISIONS, *CONTROLS])
def test_native_xsd_property_names(name: str) -> None:
    """Confirm collision and reuse fixtures are legal XSD with valid XML instances."""
    source = XML_SCHEMA_DATA_PATH / "field_name_collisions" / name
    schema = etree.XMLSchema(etree.parse(str(source.with_suffix(".xsd"))))
    schema.assertValid(etree.parse(str(source.with_suffix(".xml"))))
    with pytest.raises(etree.DocumentInvalid):
        schema.assertValid(etree.parse(str(source.with_suffix(".invalid.xml"))))


@pytest.mark.parametrize("name", COLLISIONS)
@pytest.mark.parametrize("backend", BACKENDS)
@pytest.mark.parametrize("entrypoint", ["cli", "api"])
def test_xsd_property_collision(
    name: str, backend: DataModelType, entrypoint: str, output_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Report distinct XML names before a backend can silently discard a field."""
    source = XML_SCHEMA_DATA_PATH / "field_name_collisions" / f"{name}.xsd"
    expected = EXPECTED_XML_SCHEMA_PATH / "field_name_collisions" / f"{name}.txt"
    if entrypoint == "cli":
        run_main_and_assert(
            input_path=source,
            output_path=output_file,
            input_file_type="xmlschema",
            extra_args=["--output-model-type", backend.value],
            expected_exit=Exit.ERROR,
            capsys=capsys,
            expected_stderr=expected.read_text(encoding="utf-8") + "\n",
            output_should_not_exist=True,
        )
    else:
        with pytest.raises(Error) as exc_info:
            run_generate_file_and_assert(
                input_path=source,
                output_path=output_file,
                input_file_type=InputFileType.XMLSchema,
                output_model_type=backend,
                assert_func=assert_file_content,
            )
        assert_output(str(exc_info.value), expected)
        assert_output(f"{output_file.exists()}\n", EXPECTED_XML_SCHEMA_PATH / "field_name_collisions/absent.txt")


@pytest.mark.parametrize("name", CONTROLS)
@pytest.mark.parametrize("entrypoint", ["cli", "api"])
def test_xsd_property_reuse(name: str, entrypoint: str, output_file: Path) -> None:
    """Preserve baseline output for legal reuse, scope changes, and ordinary fields."""
    source = XML_SCHEMA_DATA_PATH / "field_name_collisions" / f"{name}.xsd"
    expected = f"field_name_collisions/{name}.py"
    if entrypoint == "cli":
        run_main_and_assert(
            input_path=source,
            output_path=output_file,
            input_file_type="xmlschema",
            extra_args=["--disable-timestamp"],
            assert_func=assert_file_content,
            expected_file=expected,
        )
    else:
        run_generate_file_and_assert(
            input_path=source,
            output_path=output_file,
            input_file_type=InputFileType.XMLSchema,
            disable_timestamp=True,
            assert_func=assert_file_content,
            expected_file=expected,
        )


@pytest.mark.parametrize("backend", BACKENDS)
@pytest.mark.parametrize("entrypoint", ["cli", "api"])
def test_xsd_ordinary_fields_runtime(backend: DataModelType, entrypoint: str, output_file: Path) -> None:
    """Keep field order and usable generated types across all supported backends."""
    source = XML_SCHEMA_DATA_PATH / "field_name_collisions/ordinary.xsd"
    suffix = "_cli" if entrypoint == "cli" and backend == DataModelType.MsgspecStruct else ""
    expected = f"field_name_collisions/ordinary_{backend.name}{suffix}.py"
    if entrypoint == "cli":
        run_main_and_assert(
            input_path=source,
            output_path=output_file,
            input_file_type="xmlschema",
            extra_args=["--disable-timestamp", "--output-model-type", backend.value],
            assert_func=assert_file_content,
            expected_file=expected,
        )
    else:
        run_generate_file_and_assert(
            input_path=source,
            output_path=output_file,
            input_file_type=InputFileType.XMLSchema,
            output_model_type=backend,
            disable_timestamp=True,
            assert_func=assert_file_content,
            expected_file=expected,
        )
    payloads = DATA_PATH / "payloads/xsd_field_name_collisions"
    valid_json = (payloads / "ordinary.json").read_text(encoding="utf-8")
    invalid_json = (payloads / "ordinary_invalid.json").read_text(encoding="utf-8")
    with _generated_model(output_file, f"b65_{backend.name}_{entrypoint}", "Root") as model:
        fields = list(model.__annotations__)
        if backend == DataModelType.TypingTypedDict:
            with _generated_model(
                DATA_PATH / "python/xsd_field_name_collisions/native_typeddict.py", "native_xsd_typeddict", "NativeRoot"
            ) as native_model:
                try:
                    _model_json_validator(native_model)
                except PydanticUserError as native_error:
                    assert_output(
                        f"{native_error.code}: {native_error.message}\n",
                        EXPECTED_XML_SCHEMA_PATH / "field_name_collisions/typeddict_native_error.txt",
                    )
                    with pytest.raises(PydanticUserError) as generated_error:
                        _model_json_validator(model)
                    assert_output(
                        f"{generated_error.value.code}: {generated_error.value.message}\n",
                        EXPECTED_XML_SCHEMA_PATH / "field_name_collisions/typeddict_native_error.txt",
                    )
                    assert_output(
                        json.dumps({"fields": fields, "item": model(**json.loads(valid_json))["item"]}, indent=2)
                        + "\n",
                        EXPECTED_XML_SCHEMA_PATH / "field_name_collisions/ordinary_runtime.txt",
                    )
                    return
        if backend == DataModelType.MsgspecStruct:
            value = msgspec.json.decode(valid_json, type=model)
            item = value.item
            with pytest.raises(msgspec.ValidationError):
                msgspec.json.decode(invalid_json, type=model)
        else:
            validate = _model_json_validator(model)
            value = validate(valid_json)
            item = value["item"] if isinstance(value, dict) else value.item
            with pytest.raises(ValidationError):
                validate(invalid_json)

    assert_output(
        json.dumps({"fields": fields, "item": item}, indent=2) + "\n",
        EXPECTED_XML_SCHEMA_PATH / "field_name_collisions/ordinary_runtime.txt",
    )
