"""Bounded pattern intersections retain native acceptance and formatter-specific bytes."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from pydantic import ValidationError
from pydantic.version import VERSION as PYDANTIC_VERSION

from datamodel_code_generator import DataModelType, Formatter, GenerateConfig, InputFileType, generate
from tests.conftest import assert_inputs_not_mutated, assert_output
from tests.main.conftest import JSON_SCHEMA_DATA_PATH, _generated_model, run_main_with_args
from tests.main.jsonschema.conftest import EXPECTED_JSON_SCHEMA_PATH

if TYPE_CHECKING:
    from pathlib import Path

FIXTURES = JSON_SCHEMA_DATA_PATH / "additional_pattern_intersections"
CASES = json.loads((FIXTURES / "cases.json").read_text())
EXPECTED = EXPECTED_JSON_SCHEMA_PATH / "additional_pattern_intersections"


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("field_constraints", [False, True])
@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize("formatter", ["builtin", "external"])
def test_additional_pattern_intersections(
    tmp_path: Path, case: str, enabled: bool, field_constraints: bool, entrypoint: str, formatter: str
) -> None:
    """Check complete generated code, native validation, dumps and input mutation."""
    source = FIXTURES / f"{case}.json"
    record = CASES[case]
    template = JSON_SCHEMA_DATA_PATH.parent / "templates" / record["custom"] if record["custom"] else None
    output = tmp_path / "output.py"
    formatters = ["builtin"] if formatter == "builtin" else ["black", "isort"]
    if entrypoint == "cli":
        run_main_with_args([
            "--input",
            str(source),
            "--output",
            str(output),
            "--input-file-type",
            "jsonschema",
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--disable-timestamp",
            "--formatters",
            *formatters,
            *(["--generate-schema-validators"] if enabled else []),
            *(["--field-constraints"] if field_constraints else []),
            *(["--custom-template-dir", str(template)] if template else []),
        ])
    else:
        generate(
            source,
            config=GenerateConfig(
                output=output,
                input_file_type=InputFileType.JsonSchema,
                output_model_type=DataModelType.PydanticV2BaseModel,
                disable_timestamp=True,
                generate_schema_validators=enabled,
                field_constraints=field_constraints,
                custom_template_dir=template,
                formatters=[Formatter(value) for value in formatters],
            ),
        )
    mode = f"{enabled}_{field_constraints}_{formatter}"
    assert_output(output.read_text(), EXPECTED / record["code_names"][mode])
    schema = json.loads(source.read_text())
    if record.get("invalid_schema"):
        with pytest.raises(SchemaError):
            Draft202012Validator.check_schema(schema)
    else:
        Draft202012Validator.check_schema(schema)
    native = Draft202012Validator(schema)
    records = []
    with _generated_model(output, "additional_pattern_generated", "Root") as model:
        for payload in record["payloads"]:
            result = {"native": native.is_valid(payload)}
            with assert_inputs_not_mutated({"payload": payload}):
                try:
                    result["json"] = model.model_validate_json(json.dumps(payload)).model_dump(mode="json")
                except ValidationError:
                    result["json"] = "rejected"
                try:
                    result["python"] = model.model_validate(payload).model_dump(mode="json")
                except ValidationError:
                    result["python"] = "rejected"
            records.append(result)
    runtime_expected = (
        EXPECTED / "pydantic20"
        if case in {"minimum_number", "minimum_shared"} and PYDANTIC_VERSION.split(".")[:2] == ["2", "0"]
        else EXPECTED
    )
    assert_output(json.dumps(records, indent=2), runtime_expected / f"{case}_{enabled}_{field_constraints}_runtime.txt")
