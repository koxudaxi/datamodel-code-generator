"""Preserve finite and unbounded XSD occurrence composition."""

from __future__ import annotations

import json
from operator import itemgetter
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from datamodel_code_generator import DataModelType, InputFileType
from tests.main.conftest import (
    DATA_PATH,
    XML_SCHEMA_DATA_PATH,
    _generated_model,
    run_generate_file_and_assert,
    run_main_and_assert,
)
from tests.main.xmlschema.conftest import assert_file_content

if TYPE_CHECKING:
    from pathlib import Path

CASES = json.loads((DATA_PATH / "payloads/xmlschema_occurrence_bounds/cases.json").read_text())


@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize("case", CASES, ids=itemgetter("name"))
def test_xmlschema_occurrence_bounds(output_file: Path, entrypoint: str, case: dict) -> None:
    """Validate repeated elements without flattening their list-valued item types."""
    name = case["name"]
    source = XML_SCHEMA_DATA_PATH / "occurrence_bounds" / f"{name}.xsd"
    expected = f"occurrence_bounds/{name}.py"
    if entrypoint == "cli":
        run_main_and_assert(
            input_path=source,
            output_path=output_file,
            input_file_type="xmlschema",
            assert_func=assert_file_content,
            expected_file=expected,
            extra_args=[
                "--output-model-type",
                "pydantic_v2.BaseModel",
                "--field-constraints",
                "--use-field-description",
                "--disable-timestamp",
            ],
            force_exec_validation=True,
        )
    else:
        run_generate_file_and_assert(
            input_path=source,
            output_path=output_file,
            input_file_type=InputFileType.XMLSchema,
            output_model_type=DataModelType.PydanticV2BaseModel,
            field_constraints=True,
            use_field_description=True,
            disable_timestamp=True,
            assert_func=assert_file_content,
            expected_file=expected,
        )
    with _generated_model(output_file, f"generated_occurrences_{name}", "Root") as model:
        for sample in case["samples"]:
            if sample["valid"]:
                model.model_validate(sample["data"])
            else:
                with pytest.raises(ValidationError):
                    model.model_validate(sample["data"])
