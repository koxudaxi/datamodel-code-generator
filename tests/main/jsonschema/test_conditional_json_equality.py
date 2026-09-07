"""Conditional required rules distinguish JSON booleans from numbers."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from jsonschema import Draft202012Validator
from jsonschema import ValidationError as SchemaValidationError
from pydantic import ValidationError

from datamodel_code_generator import DataModelType, InputFileType, SchemaValidatorType
from datamodel_code_generator.format import Formatter
from tests.conftest import assert_output
from tests.main.conftest import (
    JSON_SCHEMA_DATA_PATH,
    _generated_model,
    run_generate_file_and_assert,
    run_main_and_assert,
)
from tests.main.jsonschema.conftest import EXPECTED_JSON_SCHEMA_PATH, assert_file_content

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize("formatter", ["builtin", "external"])
@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize(
    "case",
    [
        "true",
        "false",
        "one",
        "zero",
        "float",
        "object",
        "array",
        "enum",
        "string",
        "null",
        "strings",
        "string_object",
        "empty_object",
        "empty_array",
    ],
)
def test_conditional_json_equality(
    output_file: Path, entrypoint: str, formatter: str, enabled: bool, case: str
) -> None:
    """Compare native generated constructors and validators with JSON Schema semantics."""
    schema_path = JSON_SCHEMA_DATA_PATH / f"conditional_json_equality/{case}.json"
    expected = f"conditional_json_equality/{case}_{enabled}.py"
    formatters = ["builtin"] if formatter == "builtin" else ["black", "isort"]
    if entrypoint == "cli":
        run_main_and_assert(
            input_path=schema_path,
            output_path=output_file,
            input_file_type="jsonschema",
            assert_func=assert_file_content,
            expected_file=expected,
            extra_args=[
                "--disable-timestamp",
                "--output-model-type",
                "pydantic_v2.BaseModel",
                "--formatters",
                *formatters,
                *(["--schema-validator-type", "pydantic-v2"] if enabled else []),
            ],
        )
    else:
        run_generate_file_and_assert(
            input_path=schema_path,
            output_path=output_file,
            input_file_type=InputFileType.JsonSchema,
            assert_func=assert_file_content,
            expected_file=expected,
            disable_timestamp=True,
            output_model_type=DataModelType.PydanticV2BaseModel,
            schema_validator_type=SchemaValidatorType.PydanticV2 if enabled else None,
            formatters=[Formatter(value) for value in formatters],
        )
    cases = json.loads((JSON_SCHEMA_DATA_PATH.parent / "payloads/conditional_json_equality.json").read_text())
    payloads = next(item for item in cases if item["name"] == case)
    oracle = Draft202012Validator(json.loads(schema_path.read_text()))
    with _generated_model(output_file, "conditional_json_equality", "Root") as model:
        assert_output(
            "\n".join(model.model_fields) + "\n",
            EXPECTED_JSON_SCHEMA_PATH / "conditional_json_equality/fields.txt",
        )
        for value in payloads["valid"]:
            oracle.validate(value)
            model.model_validate(value)
            model.model_validate_json(json.dumps(value))
            model(**value)
        for value in payloads["invalid"]:
            with pytest.raises(SchemaValidationError):
                oracle.validate(value)
            if enabled:
                with pytest.raises(ValidationError):
                    model.model_validate(value)
                with pytest.raises(ValidationError):
                    model.model_validate_json(json.dumps(value))
                with pytest.raises(ValidationError):
                    model(**value)
            else:
                model.model_validate(value)
                model.model_validate_json(json.dumps(value))
                model(**value)
