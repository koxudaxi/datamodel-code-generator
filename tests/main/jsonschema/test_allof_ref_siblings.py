"""Regression coverage for validation siblings on a single allOf reference."""

from __future__ import annotations

import json
import sys
from operator import itemgetter
from typing import TYPE_CHECKING

import pytest
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from jsonschema.validators import validator_for
from pydantic import TypeAdapter, ValidationError
from referencing import Registry, Resource

from datamodel_code_generator import DataModelType, Error, InputFileType, generate
from datamodel_code_generator.__main__ import Exit
from tests.conftest import assert_output
from tests.main.conftest import (
    DATA_PATH,
    JSON_SCHEMA_DATA_PATH,
    _generated_model,
    run_generate_file_and_assert,
    run_main_and_assert,
)
from tests.main.jsonschema.conftest import assert_file_content

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("schema_validators", [False, True])
@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize("field_constraints", [False, True])
@pytest.mark.parametrize("merge_mode", ["all", "constraints", "none"])
@pytest.mark.parametrize(
    "case", json.loads((DATA_PATH / "payloads/allof_ref_siblings.json").read_text()), ids=itemgetter("name")
)
def test_allof_ref_siblings(
    output_file: Path,
    entrypoint: str,
    field_constraints: bool,
    schema_validators: bool,
    merge_mode: str,
    case: dict,
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
                "--output-model-type",
                DataModelType.PydanticV2BaseModel.value,
                "--allof-merge-mode",
                merge_mode,
                *(["--field-constraints"] if field_constraints else []),
                *(["--generate-schema-validators"] if schema_validators else []),
                *(["--use-tuple-for-fixed-items"] if case.get("use_tuple") else []),
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
            output_model_type=DataModelType.PydanticV2BaseModel,
            disable_timestamp=True,
            allof_merge_mode=merge_mode,
            field_constraints=field_constraints,
            generate_schema_validators=schema_validators,
            use_tuple_for_fixed_items=case.get("use_tuple", False),
            assert_func=assert_file_content,
            expected_file=expected,
        )
    schema = json.loads(schema_path.read_text())
    registry = Registry().with_resource(
        "external_types.json", Resource.from_contents(json.loads((data / "external_types.json").read_text()))
    )
    validator = validator_for(schema)(schema, registry=registry)
    with _generated_model(output_file, "allof_sibling_model", "Root") as model:
        adapter = TypeAdapter(model)
        generated_schema = adapter.json_schema()
        generated_validator = validator_for(generated_schema)(generated_schema)
        actual = []
        for value in case["valid"]:
            validator.validate(value)
            generated_validator.validate(value)
            actual.append(json.loads(adapter.dump_json(adapter.validate_json(json.dumps(value)))))
        assert_output(
            json.dumps(actual, indent=2) + "\n",
            DATA_PATH / "payloads" / "allof_ref_sibling_outputs" / f"{case['name']}.txt",
        )
        if case["name"].startswith(("enum_", "const_")):
            base = vars(sys.modules[model.__module__])["Base"]
            parsed_inputs = []
            for value in case["valid"]:
                base_value = TypeAdapter(base).validate_json(json.dumps(value))
                parsed_inputs.append(json.loads(adapter.dump_json(adapter.validate_python(base_value))))
            assert_output(
                json.dumps(parsed_inputs, indent=2) + "\n",
                DATA_PATH / "payloads" / "allof_ref_sibling_outputs" / f"{case['name']}.txt",
            )
        for value in case["invalid"]:
            with pytest.raises(JsonSchemaValidationError):
                validator.validate(value)
            with pytest.raises(JsonSchemaValidationError):
                generated_validator.validate(value)
            with pytest.raises(ValidationError):
                adapter.validate_json(json.dumps(value))


@pytest.mark.parametrize("case_name", ["enum_disjoint", "literal_boolean_number"])
def test_allof_ref_sibling_empty_intersection(output_file: Path, case_name: str) -> None:
    """Reject disjoint literal intersections, including JSON booleans versus numbers."""
    schema_path = JSON_SCHEMA_DATA_PATH / "allof_ref_siblings" / f"{case_name}.json"
    run_main_and_assert(input_path=schema_path, output_path=output_file, expected_exit=Exit.ERROR)
    with pytest.raises(Error, match="unsatisfiable"):
        generate(schema_path, input_file_type=InputFileType.JsonSchema)


@pytest.mark.parametrize("entrypoint", ["cli", "api"])
def test_allof_literal_custom_template(output_file: Path, entrypoint: str) -> None:
    """Preserve the literal and base constraints when a custom template renders validators."""
    schema_path = JSON_SCHEMA_DATA_PATH / "allof_ref_siblings/enum_length.json"
    template_dir = DATA_PATH / "templates_allof_literals"
    if entrypoint == "cli":
        run_main_and_assert(
            input_path=schema_path,
            output_path=output_file,
            extra_args=["--disable-timestamp", "--custom-template-dir", str(template_dir)],
            assert_func=assert_file_content,
            expected_file="allof_ref_siblings/enum_length_False_False.py",
            force_exec_validation=True,
        )
    else:
        run_generate_file_and_assert(
            input_path=schema_path,
            output_path=output_file,
            input_file_type=InputFileType.JsonSchema,
            disable_timestamp=True,
            custom_template_dir=template_dir,
            assert_func=assert_file_content,
            expected_file="allof_ref_siblings/enum_length_False_False.py",
        )
    case = next(
        case
        for case in json.loads((DATA_PATH / "payloads/allof_ref_siblings.json").read_text())
        if case["name"] == "enum_length"
    )
    schema = json.loads(schema_path.read_text())
    validator = validator_for(schema)(schema)
    with _generated_model(output_file, "allof_literal_custom", "Root") as model:
        actual = []
        for value in case["valid"]:
            validator.validate(value)
            actual.append(model.model_validate_json(json.dumps(value)).root)
        assert_output(
            json.dumps(actual, indent=2) + "\n",
            DATA_PATH / "payloads/allof_ref_sibling_outputs/enum_length.txt",
        )
        for value in case["invalid"]:
            with pytest.raises(JsonSchemaValidationError):
                validator.validate(value)
            with pytest.raises(ValidationError):
                model.model_validate_json(json.dumps(value))


def test_allof_literal_custom_template_missing_validators(output_file: Path) -> None:
    """Diagnose a custom root template that omits the required literal validator."""
    schema_path = JSON_SCHEMA_DATA_PATH / "allof_ref_siblings/enum_length.json"
    template_dir = DATA_PATH / "templates_docstring_escaping"
    run_main_and_assert(
        input_path=schema_path,
        output_path=output_file,
        extra_args=["--custom-template-dir", str(template_dir)],
        expected_exit=Exit.ERROR,
    )
    with pytest.raises(Error, match="must render class_body_lines"):
        generate(schema_path, input_file_type=InputFileType.JsonSchema, custom_template_dir=template_dir)
