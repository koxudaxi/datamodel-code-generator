"""Regression coverage for validation siblings on a single allOf reference."""

from __future__ import annotations

import json
from operator import itemgetter
from typing import TYPE_CHECKING

import pytest
from jsonschema.validators import validator_for
from pydantic import ValidationError
from referencing import Registry, Resource

from datamodel_code_generator import InputFileType
from tests.main.conftest import (
    JSON_SCHEMA_DATA_PATH,
    _generated_model,
    run_generate_file_and_assert,
    run_main_and_assert,
)
from tests.main.jsonschema.conftest import assert_file_content

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize("field_constraints", [False, True])
@pytest.mark.parametrize("merge_mode", ["all", "constraints", "none"])
@pytest.mark.parametrize("schema_validators", [False, True])
@pytest.mark.parametrize(
    "case", json.loads((JSON_SCHEMA_DATA_PATH / "allof_ref_siblings/cases.json").read_text()), ids=itemgetter("name")
)
def test_allof_ref_siblings(
    output_file: Path, entrypoint: str, field_constraints: bool, schema_validators: bool, merge_mode: str, case: dict
) -> None:
    """Preserve modern sibling constraints and ignore them in older reference drafts."""
    data = JSON_SCHEMA_DATA_PATH / "allof_ref_siblings"
    schema_path = data / f"{case['name']}.json"
    expected = f"allof_ref_siblings/{case['name']}_{field_constraints}_{schema_validators}.py"
    if entrypoint == "cli":
        run_main_and_assert(
            input_path=schema_path,
            output_path=output_file,
            input_file_type="jsonschema",
            extra_args=[
                "--disable-timestamp",
                "--allof-merge-mode",
                merge_mode,
                *(["--field-constraints"] if field_constraints else []),
                *(["--generate-schema-validators"] if schema_validators else []),
            ],
            assert_func=assert_file_content,
            expected_file=expected,
            force_exec_validation=True,
        )
    else:
        run_generate_file_and_assert(
            input_path=schema_path,
            output_path=output_file,
            input_file_type=InputFileType.JsonSchema,
            disable_timestamp=True,
            allof_merge_mode=merge_mode,
            field_constraints=field_constraints,
            generate_schema_validators=schema_validators,
            assert_func=assert_file_content,
            expected_file=expected,
        )
    schema = json.loads(schema_path.read_text())
    registry = Registry().with_resource(
        "external_types.json", Resource.from_contents(json.loads((data / "external_types.json").read_text()))
    )
    validator = validator_for(schema)(schema, registry=registry)
    with _generated_model(output_file, "allof_sibling_model", "Root") as model:
        for value in case["valid"]:
            validator.validate(value)
            assert json.loads(model.model_validate_json(json.dumps(value)).model_dump_json()) == value
        for value in case["invalid"]:
            assert not validator.is_valid(value)
            with pytest.raises(ValidationError):
                model.model_validate_json(json.dumps(value))
