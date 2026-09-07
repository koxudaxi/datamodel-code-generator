"""Native and generated controls for diagnosed pattern property intersections."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from datamodel_code_generator import DataModelType, GenerateConfig, InputFileType, generate
from datamodel_code_generator.format import Formatter
from tests.conftest import assert_inputs_not_mutated, assert_output
from tests.main.conftest import JSON_SCHEMA_DATA_PATH, _generated_model, run_main_with_args
from tests.main.jsonschema.conftest import EXPECTED_JSON_SCHEMA_PATH

if TYPE_CHECKING:
    from pathlib import Path

EXPECTED = EXPECTED_JSON_SCHEMA_PATH / "pattern_intersections"
CASES = json.loads((EXPECTED / "cases.json").read_text())


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize("formatter", ["external", "builtin"])
def test_pattern_property_intersections(
    tmp_path: Path, case: str, enabled: bool, entrypoint: str, formatter: str
) -> None:
    """Validate raw values independently while preserving ordinary generated code."""
    source = JSON_SCHEMA_DATA_PATH / "pattern_intersections" / f"{case}.json"
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
        ])
    else:
        generate(
            source,
            config=GenerateConfig(
                input_file_type=InputFileType.JsonSchema,
                output_model_type=DataModelType.PydanticV2BaseModel,
                output=output,
                disable_timestamp=True,
                generate_schema_validators=enabled,
                formatters=[Formatter(value) for value in formatters],
            ),
        )
    suffix = case if enabled else f"{case}_disabled"
    golden_suffix = (
        f"{suffix}_builtin" if formatter == "builtin" and suffix in {"complex_disabled", "rejected"} else suffix
    )
    assert_output(output.read_text(), EXPECTED / f"{golden_suffix}.py")
    schema = json.loads(source.read_text())
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    records = []
    with _generated_model(output, "generated_pattern_intersection", "Root") as model:
        for payload in CASES[case]["payloads"]:
            record = {"schema_valid": validator.is_valid(payload)}
            with assert_inputs_not_mutated(payload):
                try:
                    value = model.model_validate(payload)
                except ValidationError:
                    record["generated"] = "rejected"
                else:
                    record["generated"] = value.model_dump(mode="json", by_alias=True)
            records.append(record)
    assert_output(json.dumps(records, indent=2), EXPECTED / f"{suffix}_runtime.txt")


@pytest.mark.parametrize("formatter", ["external", "builtin"])
def test_invalid_pattern_does_not_change_generation(tmp_path: Path, formatter: str) -> None:
    """Keep unsupported regex generation unchanged while limiting intersection detection."""
    from jsonschema.exceptions import SchemaError

    source = JSON_SCHEMA_DATA_PATH / "pattern_intersections_invalid_regex.json"
    with pytest.raises(SchemaError):
        Draft202012Validator.check_schema(json.loads(source.read_text()))
    output = tmp_path / "output.py"
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
        "--generate-schema-validators",
        "--formatters",
        *(["builtin"] if formatter == "builtin" else ["black", "isort"]),
    ])
    assert_output(output.read_text(), EXPECTED / "invalid_regex.py")
