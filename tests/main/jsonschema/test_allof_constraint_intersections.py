"""End-to-end coverage for object allOf bound and enum intersections."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from datamodel_code_generator import InputFileType, SchemaParseError, generate
from datamodel_code_generator.__main__ import Exit
from datamodel_code_generator.enums import AllOfClassHierarchy, AllOfMergeMode
from tests.conftest import assert_output
from tests.main.conftest import (
    DATA_PATH,
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
    ("fixture", "mode", "field_constraints", "hierarchy"),
    [
        ("inline", "constraints", True, "if-no-conflict"),
        ("refs", "constraints", True, "if-no-conflict"),
        ("inline", "all", True, "if-no-conflict"),
        ("refs", "all", True, "if-no-conflict"),
        ("inline", "constraints", False, "if-no-conflict"),
        ("refs", "constraints", False, "if-no-conflict"),
        ("ordinary", "constraints", True, "if-no-conflict"),
        ("ordinary", "all", True, "if-no-conflict"),
        ("inline", "none", True, "if-no-conflict"),
        ("refs", "none", True, "if-no-conflict"),
        ("refs", "constraints", True, "always"),
        ("ordinary", "none", True, "if-no-conflict"),
        ("complex", "constraints", True, "if-no-conflict"),
        ("complex", "none", True, "if-no-conflict"),
    ],
)
def test_allof_constraint_intersections(
    output_file: Path, fixture: str, mode: str, field_constraints: bool, hierarchy: str, entry_point: str
) -> None:
    """Intersect enabled object merges while preserving explicit opt-outs and ordinary metadata."""
    input_path = JSON_SCHEMA_DATA_PATH / "allof_constraint_intersections" / f"{fixture}.json"
    expected_mode = "constraints" if mode == "all" or fixture == "ordinary" else mode
    expected_name = f"{fixture}_{expected_mode}_{'field' if field_constraints else 'constrained'}_{hierarchy}"
    if entry_point == "api":
        options = {
            "input_file_type": InputFileType.JsonSchema,
            "field_constraints": field_constraints,
            "allof_merge_mode": AllOfMergeMode(mode),
            "allof_class_hierarchy": AllOfClassHierarchy(hierarchy),
            "disable_timestamp": True,
        }
        run_generate_and_assert(
            input_=json.loads(input_path.read_text(encoding="utf-8")),
            expected_file=EXPECTED_JSON_SCHEMA_PATH / "allof_constraint_intersections" / f"{expected_name}_api.py",
            assert_input_unchanged=True,
            **options,
        )
        run_generate_file_and_assert(
            input_path=input_path,
            output_path=output_file,
            assert_func=assert_file_content,
            expected_file=f"allof_constraint_intersections/{expected_name}.py",
            **options,
        )
    else:
        run_main_and_assert(
            input_path=input_path,
            output_path=output_file,
            input_file_type="jsonschema",
            assert_func=assert_file_content,
            expected_file=f"allof_constraint_intersections/{expected_name}.py",
            extra_args=[
                "--disable-timestamp",
                "--allof-merge-mode",
                mode,
                "--allof-class-hierarchy",
                hierarchy,
                *(["--field-constraints"] if field_constraints else []),
            ],
            force_exec_validation=True,
        )

    payloads = json.loads((DATA_PATH / "payloads" / "allof_constraint_intersections.json").read_text(encoding="utf-8"))[
        fixture if fixture in {"ordinary", "complex"} else "target"
    ]
    valid = {name: payload["valid"] for name, payload in payloads.items()}
    if mode == "none" or hierarchy == "always":
        assert_generated_model_json_validation(
            output_file,
            module_name="allof_constraint_intersections",
            model_name="Root",
            valid_json=json.dumps(valid),
            invalid_json="[]",
            expected_error_type="model_type",
        )
    else:
        for name, payload in payloads.items():
            for invalid in payload["invalid"]:
                assert_generated_model_json_validation(
                    output_file,
                    module_name="allof_constraint_intersections",
                    model_name="Root",
                    valid_json=json.dumps(valid),
                    invalid_json=json.dumps({**valid, name: invalid}),
                    expected_error_type=payload["error_type"],
                    expected_attribute_path=payload["attribute_path"],
                    expected_attribute_value=payload.get("attribute_value", payload["valid"]),
                )


@pytest.mark.parametrize("fixture", ["empty_enum", "boolean_number_enum", "complex_empty_enum", "empty_enums"])
@pytest.mark.parametrize("entry_point", ["api", "cli"])
def test_allof_empty_enum_intersection(
    output_file: Path, capsys: pytest.CaptureFixture[str], fixture: str, entry_point: str
) -> None:
    """Report unsupported empty intersections instead of widening them to unconstrained values."""
    input_path = DATA_PATH / "parser" / "jsonschema" / "allof_constraint_intersections" / f"{fixture}.json"
    expected_error = EXPECTED_JSON_SCHEMA_PATH / "allof_constraint_intersections" / "empty_enum.txt"
    if entry_point == "api":
        with pytest.raises(SchemaParseError) as error:
            generate(input_path, input_file_type=InputFileType.JsonSchema)
        assert_output(f"{error.value}\n", expected_error)
    else:
        run_main_and_assert(
            input_path=input_path,
            output_path=output_file,
            input_file_type="jsonschema",
            expected_exit=Exit.ERROR,
            capsys=capsys,
            expected_stderr=expected_error.read_text(encoding="utf-8"),
            output_should_not_exist=True,
        )
