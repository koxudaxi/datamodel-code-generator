"""Resolve final allOf field scopes without disturbing model-name allocation."""

from __future__ import annotations

import json
from contextlib import nullcontext
from operator import itemgetter
from typing import TYPE_CHECKING

import pytest

from datamodel_code_generator import Error, Formatter, InputFileType, generate
from datamodel_code_generator.__main__ import Exit
from tests.conftest import assert_directory_content, assert_output
from tests.main.conftest import (
    JSON_SCHEMA_DATA_PATH,
    _assert_model_json_invalid,
    _generated_model,
    _generated_package_module,
    _uses_external_test_default_formatter,
    assert_generated_model_json_validation,
    run_generate_file_and_assert,
    run_main_and_assert,
)
from tests.main.jsonschema.conftest import EXPECTED_JSON_SCHEMA_PATH, assert_file_content

if TYPE_CHECKING:
    from pathlib import Path

DATA = JSON_SCHEMA_DATA_PATH / "allof_scoped_aliases"
PAYLOADS = JSON_SCHEMA_DATA_PATH.parent / "payloads"


@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize(
    "case",
    json.loads((PAYLOADS / "allof_scoped_aliases_cases.json").read_text()),
    ids=itemgetter("name"),
)
def test_allof_final_scoped_aliases(output_file: Path, entrypoint: str, case: dict) -> None:
    """Keep final/raw/global precedence, alias choices, required fields and baseline class order."""
    with (
        pytest.warns(UserWarning, match="Field name `renamed` is duplicated on ApiChildSchema")
        if case["name"] == "repeated"
        else nullcontext()
    ):
        expected = f"allof_scoped_aliases/{case['name']}.py"
        if entrypoint == "api":
            run_generate_file_and_assert(
                input_path=DATA / f"{case['schema']}.json",
                input_file_type=InputFileType.JsonSchema,
                output_path=output_file,
                aliases=case["aliases"],
                disable_timestamp=True,
                assert_func=assert_file_content,
                expected_file=expected,
                unchanged_inputs={"aliases": case["aliases"], "options": case["options"]},
                **case["options"],
            )
        else:
            args = ["--disable-timestamp", "--aliases", json.dumps(case["aliases"])]
            for key, value in case["options"].items():
                args.append(f"--{key.replace('_', '-')}")
                if value is not True:
                    args.append(str(value))
            run_main_and_assert(
                input_path=DATA / f"{case['schema']}.json",
                input_file_type="jsonschema",
                output_path=output_file,
                extra_args=args,
                assert_func=assert_file_content,
                expected_file=expected,
                force_exec_validation=True,
            )
        if case["options"].get("output_model_type") == "msgspec.Struct":
            import msgspec

            with _generated_model(output_file, "allof_scoped_msgspec", "ApiRootSchema") as model:
                value = msgspec.json.decode((PAYLOADS / "allof_scoped_aliases_valid.json").read_bytes(), type=model)
                assert_output(
                    f"{value.child.renamed}\n", EXPECTED_JSON_SCHEMA_PATH / "allof_scoped_aliases/attribute.txt"
                )
                assert_output(
                    json.dumps(msgspec.to_builtins(value), indent=2) + "\n",
                    EXPECTED_JSON_SCHEMA_PATH / "allof_scoped_aliases/msgspec-runtime.txt",
                )
                with pytest.raises(msgspec.ValidationError):
                    msgspec.json.decode((PAYLOADS / "allof_scoped_aliases_invalid.json").read_bytes(), type=model)
            return
        valid_data = json.loads((PAYLOADS / "allof_scoped_aliases_valid.json").read_text())
        if case["options"].get("output_model_type") in {"dataclasses.dataclass", "typing.TypedDict"}:
            valid_data["child"][case["attribute"]] = valid_data["child"].pop("x")
        assert_generated_model_json_validation(
            output_file,
            module_name=f"allof_scoped_{case['name']}_{entrypoint}",
            model_name="ApiRootSchema" if case["options"].get("class_name_prefix") else "Root",
            valid_json=json.dumps(valid_data),
            invalid_json=(PAYLOADS / "allof_scoped_aliases_invalid.json").read_text(),
            expected_error_type="missing",
            expected_attribute_path=("child", case["attribute"]),
            expected_attribute_value="ok",
        )


@pytest.mark.parametrize("entrypoint", ["cli", "api"])
def test_allof_final_scoped_aliases_modular(output_dir: Path, entrypoint: str) -> None:
    """Preserve the generated package layout and module-qualified alias scopes."""
    expected = EXPECTED_JSON_SCHEMA_PATH / "allof_scoped_aliases/modular"
    aliases = {"pkg.ApiChildSchema.x": "renamed"}
    if entrypoint == "api":
        generate(
            DATA / "modular.json",
            input_file_type=InputFileType.JsonSchema,
            output=output_dir,
            aliases=aliases,
            class_name_prefix="Api",
            class_name_suffix="Schema",
            disable_timestamp=True,
            formatters=[Formatter.BLACK, Formatter.ISORT]
            if _uses_external_test_default_formatter()
            else [Formatter.BUILTIN],
        )
        assert_directory_content(output_dir, expected)
    else:
        run_main_and_assert(
            input_path=DATA / "modular.json",
            input_file_type="jsonschema",
            output_path=output_dir,
            extra_args=[
                "--aliases",
                json.dumps(aliases),
                "--class-name-prefix",
                "Api",
                "--class-name-suffix",
                "Schema",
                "--disable-timestamp",
            ],
            expected_directory=expected,
        )
    with _generated_package_module(output_dir, "pkg") as module:
        model = module.ApiChildSchema
        value = model.model_validate(json.loads((PAYLOADS / "allof_scoped_aliases_valid.json").read_text())["child"])
        assert_output(
            json.dumps({"fields": list(model.model_fields), "data": value.model_dump(by_alias=True)}, indent=2) + "\n",
            EXPECTED_JSON_SCHEMA_PATH / "allof_scoped_aliases/modular-runtime.txt",
        )
        _assert_model_json_invalid(model.model_validate, {"base": 1}, "missing")


@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize(
    "case", json.loads((PAYLOADS / "allof_scoped_aliases_errors.json").read_text()), ids=itemgetter("name")
)
def test_allof_final_scoped_aliases_invalid(
    output_file: Path, entrypoint: str, case: dict, capsys: pytest.CaptureFixture[str]
) -> None:
    """Validate the selected final alias before writing conflicting or reserved field names."""
    expected = EXPECTED_JSON_SCHEMA_PATH / "allof_scoped_aliases" / f"error_{case['name']}.txt"
    if entrypoint == "api":
        with pytest.raises(Error) as error:
            generate(
                DATA / "allof.json",
                input_file_type=InputFileType.JsonSchema,
                output=output_file,
                aliases=case["aliases"],
                class_name_prefix="Api",
                class_name_suffix="Schema",
            )
        assert_output(f"{error.value}\n", expected)
        assert_output(f"{output_file.exists()}\n", EXPECTED_JSON_SCHEMA_PATH / "allof_scoped_aliases/absent.txt")
    else:
        run_main_and_assert(
            input_path=DATA / "allof.json",
            input_file_type="jsonschema",
            output_path=output_file,
            extra_args=[
                "--aliases",
                json.dumps(case["aliases"]),
                "--class-name-prefix",
                "Api",
                "--class-name-suffix",
                "Schema",
            ],
            expected_exit=Exit.ERROR,
            capsys=capsys,
            expected_stderr=expected.read_text(),
            output_should_not_exist=True,
        )
