"""Check type-specific union constraints against native JSON Schema validation."""

from __future__ import annotations

import json
from contextlib import nullcontext
from functools import partial
from typing import TYPE_CHECKING

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from datamodel_code_generator import InputFileType, generate_dynamic_models
from datamodel_code_generator.config import GenerateConfig
from tests.conftest import assert_output
from tests.main.conftest import (
    DATA_PATH,
    EXPECTED_JSON_SCHEMA_PATH,
    JSON_SCHEMA_DATA_PATH,
    _generated_model,
    run_generate_file_and_assert,
    run_main_and_assert,
)
from tests.main.jsonschema.conftest import assert_file_content

if TYPE_CHECKING:
    from pathlib import Path

INPUTS = JSON_SCHEMA_DATA_PATH / "type_union_constraints"
PAYLOADS = DATA_PATH / "payloads" / "type_union_constraints"
EXPECTED = EXPECTED_JSON_SCHEMA_PATH / "type_union_constraints"
CASES = json.loads((PAYLOADS / "cases.json").read_text())


@pytest.mark.parametrize("name", CASES)
@pytest.mark.parametrize("constraints", [False, True])
@pytest.mark.parametrize("entry", ["cli", "api", "dynamic"])
def test_type_union_constraints(name: str, constraints: bool, entry: str, output_file: Path) -> None:
    """Validate branches without changing normal order or disabled-option behavior."""
    input_path = INPUTS / f"{name}.json"
    expected_file = f"type_union_constraints/{name}_{int(constraints)}.py"
    if entry == "cli":
        run_main_and_assert(
            input_path=input_path,
            output_path=output_file,
            input_file_type="jsonschema",
            extra_args=[
                "--custom-file-header",
                "# Type-specific union constraints",
                *(["--field-constraints"] if constraints else []),
            ],
            assert_func=assert_file_content,
            expected_file=expected_file,
        )
    elif entry == "api":
        run_generate_file_and_assert(
            input_path=input_path,
            output_path=output_file,
            input_file_type=InputFileType.JsonSchema,
            custom_file_header="# Type-specific union constraints",
            field_constraints=constraints,
            assert_func=assert_file_content,
            expected_file=expected_file,
        )
    schema = json.loads(input_path.read_text())
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    payloads = json.loads((PAYLOADS / f"{name}.json").read_text())
    assert_output(
        json.dumps([validator.is_valid(value) for value in payloads], indent=2) + "\n",
        EXPECTED / f"{name}_native.txt",
    )
    runtime_path = EXPECTED / (f"{name}_native.txt" if constraints else f"{name}_0_runtime.txt")
    acceptance = json.loads(runtime_path.read_text())
    context = (
        nullcontext(
            generate_dynamic_models(schema, config=GenerateConfig(field_constraints=constraints), cache_size=0)["Root"]
        )
        if entry == "dynamic"
        else _generated_model(output_file, "type_union_constraints", "Root")
    )
    actual = []
    with context as model:
        for value, valid in zip(payloads, acceptance, strict=True):
            if valid:
                model.model_validate(value)
                actual.append(True)
            else:
                with pytest.raises(ValidationError):
                    model.model_validate(value)
                actual.append(False)
    assert_output(json.dumps(actual, indent=2) + "\n", runtime_path)


@pytest.mark.parametrize(
    "name",
    ["string_length_field", "both_root", "array_minimum_field", "plain_field", "modeled_field", "numeric_min_field"],
)
@pytest.mark.parametrize(
    "mode", ["annotated", "legacy_union", "strict", "msgspec", "pydantic_dataclass", "msgspec_plain"]
)
@pytest.mark.parametrize("entry", ["cli", "api"])
def test_type_union_constraint_options(name: str, mode: str, entry: str, output_file: Path) -> None:
    """Respect supported annotation, strictness, backend, and union-syntax choices."""
    import msgspec
    from pydantic import TypeAdapter

    from datamodel_code_generator import DataModelType
    from datamodel_code_generator.types import StrictTypes

    options = {
        "annotated": {"use_annotated": True},
        "legacy_union": {"use_union_operator": False},
        "strict": {"strict_types": [StrictTypes.str, StrictTypes.int]},
        "msgspec": {"output_model_type": DataModelType.MsgspecStruct, "use_annotated": True},
        "pydantic_dataclass": {"output_model_type": DataModelType.PydanticV2Dataclass},
        "msgspec_plain": {"output_model_type": DataModelType.MsgspecStruct, "use_annotated": False},
    }[mode]
    arguments = {
        "annotated": ["--use-annotated"],
        "legacy_union": ["--no-use-union-operator"],
        "strict": ["--strict-types", "str", "int"],
        "msgspec": ["--output-model-type", "msgspec.Struct", "--use-annotated"],
        "pydantic_dataclass": ["--output-model-type", "pydantic_v2.dataclass"],
        "msgspec_plain": ["--output-model-type", "msgspec.Struct", "--no-use-annotated"],
    }[mode]
    input_path = INPUTS / f"{name}.json"
    expected_file = f"type_union_constraints/{name}_{mode}.py"
    if entry == "cli":
        run_main_and_assert(
            input_path=input_path,
            output_path=output_file,
            input_file_type="jsonschema",
            extra_args=["--custom-file-header", "# Type-specific union constraints", "--field-constraints", *arguments],
            assert_func=assert_file_content,
            expected_file=expected_file,
        )
    else:
        run_generate_file_and_assert(
            input_path=input_path,
            output_path=output_file,
            input_file_type=InputFileType.JsonSchema,
            custom_file_header="# Type-specific union constraints",
            field_constraints=True,
            assert_func=assert_file_content,
            expected_file=expected_file,
            **options,
        )
    payloads = json.loads((PAYLOADS / f"{name}.json").read_text())
    expected_runtime = EXPECTED / (f"{name}_{mode}_runtime.txt" if mode == "msgspec_plain" else f"{name}_native.txt")
    acceptance = json.loads(expected_runtime.read_text())
    actual = []
    with _generated_model(output_file, "type_union_options", "Root") as model:
        validate = (
            partial(msgspec.convert, type=model) if mode.startswith("msgspec") else TypeAdapter(model).validate_python
        )
        for value, valid in zip(payloads, acceptance, strict=True):
            if valid:
                validate(value)
                actual.append(True)
            else:
                with pytest.raises((ValidationError, msgspec.ValidationError)):
                    validate(value)
                actual.append(False)
    assert_output(json.dumps(actual, indent=2) + "\n", expected_runtime)
