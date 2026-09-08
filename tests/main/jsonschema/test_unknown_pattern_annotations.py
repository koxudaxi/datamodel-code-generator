"""Unknown annotations are inert only for proven standard pattern adapters."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from datamodel_code_generator import DataModelType, Formatter, GenerateConfig, InputFileType, generate
from tests.conftest import assert_inputs_not_mutated, assert_output
from tests.main.conftest import JSON_SCHEMA_DATA_PATH, _generated_model, run_main_with_args
from tests.main.jsonschema.conftest import EXPECTED_JSON_SCHEMA_PATH

if TYPE_CHECKING:
    from pathlib import Path

FIXTURES = JSON_SCHEMA_DATA_PATH / "unknown_pattern_annotations"
CASES = json.loads((FIXTURES / "cases.json").read_text())
EXPECTED = EXPECTED_JSON_SCHEMA_PATH / "unknown_pattern_annotations"


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("field_constraints", [False, True])
@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize("formatter", ["builtin", "external"])
def test_unknown_pattern_root_annotations(
    tmp_path: Path, case: str, enabled: bool, field_constraints: bool, entrypoint: str, formatter: str
) -> None:
    """Preserve external bytes and metadata while comparing native JSON/Python acceptance."""
    record = CASES[case]
    source = FIXTURES / f"{record['source']}.json"
    output = tmp_path / "output.py"
    formatters = ["builtin"] if formatter == "builtin" else ["black", "isort"]
    if entrypoint == "cli":
        options = []
        for key, value in record["config"].items():
            options.extend(
                [f"--{key.replace('_', '-')}", *value]
                if isinstance(value, list)
                else [f"--{key.replace('_', '-')}", value]
            )
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
            *options,
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
                formatters=[Formatter(value) for value in formatters],
                **record["config"],
            ),
        )
    mode = f"{enabled}_{field_constraints}_{formatter}"
    assert_output(output.read_text(), EXPECTED / record["code_names"][mode])
    schema = json.loads(source.read_text())
    Draft202012Validator.check_schema(schema)
    native = Draft202012Validator(schema)
    records = []
    with _generated_model(output, "unknown_pattern_generated", "Root") as model:
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
        metadata = {
            key: value for key, value in model.model_json_schema().items() if key.startswith("x-") or key == "notes"
        }
    assert_output(
        json.dumps({"values": records, "metadata": metadata}, indent=2),
        EXPECTED / f"{case}_{enabled}_{field_constraints}_runtime.txt",
    )


@pytest.mark.parametrize("custom", ["parser", "parser_other", "schema", "model", "root", "field", "manager"])
def test_custom_pattern_annotation_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, custom: str) -> None:
    """Keep existing custom extension code, raw metadata and accepted dumps intact."""
    from datamodel_code_generator.parser.jsonschema import JsonSchemaParser
    from tests.data.python.unknown_pattern_annotations import (
        AttributesParser,
        CustomField,
        CustomManager,
        CustomModel,
        CustomRoot,
        CustomSchema,
    )

    options = {
        "model": {"data_model_type": CustomModel},
        "root": {"data_model_root_type": CustomRoot},
        "field": {"data_model_field_type": CustomField},
        "manager": {"data_type_manager_type": CustomManager},
    }.get(custom, {})
    if custom == "schema":
        monkeypatch.setattr(JsonSchemaParser, "SCHEMA_OBJECT_TYPE", CustomSchema)
    parser_type = AttributesParser if custom.startswith("parser") else JsonSchemaParser
    source = FIXTURES / ("other_annotation.json" if custom == "parser_other" else "annotation.json")
    parser = parser_type(source, generate_schema_validators=True, formatters=[Formatter.BUILTIN], **options)
    output = tmp_path / "output.py"
    output.write_text(parser.parse())
    assert_output(output.read_text(), EXPECTED / f"custom_{custom}.py")
    contexts = [value["extensions"] for value in parser.extra_template_data.values() if "extensions" in value]
    records = []
    schema = json.loads(source.read_text())
    Draft202012Validator.check_schema(schema)
    with _generated_model(output, "custom_pattern_annotation", "Root") as model:
        for payload in CASES["annotation"]["payloads"]:
            record = {"native": Draft202012Validator(schema).is_valid(payload)}
            with assert_inputs_not_mutated({"payload": payload}):
                try:
                    record["generated"] = model.model_validate(payload).model_dump(mode="json")
                except ValidationError:
                    record["generated"] = "rejected"
            records.append(record)
    assert_output(
        json.dumps({"contexts": contexts, "values": records}, indent=2), EXPECTED / f"custom_{custom}_runtime.txt"
    )
