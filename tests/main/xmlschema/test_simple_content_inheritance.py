"""Keep inherited XSD simple content scalar and attributes at the same level."""

from __future__ import annotations

import json
from operator import itemgetter
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from datamodel_code_generator import DataModelType, InputFileType
from tests.conftest import assert_output
from tests.main.conftest import (
    DATA_PATH,
    EXPECTED_XML_SCHEMA_PATH,
    XML_SCHEMA_DATA_PATH,
    _generated_model,
    run_generate_file_and_assert,
    run_main_and_assert,
)
from tests.main.xmlschema.conftest import assert_file_content

if TYPE_CHECKING:
    from pathlib import Path

CASES = json.loads((DATA_PATH / "payloads/xmlschema_simple_content_inheritance/cases.json").read_text())


@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize("case", CASES, ids=itemgetter("name"))
def test_xmlschema_simple_content_inheritance(output_file: Path, entrypoint: str, case: dict) -> None:
    """Preserve scalar validation, inherited attributes and their defaults without nested objects."""
    name = case["name"]
    source = XML_SCHEMA_DATA_PATH / "simple_content_inheritance" / f"{name}.xsd"
    expected = f"simple_content_inheritance/{name}.py"
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
    with _generated_model(output_file, f"generated_simple_content_{name}", "Root") as model:
        results = []
        for sample in case["samples"]:
            if sample["valid"]:
                results.append(model.model_validate(sample["data"]).model_dump(mode="json"))
            else:
                with pytest.raises(ValidationError):
                    model.model_validate(sample["data"])
        assert_output(
            json.dumps(results, indent=2) + "\n",
            EXPECTED_XML_SCHEMA_PATH / "simple_content_inheritance" / f"{name}.txt",
        )
