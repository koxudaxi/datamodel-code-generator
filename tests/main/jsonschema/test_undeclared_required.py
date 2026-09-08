"""Undeclared required names retain explicit generation options and raw input semantics."""

from __future__ import annotations

import json
from collections import defaultdict
from typing import TYPE_CHECKING

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError
from pydantic.version import VERSION as PYDANTIC_VERSION

from datamodel_code_generator import DataModelType, Formatter, GenerateConfig, InputFileType, generate
from tests.conftest import assert_inputs_not_mutated, assert_output
from tests.main.conftest import JSON_SCHEMA_DATA_PATH, _generated_model, run_main_with_args
from tests.main.jsonschema.conftest import EXPECTED_JSON_SCHEMA_PATH

if TYPE_CHECKING:
    from pathlib import Path

FIXTURES = JSON_SCHEMA_DATA_PATH / "undeclared_required"
CASES = json.loads((FIXTURES / "cases.json").read_text())
EXPECTED = EXPECTED_JSON_SCHEMA_PATH / "undeclared_required"


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize("formatter", ["builtin", "external"])
def test_undeclared_required(tmp_path: Path, case: str, enabled: bool, entrypoint: str, formatter: str) -> None:
    """Compare native validity, Python/JSON validation, full output and model field order."""
    source = FIXTURES / f"{case}.json"
    record = CASES[case]
    options = dict(record["options"])
    if record["custom"]:
        options["custom_template_dir"] = JSON_SCHEMA_DATA_PATH.parent / "templates" / "additional_pattern_context"
    output = tmp_path / "output.py"
    formatters = ["builtin"] if formatter == "builtin" else ["black", "isort"]
    if entrypoint == "cli":
        args = []
        for key, value in options.items():
            argument_value = value
            if isinstance(value, dict):
                value_path = tmp_path / f"{key}.json"
                value_path.write_text(json.dumps(value))
                argument_value = value_path
            option = {
                "force_optional_for_required_fields": "force-optional",
                "apply_default_values_for_required_fields": "use-default",
            }.get(key, key.replace("_", "-"))
            args.extend([f"--{option}", *([] if argument_value is True else [str(argument_value)])])
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
            *args,
        ])
    else:
        if "extra_template_data" in options:
            options["extra_template_data"] = defaultdict(dict, options["extra_template_data"])
        generate(
            source,
            config=GenerateConfig(
                output=output,
                input_file_type=InputFileType.JsonSchema,
                output_model_type=DataModelType.PydanticV2BaseModel,
                disable_timestamp=True,
                generate_schema_validators=enabled,
                formatters=[Formatter(value) for value in formatters],
                **options,
            ),
        )
    assert_output(output.read_text(), EXPECTED / record["code_names"][f"{enabled}_{formatter}"])
    schema = json.loads(source.read_text())
    Draft202012Validator.check_schema(schema)
    native = Draft202012Validator(schema)
    results = []
    with _generated_model(output, "undeclared_required_generated", "Root") as model:
        for payload in record["payloads"]:
            result = {"native": native.is_valid(payload), "fields": list(model.model_fields)}
            with assert_inputs_not_mutated({"payload": payload}):
                try:
                    value = model.model_validate(payload)
                    result["python"] = value.model_dump(mode="json", by_alias=True)
                    result["identity"] = type(value).__name__
                except ValidationError:
                    result["python"] = "rejected"
                try:
                    result["json"] = model.model_validate_json(json.dumps(payload)).model_dump(
                        mode="json", by_alias=True
                    )
                except ValidationError:
                    result["json"] = "rejected"
            results.append(result)
    runtime_expected = (
        EXPECTED / "pydantic20"
        if not enabled and "objects" in case and PYDANTIC_VERSION.split(".")[:2] == ["2", "0"]
        else EXPECTED
    )
    assert_output(json.dumps(results, indent=2), runtime_expected / f"{case}_{enabled}_runtime.txt")
