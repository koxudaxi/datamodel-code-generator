"""Preserve root constraints across class and alias output options."""

from __future__ import annotations

import json
import subprocess
import sys
from contextlib import ExitStack
from typing import TYPE_CHECKING

import black
import pytest
from jsonschema import Draft7Validator
from pydantic_core import SchemaError

from datamodel_code_generator import InputFileType, generate
from datamodel_code_generator.model.base import TEMPLATE_DIR
from tests.conftest import assert_inputs_not_mutated, assert_output
from tests.main.conftest import (
    DATA_PATH,
    JSON_SCHEMA_DATA_PATH,
    _default_formatter_generate_options,
    _generated_model,
    _uses_builtin_test_default_formatter,
    assert_generated_model_json_validation,
    run_main_and_assert,
)
from tests.main.jsonschema.conftest import EXPECTED_JSON_SCHEMA_PATH

if TYPE_CHECKING:
    from pathlib import Path


LEGACY_API_OUTPUTS = {("plain_1_1_0.py", True): "plain_1_1_0_black23.py"}


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
        filename = LEGACY_API_OUTPUTS.get(
            (filename, int(black.__version__.split(".")[0]) < 24 and not _uses_builtin_test_default_formatter()),
            filename,
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


@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize("case", ["integer", "multiple"])
@pytest.mark.parametrize("template_mode", ["custom", "custom_alias", "partial", "missing", "builtin", "builtin_alias"])
@pytest.mark.parametrize(("field_constraints", "use_annotated"), [(False, False), (True, False), (True, True)])
def test_root_alias_custom_template_constraints(
    tmp_path: Path,
    output_file: Path,
    entrypoint: str,
    template_mode: str,
    case: str,
    *,
    field_constraints: bool,
    use_annotated: bool,
) -> None:
    """Preserve an existing custom alias while fixing known built-in alias constraints."""
    source = JSON_SCHEMA_DATA_PATH / "root_alias_constraints" / f"{case}.json"
    expected = EXPECTED_JSON_SCHEMA_PATH / "root_alias_constraints"
    custom_template = DATA_PATH / "templates/root_alias_constraints"
    match template_mode:
        case "custom":
            template_dir = custom_template
        case "builtin":
            template_dir = TEMPLATE_DIR
        case "custom_alias" | "builtin_alias":
            template_dir = tmp_path / "linked-templates"
            template_dir.symlink_to(
                custom_template if template_mode == "custom_alias" else TEMPLATE_DIR, target_is_directory=True
            )
        case "partial":
            template_dir = tmp_path / "partial-templates"
            (template_dir / "pydantic_v2").mkdir(parents=True)
        case _:
            template_dir = tmp_path / "missing-templates"
    filename = (
        f"{case}_custom_{int(field_constraints)}_{int(use_annotated)}.py"
        if template_mode.startswith("custom")
        else f"{case}_{int(field_constraints)}_{int(use_annotated)}_1.py"
    )
    options = {
        "field_constraints": field_constraints,
        "use_annotated": use_annotated,
        "use_root_model_type_alias": True,
        "custom_template_dir": template_dir,
    }
    if entrypoint == "cli":
        args = ["--disable-timestamp", "--use-root-model-type-alias", "--custom-template-dir", str(template_dir)]
        if field_constraints:
            args.append("--field-constraints")
        if use_annotated:
            args.append("--use-annotated")
        run_main_and_assert(
            input_path=source,
            output_path=output_file,
            input_file_type="jsonschema",
            expected_file=expected / filename,
            extra_args=args,
        )
    else:
        generate(
            source,
            **_default_formatter_generate_options({
                "input_file_type": InputFileType.JsonSchema,
                "output": output_file,
                "disable_timestamp": True,
                **options,
            }),
        )
        assert_output(output_file.read_text(encoding="utf-8"), expected / filename)
    result = subprocess.run(
        [sys.executable, str(DATA_PATH / "python/root_alias_constraints/runtime.py"), str(source), str(output_file)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert_output(result.stdout, expected / f"{case}_runtime.txt")


@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize("case", ["null_numeric", "null_pattern"])
@pytest.mark.parametrize(("field_constraints", "use_annotated"), [(False, False), (True, False), (True, True)])
def test_root_alias_null_constraints(
    output_file: Path, entrypoint: str, case: str, *, field_constraints: bool, use_annotated: bool
) -> None:
    """Keep already-correct null aliases when unrelated type-specific keywords are present."""
    source = JSON_SCHEMA_DATA_PATH / "root_alias_constraints" / f"{case}.json"
    expected = EXPECTED_JSON_SCHEMA_PATH / "root_alias_constraints"
    if entrypoint == "cli":
        run_main_and_assert(
            input_path=source,
            output_path=output_file,
            input_file_type="jsonschema",
            expected_file=expected / f"{case}.py",
            extra_args=[
                "--disable-timestamp",
                "--use-root-model-type-alias",
                *(["--field-constraints"] if field_constraints else []),
                *(["--use-annotated"] if use_annotated else []),
            ],
        )
    else:
        generate(
            source,
            **_default_formatter_generate_options({
                "input_file_type": InputFileType.JsonSchema,
                "output": output_file,
                "disable_timestamp": True,
                "use_root_model_type_alias": True,
                "field_constraints": field_constraints,
                "use_annotated": use_annotated,
            }),
        )
        assert_output(
            output_file.read_text(encoding="utf-8"),
            expected / (f"{case}_annotated_api.py" if use_annotated else f"{case}.py"),
        )
    payloads = json.loads((DATA_PATH / "payloads/root_alias_null_values.json").read_text())
    validator = Draft7Validator(json.loads(source.read_text()))
    assert_output(json.dumps([validator.is_valid(value) for value in payloads]) + "\n", expected / "null_runtime.txt")
    try:
        with _generated_model(DATA_PATH / "python/root_alias_constraints/native_null.py", "native_null", "NativeNull"):
            pass
    except AssertionError as native_error:
        assert_output(str(native_error) + "\n", expected / "null_native_error.txt")
        with ExitStack() as stack, pytest.raises(AssertionError) as generated_error:
            stack.enter_context(_generated_model(output_file, "generated_null_alias", "Root"))
        assert_output(str(generated_error.value) + "\n", expected / "null_native_error.txt")
        return
    for value in payloads[1:]:
        assert_generated_model_json_validation(
            output_file,
            module_name="generated_null_alias",
            model_name="Root",
            valid_json=json.dumps(payloads[0]),
            invalid_json=json.dumps(value),
            expected_error_type="none_required",
        )
