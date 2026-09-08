"""Exercise schema validators with real mutable and immutable Mapping inputs."""

from __future__ import annotations

import json
from collections import UserDict
from types import MappingProxyType
from typing import TYPE_CHECKING

import pytest
from jsonschema import Draft202012Validator

from datamodel_code_generator import Formatter, GenerateConfig, InputFileType, generate
from tests.conftest import assert_output
from tests.main.conftest import (
    DATA_PATH,
    JSON_SCHEMA_DATA_PATH,
    _assert_model_json_invalid,
    _generated_model,
    run_generate_file_and_assert,
    run_main_and_assert,
    run_main_with_args,
)
from tests.main.jsonschema.conftest import assert_file_content

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from pathlib import Path
    from typing import Any


@pytest.mark.parametrize("formatter", ["builtin", "external"])
@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize("container", [dict, UserDict, MappingProxyType])
@pytest.mark.parametrize(
    "case",
    [
        "Count",
        "CountMinimum",
        "One",
        "Any",
        "Conditional",
        "ConditionalElse",
        "Unique",
        "Nested",
        "Pattern",
        "PatternUnique",
        "AdditionalUnique",
    ],
)
def test_schema_validator_mapping_inputs(
    output_file: Path, entrypoint: str, container: Callable[..., Mapping[str, Any]], case: str, formatter: str
) -> None:
    """Match native schema acceptance and preserve caller mappings, including nested objects."""
    source = JSON_SCHEMA_DATA_PATH / "mapping_schema_validators.json"
    payloads = DATA_PATH / "payloads/mapping_schema_validators"
    valid_path = payloads / f"{case}_valid.txt"
    invalid_path = payloads / f"{case}_invalid.txt"
    valid = json.loads(valid_path.read_text(encoding="utf-8"), object_hook=container)
    invalid = json.loads(invalid_path.read_text(encoding="utf-8"), object_hook=container)
    schema_case = {"CountMinimum": "Count", "ConditionalElse": "Conditional"}.get(case, case)
    schema = json.loads(source.read_text(encoding="utf-8"))["$defs"][schema_case]
    native = Draft202012Validator(schema)
    assert_output(
        json.dumps([
            native.is_valid(json.loads(valid_path.read_text(encoding="utf-8"))),
            native.is_valid(json.loads(invalid_path.read_text(encoding="utf-8"))),
        ])
        + "\n",
        payloads / "native.txt",
    )
    formatters = [Formatter.BUILTIN] if formatter == "builtin" else [Formatter.BLACK, Formatter.ISORT]
    suffix = "_builtin" if formatter == "builtin" else ""
    expected = f"mapping_schema_validators{suffix}.py"
    if entrypoint == "cli":
        run_main_with_args([
            "--input",
            str(source),
            "--output",
            str(output_file),
            "--input-file-type",
            "jsonschema",
            "--generate-schema-validators",
            "--disable-timestamp",
            "--formatters",
            *(value.value for value in formatters),
        ])
    else:
        generate(
            source,
            config=GenerateConfig(
                output=output_file,
                input_file_type=InputFileType.JsonSchema,
                formatters=formatters,
                generate_schema_validators=True,
                disable_timestamp=True,
            ),
        )
    assert_file_content(output_file, expected)
    with _generated_model(
        output_file, f"mapping_inputs_{case}", "AnyModel" if schema_case == "Any" else schema_case
    ) as model:
        _assert_model_json_invalid(model.model_validate, None, "model_type")
        value = model.model_validate(valid)
        assert_output(json.dumps(value.model_dump(exclude_unset=True), default=dict, indent=2) + "\n", valid_path)
        _assert_model_json_invalid(model.model_validate, invalid, "int_parsing" if case == "Pattern" else "value_error")
    assert_output(json.dumps(valid, default=dict, indent=2) + "\n", valid_path)
    assert_output(json.dumps(invalid, default=dict, indent=2) + "\n", invalid_path)


@pytest.mark.parametrize("entrypoint", ["cli", "api"])
def test_schema_validator_legacy_custom_helper(output_file: Path, entrypoint: str) -> None:
    """Preserve complete output and runtime behavior of an existing helper override."""
    source = JSON_SCHEMA_DATA_PATH / "inline_allof_validators/oneof.json"
    template_dir = DATA_PATH / "templates/mapping_legacy_helper"
    expected = "mapping_schema_validators_legacy_helper.py"
    if entrypoint == "cli":
        run_main_and_assert(
            input_path=source,
            output_path=output_file,
            input_file_type="jsonschema",
            extra_args=[
                "--generate-schema-validators",
                "--disable-timestamp",
                "--custom-template-dir",
                str(template_dir),
            ],
            assert_func=assert_file_content,
            expected_file=expected,
            force_exec_validation=True,
        )
    else:
        run_generate_file_and_assert(
            input_path=source,
            output_path=output_file,
            input_file_type=InputFileType.JsonSchema,
            generate_schema_validators=True,
            disable_timestamp=True,
            custom_template_dir=template_dir,
            assert_func=assert_file_content,
            expected_file=expected,
        )
    values = json.loads((DATA_PATH / "payloads/inline_allof_validators/oneof.json").read_text(encoding="utf-8"))
    with _generated_model(output_file, "mapping_legacy_helper", "Root") as model:
        model.model_validate(values["valid"])
        _assert_model_json_invalid(model.model_validate, values["invalid"], "value_error")
