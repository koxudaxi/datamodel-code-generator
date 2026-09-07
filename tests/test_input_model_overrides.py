"""CLI/API regressions for Python inherited field replacement."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from datamodel_code_generator import DataModelType, Formatter, GenerateConfig, InputFileType, generate
from datamodel_code_generator.input_model import load_model_schema
from tests.conftest import BUILTIN_FORMATTER_VALUE, TEST_DEFAULT_FORMATTER_ENV, assert_inputs_not_mutated, assert_output
from tests.data.python.input_model import inherited_overrides
from tests.data.python.input_model.inherited_override_runtime import CASES
from tests.main.conftest import _generated_model, run_main_with_args

EXPECTED = Path(__file__).parent / "data" / "expected" / "main" / "input_model" / "inherited_overrides"
INPUT_MODULE = "tests.data.python.input_model.inherited_overrides"


@pytest.mark.parametrize("model_name", CASES)
@pytest.mark.parametrize("entrypoint", ["cli", "api"])
def test_input_model_inherited_overrides(model_name: str, entrypoint: str, tmp_path: Path) -> None:
    """Preserve effective child fields, generated base classes, and native behavior."""
    source = f"{INPUT_MODULE}:{model_name}"
    output = tmp_path / "output.py"
    use_builtin = os.environ.get(TEST_DEFAULT_FORMATTER_ENV) == BUILTIN_FORMATTER_VALUE
    formatters = [Formatter.BUILTIN] if use_builtin else [Formatter.ISORT, Formatter.BLACK]
    schema_path = (
        Path(__file__).parent / "data" / "jsonschema" / "input_model_caller_override_extension.json"
        if model_name == "RawSchemaIntersection"
        else None
    )
    input_args = (
        ["--input", str(schema_path), "--input-file-type", "jsonschema"] if schema_path else ["--input-model", source]
    )
    if entrypoint == "cli":
        run_main_with_args(
            [
                *input_args,
                "--output",
                str(output),
                "--disable-timestamp",
                "--strict-nullable",
                "--generate-schema-validators",
                "--formatters",
                *(formatter.value for formatter in formatters),
            ],
            use_parsed_source_cache=False,
        )
    else:
        schema = (
            json.loads(schema_path.read_text())
            if schema_path
            else load_model_schema([source], InputFileType.JsonSchema)
        )
        with assert_inputs_not_mutated(schema):
            generate(
                deepcopy(schema),
                config=GenerateConfig(
                    input_file_type=InputFileType.JsonSchema,
                    input_filename=schema_path.name if schema_path else "<stdin>",
                    output_model_type=DataModelType.PydanticV2BaseModel,
                    disable_timestamp=True,
                    strict_nullable=True,
                    generate_schema_validators=True,
                    formatters=formatters,
                    output=output,
                ),
            )
    assert_output(output.read_text(), EXPECTED / f"{model_name}{'_builtin' if use_builtin else ''}.py")
    schema = (
        json.loads(schema_path.read_text()) if schema_path else load_model_schema([source], InputFileType.JsonSchema)
    )
    assert_output(json.dumps(schema, indent=2), EXPECTED / f"{model_name}_schema.txt")
    records = []
    with _generated_model(output, "_generated_inherited_overrides", model_name) as generated:
        records.append({
            "bases": [base.__name__ for base in generated.__bases__],
            "fields": list(generated.model_fields),
        })
        for payload in CASES[model_name]:
            observations = {"payload": payload}
            for name, model in (("source", getattr(inherited_overrides, model_name)), ("generated", generated)):
                with assert_inputs_not_mutated(payload):
                    try:
                        result = model.model_validate(payload)
                    except ValidationError as error:
                        observations[name] = {"errors": [item["type"] for item in error.errors()]}
                    else:
                        observations[name] = result.model_dump(mode="json", by_alias=True)
            records.append(observations)
    assert_output(json.dumps(records, indent=2), EXPECTED / f"{model_name}_runtime.txt")
