"""Diagnose impossible type intersections without changing compatible schemas."""

from __future__ import annotations

import json
import warnings
from typing import TYPE_CHECKING

import pytest
from jsonschema.validators import validator_for
from pydantic import ValidationError

from datamodel_code_generator import AllOfMergeMode, InputFileType, SchemaParseError, generate
from datamodel_code_generator.__main__ import Exit
from tests.conftest import assert_inputs_not_mutated, assert_output
from tests.main.conftest import (
    DATA_PATH,
    _default_formatter_generate_options,
    _generated_model,
    run_main_with_args,
)
from tests.main.jsonschema.conftest import EXPECTED_JSON_SCHEMA_PATH
from tests.main.payload_validation.constants import DISJOINT_ALLOF_DIAGNOSTIC_CASES

if TYPE_CHECKING:
    from pathlib import Path

EXPECTED = EXPECTED_JSON_SCHEMA_PATH / "disjoint_allof_types"
CASES = json.loads((EXPECTED / "cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize(("case_id", "case"), DISJOINT_ALLOF_DIAGNOSTIC_CASES.items())
@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize("merge_mode", list(AllOfMergeMode))
@pytest.mark.parametrize("field_constraints", [False, True])
def test_disjoint_allof_diagnostics(
    output_file: Path,
    capsys: pytest.CaptureFixture[str],
    case_id: str,
    case: str,
    entrypoint: str,
    merge_mode: AllOfMergeMode,
    field_constraints: bool,
) -> None:
    """Keep every diagnostic input assigned to real CLI/API and native-schema checks."""
    source = DATA_PATH / case_id
    schema = json.loads(source.read_text(encoding="utf-8"))
    validator_class = validator_for(schema)
    validator_class.check_schema(schema)
    validator = validator_class(schema)
    assert_output(
        json.dumps([{"payload": p, "native": validator.is_valid(p)} for p in CASES[case]["payloads"]], indent=2) + "\n",
        EXPECTED / f"{case}_native.txt",
    )
    with assert_inputs_not_mutated(schema):
        if entrypoint == "cli":
            run_main_with_args(
                [
                    "--input",
                    str(source),
                    "--output",
                    str(output_file),
                    "--input-file-type",
                    "jsonschema",
                    "--allof-merge-mode",
                    merge_mode.value,
                    *(["--field-constraints"] if field_constraints else []),
                ],
                expected_exit=Exit.ERROR,
                capsys=capsys,
                expected_stderr=(EXPECTED / f"{case}_cli_error.txt").read_text(encoding="utf-8"),
            )
        else:
            with pytest.raises(SchemaParseError) as error:
                generate(
                    schema,
                    input_file_type=InputFileType.JsonSchema,
                    output=output_file,
                    allof_merge_mode=merge_mode,
                    field_constraints=field_constraints,
                )
            assert_output(str(error.value) + "\n", EXPECTED / f"{case}_api_error.txt")


@pytest.mark.parametrize("case", [case for case, spec in CASES.items() if not spec["error"]])
@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize("merge_mode", list(AllOfMergeMode))
@pytest.mark.parametrize("field_constraints", [False, True])
@pytest.mark.parametrize("custom_template", [False, True])
def test_compatible_allof_types(
    output_file: Path,
    case: str,
    entrypoint: str,
    merge_mode: AllOfMergeMode,
    field_constraints: bool,
    custom_template: bool,
) -> None:
    """Compare compatible code and runtime with unchanged predecessor-generated fixtures."""
    source = DATA_PATH / "jsonschema" / CASES[case]["source"]
    schema = json.loads(source.read_text(encoding="utf-8"))
    validator_class = validator_for(schema)
    validator_class.check_schema(schema)
    validator = validator_class(schema)
    templates = DATA_PATH / "templates_disjoint_allof"
    key = f"{merge_mode.value}_{int(field_constraints)}_{int(custom_template)}"
    with assert_inputs_not_mutated(schema), warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always", UserWarning)
        if entrypoint == "cli":
            run_main_with_args([
                "--input",
                str(source),
                "--output",
                str(output_file),
                "--input-file-type",
                "jsonschema",
                "--disable-timestamp",
                "--custom-file-header-path",
                str(DATA_PATH / "custom_file_header.txt"),
                "--allof-merge-mode",
                merge_mode.value,
                *(["--field-constraints"] if field_constraints else []),
                *(["--custom-template-dir", str(templates)] if custom_template else []),
            ])
        else:
            generate(
                schema,
                **_default_formatter_generate_options({
                    "input_file_type": InputFileType.JsonSchema,
                    "output": output_file,
                    "disable_timestamp": True,
                    "custom_file_header_path": DATA_PATH / "custom_file_header.txt",
                    "allof_merge_mode": merge_mode,
                    "field_constraints": field_constraints,
                    "custom_template_dir": templates if custom_template else None,
                }),
            )
    assert_output(output_file.read_text(encoding="utf-8"), EXPECTED / CASES[case]["outputs"][key])
    assert_output(json.dumps([str(w.message) for w in captured]) + "\n", EXPECTED / "no_warnings.txt")
    records = []
    with _generated_model(output_file, "compatible_allof", CASES[case]["model"]) as model:
        for payload in CASES[case]["payloads"]:
            with assert_inputs_not_mutated({"payload": payload}):
                try:
                    model.model_validate(payload)
                    accepted = True
                except ValidationError:
                    accepted = False
            records.append({"payload": payload, "native": validator.is_valid(payload), "generated": accepted})
    assert_output(json.dumps(records, indent=2) + "\n", EXPECTED / f"{case}_runtime.txt")
