"""Runtime validators on inline allOf children use the same JSON Schema rules."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from jsonschema import Draft202012Validator

from datamodel_code_generator import DataModelType, InputFileType
from tests.conftest import assert_output
from tests.main.conftest import (
    DATA_PATH,
    JSON_SCHEMA_DATA_PATH,
    _assert_model_json_invalid,
    _generated_model,
    _uses_external_test_default_formatter,
    assert_generated_model_json_validation,
    run_generate_file_and_assert,
    run_main_and_assert,
)
from tests.main.jsonschema.conftest import assert_file_content

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize(
    "case", ["conditional", "oneof", "anyof", "nested", "count", "core", "inherited", "referenced"]
)
def test_inline_allof_validators(output_file: Path, entrypoint: str, case: str) -> None:
    """Validate native-schema and generated runtime behavior through both entrypoints."""
    source = JSON_SCHEMA_DATA_PATH / "inline_allof_validators" / f"{case}.json"
    payloads = DATA_PATH / "payloads/inline_allof_validators"
    values = json.loads((payloads / f"{case}.json").read_text())
    native = Draft202012Validator(json.loads(source.read_text()))
    assert_output(
        json.dumps([native.is_valid(values["valid"]), native.is_valid(values["invalid"])]) + "\n",
        payloads / "native.txt",
    )
    suffix = "_builtin" if case in {"anyof", "core"} and not _uses_external_test_default_formatter() else ""
    expected = f"inline_allof_validators/{case}{suffix}.py"
    if entrypoint == "cli":
        run_main_and_assert(
            input_path=source,
            output_path=output_file,
            input_file_type="jsonschema",
            assert_func=assert_file_content,
            expected_file=expected,
            extra_args=[
                "--output-model-type",
                "pydantic_v2.BaseModel",
                "--generate-schema-validators",
                "--disable-timestamp",
            ],
            force_exec_validation=True,
        )
    else:
        run_generate_file_and_assert(
            input_path=source,
            output_path=output_file,
            input_file_type=InputFileType.JsonSchema,
            output_model_type=DataModelType.PydanticV2BaseModel,
            generate_schema_validators=True,
            disable_timestamp=True,
            assert_func=assert_file_content,
            expected_file=expected,
        )
    assert_generated_model_json_validation(
        output_file,
        module_name=f"inline_allof_{case}",
        model_name="Root",
        valid_json=json.dumps(values["valid"]),
        invalid_json=json.dumps(values["invalid"]),
        expected_error_type="value_error",
    )
    with _generated_model(output_file, f"inline_allof_python_{case}", "Root") as model:
        _assert_model_json_invalid(model.model_validate, values["invalid"], "value_error")
