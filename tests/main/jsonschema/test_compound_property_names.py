"""Validate compound string keys through the CLI, API, and native schema oracle."""

from __future__ import annotations

import json
from contextlib import nullcontext
from typing import TYPE_CHECKING

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from datamodel_code_generator import InputFileType, SchemaParseError, generate, generate_dynamic_models
from datamodel_code_generator.__main__ import Exit
from datamodel_code_generator.config import GenerateConfig
from datamodel_code_generator.model.pydantic_v2.version import PYDANTIC_V2_ROOT_MODEL_DICT_KEY_FORWARD_REF_NEEDS_SORTING
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
from tests.main.payload_validation.constants import COMPOUND_PROPERTY_NAMES_DIAGNOSTIC_CASES

if TYPE_CHECKING:
    from pathlib import Path

INPUTS = JSON_SCHEMA_DATA_PATH / "compound_property_names"
PAYLOADS = DATA_PATH / "payloads" / "compound_property_names"
EXPECTED = EXPECTED_JSON_SCHEMA_PATH / "compound_property_names"
CASES = json.loads((PAYLOADS / "cases.json").read_text())


@pytest.mark.parametrize("name", CASES)
@pytest.mark.parametrize("constraints", [False, True])
@pytest.mark.parametrize("entry", ["cli", "api", "dynamic"])
def test_compound_property_name_generation(name: str, constraints: bool, entry: str, output_file: Path) -> None:
    """Preserve string keys, native acceptance, and deterministic generated output."""
    input_path = INPUTS / f"{name}.json"
    suffix = (
        "_legacy_pydantic"
        if PYDANTIC_V2_ROOT_MODEL_DICT_KEY_FORWARD_REF_NEEDS_SORTING and name in {"enum_refs", "ref_then_any"}
        else ""
    )
    expected_file = f"compound_property_names/{name}_{int(constraints)}{suffix}.py"
    if entry == "cli":
        run_main_and_assert(
            input_path=input_path,
            output_path=output_file,
            input_file_type="jsonschema",
            extra_args=[
                "--custom-file-header",
                "# Compound property names",
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
            custom_file_header="# Compound property names",
            field_constraints=constraints,
            assert_func=assert_file_content,
            expected_file=expected_file,
        )
    schema = json.loads(input_path.read_text())
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    payloads = json.loads((PAYLOADS / f"{name}.json").read_text())
    assert_output(
        json.dumps([validator.is_valid(value) for value in payloads], indent=2) + "\n", EXPECTED / f"{name}_runtime.txt"
    )
    actual = []
    context = (
        nullcontext(
            generate_dynamic_models(schema, config=GenerateConfig(field_constraints=constraints), cache_size=0)["Root"]
        )
        if entry == "dynamic"
        else _generated_model(output_file, "compound_keys", "Root")
    )
    with context as model:
        for value in payloads:
            if validator.is_valid(value):
                model.model_validate(value)
                actual.append(True)
            else:
                with pytest.raises(ValidationError):
                    model.model_validate(value)
                actual.append(False)
    assert_output(json.dumps(actual, indent=2) + "\n", EXPECTED / f"{name}_runtime.txt")


@pytest.mark.parametrize(("case_id", "expected_file"), COMPOUND_PROPERTY_NAMES_DIAGNOSTIC_CASES.items())
@pytest.mark.parametrize("constraints", [False, True])
@pytest.mark.parametrize("entry", ["cli", "api"])
def test_unrepresentable_compound_property_names(
    case_id: str,
    expected_file: str,
    constraints: bool,
    entry: str,
    output_file: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Diagnose unsupported key intersections instead of emitting invalid models."""
    input_path = DATA_PATH / case_id
    expected = EXPECTED_JSON_SCHEMA_PATH / expected_file
    Draft202012Validator.check_schema(json.loads(input_path.read_text(encoding="utf-8")))
    if entry == "cli":
        run_main_and_assert(
            input_path=input_path,
            output_path=output_file,
            input_file_type="jsonschema",
            extra_args=["--field-constraints"] if constraints else [],
            expected_exit=Exit.ERROR,
            output_should_not_exist=True,
            capsys=capsys,
            expected_stderr_contains=expected.read_text().strip(),
        )
    else:
        with pytest.raises(SchemaParseError) as error:
            generate(input_path, input_file_type=InputFileType.JsonSchema, field_constraints=constraints)
        assert_output(str(error.value) + "\n", expected)
