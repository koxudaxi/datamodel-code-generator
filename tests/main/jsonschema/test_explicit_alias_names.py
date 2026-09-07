"""Diagnose invalid explicit field aliases before writing generated code."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

import pytest

from datamodel_code_generator import DataModelType, Error, InputFileType, generate
from datamodel_code_generator.__main__ import Exit
from tests.main.conftest import (
    ALIASES_DATA_PATH,
    JSON_SCHEMA_DATA_PATH,
    assert_generated_model_json_validation,
    run_generate_file_and_assert,
    run_main_and_assert,
)
from tests.main.jsonschema.conftest import assert_file_content

if TYPE_CHECKING:
    from pathlib import Path

ALIASES = json.loads((ALIASES_DATA_PATH / "explicit_alias_names.json").read_text())


@pytest.mark.parametrize(
    ("case", "backend"),
    [
        (case, backend)
        for case in ["duplicate", "existing", "scoped_duplicate", "keyword", "invalid", "empty"]
        for backend in DataModelType
    ]
    + [
        ("reserved_config", DataModelType.PydanticV2BaseModel),
        ("reserved_validate", DataModelType.PydanticV2BaseModel),
        ("reserved_msgspec", DataModelType.MsgspecStruct),
    ],
)
def test_explicit_alias_names_invalid(
    case: str, backend: DataModelType, output_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Reject collisions and invalid Python identifiers for every output model."""
    aliases = ALIASES[case]
    field_name = "b" if case in {"duplicate", "existing", "scoped_duplicate"} else "a"
    alias = aliases.get(f"AliasNames.{field_name}", aliases.get(field_name))
    reason = "conflicts with another field" if field_name == "b" else "is not a valid field name"
    message = f"Alias {alias!r} for field {field_name!r} {reason}."
    with pytest.raises(Error, match=re.escape(message)):
        generate(
            JSON_SCHEMA_DATA_PATH / "explicit_alias_names.json",
            input_file_type=InputFileType.JsonSchema,
            output=output_file,
            aliases=aliases,
            output_model_type=backend,
        )
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "explicit_alias_names.json",
        output_path=output_file,
        input_file_type="jsonschema",
        extra_args=["--aliases", json.dumps(aliases), "--output-model-type", backend.value],
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains=message,
        output_should_not_exist=True,
    )


@pytest.mark.parametrize("case", ["normal", "global", "scoped", "choices", "neutral_reserved"])
def test_explicit_alias_names_valid(case: str, output_file: Path) -> None:
    """Preserve valid aliases, spelling, precedence, field order and required fields."""
    backend = DataModelType.DataclassesDataclass if case == "neutral_reserved" else DataModelType.PydanticV2BaseModel
    run_generate_file_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "explicit_alias_names.json",
        output_path=output_file,
        input_file_type=InputFileType.JsonSchema,
        aliases=ALIASES[case],
        output_model_type=backend,
        snake_case_field=True,
        disable_timestamp=True,
        assert_func=assert_file_content,
        expected_file=f"explicit_alias_names_{case}.py",
        unchanged_inputs={"aliases": ALIASES[case]},
    )
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "explicit_alias_names.json",
        output_path=output_file,
        input_file_type="jsonschema",
        extra_args=[
            "--aliases",
            json.dumps(ALIASES[case]),
            "--snake-case-field",
            "--output-model-type",
            backend.value,
            "--disable-timestamp",
        ],
        assert_func=assert_file_content,
        expected_file=f"explicit_alias_names_{case}.py",
        force_exec_validation=True,
    )
    fields = {
        "normal": ("a", "b"),
        "global": ("camel_name", "count"),
        "scoped": ("value", "count"),
        "choices": ("first", "count"),
        "neutral_reserved": ("model_config", "model_validate"),
    }[case]
    data = {fields[0]: "A", fields[1]: 1} if case == "neutral_reserved" else {"a": "A", "b": 1}
    assert_generated_model_json_validation(
        output_file,
        module_name=f"explicit_alias_names_{case}",
        model_name="AliasNames",
        valid_json=json.dumps(data),
        invalid_json=json.dumps({next(iter(data)): "A"}),
        expected_error_type="missing",
        expected_repr=f"AliasNames({fields[0]}='A', {fields[1]}=1)",
    )
