"""End-to-end coverage for integer precision in numeric constraints."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from datamodel_code_generator import Formatter, InputFileType
from datamodel_code_generator.enums import StrictTypes
from datamodel_code_generator.model._constraints import Constraints
from datamodel_code_generator.parser.jsonschema import JsonSchemaObject
from tests.main.conftest import (
    JSON_DATA_PATH,
    JSON_SCHEMA_DATA_PATH,
    assert_generated_model_json_validation,
    run_generate_and_assert,
    run_generate_file_and_assert,
    run_main_and_assert,
)
from tests.main.jsonschema.conftest import EXPECTED_JSON_SCHEMA_PATH, assert_file_content

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("entry_point", ["api", "cli"])
@pytest.mark.parametrize(
    ("fixture", "field_constraints", "strict", "expected_name"),
    [
        ("large", True, False, "large_field"),
        ("large", False, False, "large_constrained"),
        ("large", True, True, "large_strict"),
        ("ordinary", True, False, "ordinary_field"),
        ("ordinary", False, False, "ordinary_constrained"),
        ("draft4", True, False, "draft4_field"),
        ("draft4", False, False, "draft4_constrained"),
    ],
)
def test_numeric_constraint_precision(
    output_file: Path, entry_point: str, fixture: str, field_constraints: bool, strict: bool, expected_name: str
) -> None:
    """Retain large integer constraints while preserving ordinary floats and Draft 4 booleans."""
    input_path = JSON_SCHEMA_DATA_PATH / "numeric_constraint_precision" / f"{fixture}.json"
    if entry_point == "api":
        options = {
            "input_file_type": InputFileType.JsonSchema,
            "field_constraints": field_constraints,
            "strict_types": [StrictTypes.int] if strict else [],
            "disable_timestamp": True,
            "formatters": [Formatter.BUILTIN],
        }
        run_generate_and_assert(
            input_=json.loads(input_path.read_text(encoding="utf-8")),
            expected_file=EXPECTED_JSON_SCHEMA_PATH / "numeric_constraint_precision" / f"{expected_name}_api.py",
            assert_input_unchanged=True,
            **options,
        )
        run_generate_file_and_assert(
            input_path=input_path,
            output_path=output_file,
            assert_func=assert_file_content,
            expected_file=f"numeric_constraint_precision/{expected_name}.py",
            **options,
        )
    else:
        run_main_and_assert(
            input_path=input_path,
            output_path=output_file,
            input_file_type="jsonschema",
            assert_func=assert_file_content,
            expected_file=f"numeric_constraint_precision/{expected_name}.py",
            extra_args=[
                "--disable-timestamp",
                "--formatters",
                "builtin",
                *(["--field-constraints"] if field_constraints else []),
                *(["--strict-types", "int"] if strict else []),
            ],
            force_exec_validation=True,
        )

    payloads = json.loads(
        (JSON_DATA_PATH / "numeric_constraint_precision" / f"{fixture}_payloads.json").read_text(encoding="utf-8")
    )
    valid_payload = {name: payload["valid"] for name, payload in payloads.items()}
    for name, payload in payloads.items():
        assert_generated_model_json_validation(
            output_file,
            module_name="numeric_constraint_precision",
            model_name="NumericConstraints",
            valid_json=json.dumps(valid_payload),
            invalid_json=json.dumps({**valid_payload, name: payload["invalid"]}),
            expected_error_type=payload["error_type"],
            expected_attribute_path=payload.get("attribute_path", [name]),
            expected_attribute_value=payload["valid"],
        )


@pytest.mark.parametrize("fixture", ["large", "ordinary"])
@pytest.mark.parametrize("serialization", ["python", "json"])
@pytest.mark.parametrize("constraint_model", ["schema", "constraints"])
def test_numeric_constraint_serialization(fixture: str, serialization: str, constraint_model: str) -> None:
    """Preserve numeric constraints through schema model Python and JSON serialization."""
    input_path = JSON_SCHEMA_DATA_PATH / "numeric_constraint_precision" / f"{fixture}.json"
    schema = json.loads(input_path.read_text(encoding="utf-8"))
    for name, value in schema["properties"].items():
        if constraint_model == "schema":
            parsed = JsonSchemaObject.model_validate(value)
        elif "multipleOf" in value:
            parsed = Constraints.model_validate({"multipleOf": value["multipleOf"]})
        else:
            continue
        serialized = (
            json.loads(parsed.model_dump_json(exclude_unset=True, by_alias=True))
            if serialization == "json"
            else parsed.model_dump(exclude_unset=True, by_alias=True)
        )
        schema["properties"][name] = serialized if constraint_model == "schema" else {**value, **serialized}
    run_generate_and_assert(
        input_=schema,
        expected_file=EXPECTED_JSON_SCHEMA_PATH / "numeric_constraint_precision" / f"{fixture}_field_api.py",
        assert_input_unchanged=True,
        input_file_type=InputFileType.JsonSchema,
        field_constraints=True,
        disable_timestamp=True,
        formatters=[Formatter.BUILTIN],
    )
