"""Root allOf constraints retain the assertions alongside the composition."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from jsonschema import Draft7Validator
from jsonschema import ValidationError as SchemaValidationError
from pydantic import ValidationError

from datamodel_code_generator import InputFileType
from datamodel_code_generator.format import Formatter
from tests.conftest import assert_output
from tests.main.conftest import (
    JSON_SCHEMA_DATA_PATH,
    _generated_model,
    _model_json_validator,
    assert_generated_model_json_validation,
    run_generate_file_and_assert,
    run_main_and_assert,
)
from tests.main.jsonschema.conftest import EXPECTED_JSON_SCHEMA_PATH, assert_file_content

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize("formatter", ["builtin", "external"])
@pytest.mark.parametrize("constraints", [False, True])
@pytest.mark.parametrize("merge", ["none", "all"])
@pytest.mark.parametrize(
    "case", ["length", "minimum", "number", "multiple", "redundant", "description", "ordinary", "same_pattern"]
)
def test_allof_outer_constraints(
    output_file: Path, entrypoint: str, formatter: str, constraints: bool, merge: str, case: str
) -> None:
    """Compare real generated root validation with all schema assertions."""
    schema = JSON_SCHEMA_DATA_PATH / f"allof_outer_constraints/{case}.json"
    formatters = ["builtin"] if formatter == "builtin" else ["black", "isort"]
    expected = f"allof_outer_constraints/{case}_{constraints}_{merge}.py"
    if entrypoint == "cli":
        run_main_and_assert(
            input_path=schema,
            output_path=output_file,
            input_file_type="jsonschema",
            assert_func=assert_file_content,
            expected_file=expected,
            extra_args=[
                "--disable-timestamp",
                "--allof-merge-mode",
                merge,
                "--formatters",
                *formatters,
                *(["--field-constraints"] if constraints else []),
            ],
        )
    else:
        run_generate_file_and_assert(
            input_path=schema,
            output_path=output_file,
            input_file_type=InputFileType.JsonSchema,
            assert_func=assert_file_content,
            expected_file=expected,
            disable_timestamp=True,
            allof_merge_mode=merge,
            field_constraints=constraints,
            formatters=[Formatter(value) for value in formatters],
        )
    cases = json.loads((JSON_SCHEMA_DATA_PATH.parent / "payloads/allof_outer_constraints.json").read_text())
    payloads = next(item for item in cases if item["name"] == case)
    validator = Draft7Validator(json.loads(schema.read_text()))
    with _generated_model(output_file, "allof_outer_constraints", "Root") as model:
        validate = _model_json_validator(model)
        assert_output(
            "\n".join(model.model_fields) + "\n",
            EXPECTED_JSON_SCHEMA_PATH / "allof_outer_constraints/root_fields.txt",
        )
        for value in payloads["valid"]:
            validator.validate(value)
            assert_generated_model_json_validation(
                output_file,
                module_name="allof_outer_constraints_valid",
                model_name="Root",
                valid_json=json.dumps(value),
                invalid_json=json.dumps(payloads["invalid"][0]),
                expected_error_type=payloads["error_type"],
                expected_attribute_path=("root",),
                expected_attribute_value=value,
            )
        for value in payloads["invalid"]:
            with pytest.raises(SchemaValidationError):
                validator.validate(value)
            with pytest.raises(ValidationError):
                validate(json.dumps(value))
