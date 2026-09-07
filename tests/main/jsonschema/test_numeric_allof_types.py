"""Compare numeric allOf type intersections with the original schema."""

from __future__ import annotations

import json
import warnings
from contextlib import ExitStack
from typing import TYPE_CHECKING

import pytest
from jsonschema import Draft7Validator
from pydantic import ValidationError

from datamodel_code_generator import AllOfMergeMode, InputFileType, SchemaParseError, generate
from datamodel_code_generator.__main__ import Exit
from tests.conftest import assert_inputs_not_mutated, assert_output
from tests.main.conftest import (
    DATA_PATH,
    JSON_SCHEMA_DATA_PATH,
    _default_formatter_generate_options,
    _generated_model,
    run_main_with_args,
)
from tests.main.jsonschema.conftest import EXPECTED_JSON_SCHEMA_PATH

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize("case", json.loads((DATA_PATH / "python/numeric_allof_types/cases.json").read_text()))
@pytest.mark.parametrize("merge_mode", list(AllOfMergeMode))
@pytest.mark.parametrize("field_constraints", [False, True])
def test_numeric_allof_types(
    output_file: Path, entrypoint: str, case: str, merge_mode: AllOfMergeMode, *, field_constraints: bool
) -> None:
    """Preserve order and intersect numeric types independently of constraint merge mode."""
    source = JSON_SCHEMA_DATA_PATH / "numeric_allof_types" / f"{case}.json"
    expected = EXPECTED_JSON_SCHEMA_PATH / "numeric_allof_types"
    filename = f"{case}_{merge_mode.value}_{int(field_constraints)}.py"
    schema = json.loads(source.read_text())
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always", UserWarning)
        if entrypoint == "cli":
            args = ["--disable-timestamp", "--allof-merge-mode", merge_mode.value]
            if field_constraints:
                args.append("--field-constraints")
            run_main_with_args([
                "--input",
                str(source),
                "--output",
                str(output_file),
                "--input-file-type",
                "jsonschema",
                *args,
            ])
        else:
            with assert_inputs_not_mutated({"schema": schema}):
                generate(
                    schema,
                    **_default_formatter_generate_options({
                        "input_file_type": InputFileType.JsonSchema,
                        "input_filename": source.name,
                        "output": output_file,
                        "disable_timestamp": True,
                        "allof_merge_mode": merge_mode,
                        "field_constraints": field_constraints,
                    }),
                )
        assert_output(output_file.read_text(encoding="utf-8"), expected / filename)
    assert_output(
        json.dumps([str(item.message) for item in captured], indent=2) + "\n", expected / f"{case}_warnings.txt"
    )
    payloads = json.loads((DATA_PATH / "python/numeric_allof_types/cases.json").read_text())[case]
    validator = Draft7Validator(schema)
    if case in json.loads((DATA_PATH / "python/numeric_allof_types/native_null_cases.json").read_text()):
        try:
            with _generated_model(
                DATA_PATH / "python/numeric_allof_types/native_null.py", "native_null_control", "NativeNull"
            ) as native_model:
                native_model.model_validate(None)
        except AssertionError as native_error:
            assert_output(str(native_error) + "\n", expected / "native_null_error.txt")
            with ExitStack() as stack, pytest.raises(AssertionError) as generated_error:
                stack.enter_context(_generated_model(output_file, "numeric_allof_type_probe", "Root"))
            assert_output(str(generated_error.value) + "\n", expected / "native_null_error.txt")
            assert_output(
                json.dumps([{"payload": p, "native": validator.is_valid(p)} for p in payloads], indent=2) + "\n",
                expected / f"{case}_native.txt",
            )
            return
    results = []
    with _generated_model(output_file, "numeric_allof_type_probe", "Root") as model:
        for payload in payloads:
            try:
                model.model_validate(payload)
                accepted = True
            except ValidationError:
                accepted = False
            results.append({"payload": payload, "native": validator.is_valid(payload), "generated": accepted})
    assert_output(json.dumps(results, indent=2) + "\n", expected / f"{case}_runtime.txt")


@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize("case", json.loads((DATA_PATH / "python/numeric_allof_types/errors.json").read_text()))
@pytest.mark.parametrize("merge_mode", list(AllOfMergeMode))
def test_numeric_allof_empty_intersection(
    output_file: Path, capsys: pytest.CaptureFixture[str], entrypoint: str, case: str, merge_mode: AllOfMergeMode
) -> None:
    """Reject an empty numeric/null intersection instead of widening its type."""
    source = JSON_SCHEMA_DATA_PATH / "numeric_allof_types" / f"{case}.json"
    schema = json.loads(source.read_text())
    validator = Draft7Validator(schema)
    payloads = json.loads((DATA_PATH / "python/numeric_allof_types/errors.json").read_text())[case]
    assert_output(
        json.dumps([{"payload": payload, "native": validator.is_valid(payload)} for payload in payloads], indent=2)
        + "\n",
        EXPECTED_JSON_SCHEMA_PATH / "numeric_allof_types" / f"{case}_runtime.txt",
    )
    message = "allOf numeric/null type constraints have no common value"
    if entrypoint == "cli":
        run_main_with_args(
            ["--input", str(source), "--output", str(output_file), "--allof-merge-mode", merge_mode.value],
            expected_exit=Exit.ERROR,
            capsys=capsys,
            expected_stderr_contains=message,
        )
    else:
        with assert_inputs_not_mutated({"schema": schema}), pytest.raises(SchemaParseError, match=message):
            generate(schema, input_file_type=InputFileType.JsonSchema, output=output_file, allof_merge_mode=merge_mode)
