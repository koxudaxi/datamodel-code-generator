"""Runtime validators on inline allOf children use the same JSON Schema rules."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from jsonschema import Draft202012Validator

from datamodel_code_generator import DataModelType, Formatter, GenerateConfig, InputFileType, generate
from tests.conftest import assert_output
from tests.main.conftest import (
    DATA_PATH,
    JSON_SCHEMA_DATA_PATH,
    _assert_model_json_invalid,
    _generated_model,
    assert_generated_model_json_validation,
    run_main_with_args,
)
from tests.main.jsonschema.conftest import assert_file_content

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("formatter", ["builtin", "external"])
@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize(
    "case", ["conditional", "oneof", "anyof", "nested", "count", "core", "inherited", "referenced"]
)
def test_inline_allof_validators(output_file: Path, entrypoint: str, case: str, formatter: str) -> None:
    """Validate native-schema and generated runtime behavior through both entrypoints."""
    source = JSON_SCHEMA_DATA_PATH / "inline_allof_validators" / f"{case}.json"
    payloads = DATA_PATH / "payloads/inline_allof_validators"
    values = json.loads((payloads / f"{case}.json").read_text())
    native = Draft202012Validator(json.loads(source.read_text()))
    assert_output(
        json.dumps([native.is_valid(values["valid"]), native.is_valid(values["invalid"])]) + "\n",
        payloads / "native.txt",
    )
    # Black and the builtin formatter intentionally wrap the runtime helpers differently.
    formatters = ["builtin"] if formatter == "builtin" else ["black", "isort"]
    (output_file.parent / "pyproject.toml").write_text((source.parent / "pyproject.toml").read_text())
    suffix = "_builtin" if case in {"anyof", "core"} and formatter == "builtin" else ""
    expected = f"inline_allof_validators/{case}{suffix}.py"
    if entrypoint == "cli":
        run_main_with_args([
            "--input",
            str(source),
            "--output",
            str(output_file),
            "--input-file-type",
            "jsonschema",
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--generate-schema-validators",
            "--disable-timestamp",
            "--formatters",
            *formatters,
        ])
    else:
        generate(
            source,
            config=GenerateConfig(
                output=output_file,
                input_file_type=InputFileType.JsonSchema,
                output_model_type=DataModelType.PydanticV2BaseModel,
                generate_schema_validators=True,
                disable_timestamp=True,
                formatters=[Formatter(value) for value in formatters],
                settings_path=output_file.parent,
            ),
        )
    assert_file_content(output_file, expected)
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
