"""Preserve root constraints across class and alias output options."""

from __future__ import annotations

import json
import subprocess
import sys
from contextlib import ExitStack
from typing import TYPE_CHECKING

import pytest
from jsonschema import Draft7Validator
from pydantic_core import SchemaError

from datamodel_code_generator import InputFileType, generate
from tests.conftest import assert_inputs_not_mutated, assert_output
from tests.main.conftest import (
    DATA_PATH,
    JSON_SCHEMA_DATA_PATH,
    _default_formatter_generate_options,
    _generated_model,
    run_main_and_assert,
)
from tests.main.jsonschema.conftest import EXPECTED_JSON_SCHEMA_PATH

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize("case", json.loads((DATA_PATH / "python/root_alias_constraints/cases.json").read_text()))
@pytest.mark.parametrize(("field_constraints", "use_annotated"), [(False, False), (True, False), (True, True)])
@pytest.mark.parametrize("use_alias", [False, True])
def test_root_alias_constraints(
    output_file: Path, entrypoint: str, case: str, *, field_constraints: bool, use_annotated: bool, use_alias: bool
) -> None:
    """Compare real CLI/API bytes and native acceptance with all option combinations."""
    source = JSON_SCHEMA_DATA_PATH / "root_alias_constraints" / f"{case}.json"
    expected = EXPECTED_JSON_SCHEMA_PATH / "root_alias_constraints"
    filename = f"{case}_{int(field_constraints)}_{int(use_annotated)}_{int(use_alias)}.py"
    options = {
        "field_constraints": field_constraints,
        "use_annotated": use_annotated,
        "use_root_model_type_alias": use_alias,
    }
    if entrypoint == "cli":
        args = ["--disable-timestamp"]
        args.extend(f"--{name.replace('_', '-')}" for name, enabled in options.items() if enabled)
        run_main_and_assert(
            input_path=source,
            output_path=output_file,
            input_file_type="jsonschema",
            expected_file=expected / filename,
            extra_args=args,
        )
    else:
        schema = json.loads(source.read_text())
        with assert_inputs_not_mutated({"schema": schema}):
            generate(
                schema,
                **_default_formatter_generate_options({
                    "input_file_type": InputFileType.JsonSchema,
                    "input_filename": source.name,
                    "output": output_file,
                    "disable_timestamp": True,
                    **options,
                }),
            )
        assert_output(output_file.read_text(encoding="utf-8"), expected / filename)
    if case == "lookaround":
        try:
            with _generated_model(
                DATA_PATH / "python/root_alias_constraints/native_lookaround.py",
                "native_lookaround_control",
                "NativeLookaround",
            ) as native_model:
                native_model.model_validate("a")
        except SchemaError as native_error:
            assert_output(str(native_error) + "\n", expected / "lookaround_native_error.txt")
            with ExitStack() as stack, pytest.raises(SchemaError) as generated_error:
                stack.enter_context(_generated_model(output_file, "generated_lookaround_probe", "Root"))
            assert_output(str(generated_error.value) + "\n", expected / "lookaround_generated_error.txt")
            validator = Draft7Validator(json.loads(source.read_text()))
            payloads = json.loads((DATA_PATH / "python/root_alias_constraints/cases.json").read_text())[case]
            assert_output(
                json.dumps([{"payload": p, "native": validator.is_valid(p)} for p in payloads], indent=2) + "\n",
                expected / "lookaround_native.txt",
            )
            return
    result = subprocess.run(
        [sys.executable, str(DATA_PATH / "python/root_alias_constraints/runtime.py"), str(source), str(output_file)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert_output(result.stdout, expected / f"{case}_runtime.txt")
