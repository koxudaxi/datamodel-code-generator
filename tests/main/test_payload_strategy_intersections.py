"""Check empty intersections independently of generated-model compatibility."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import TYPE_CHECKING

import pytest
from hypothesis_jsonschema import from_schema
from jsonschema import Draft7Validator

from tests.conftest import assert_inputs_not_mutated, assert_output
from tests.main.conftest import DATA_PATH, EXPECTED_MAIN_PATH, JSON_SCHEMA_DATA_PATH
from tests.main.payload_validation.codegen import PayloadAdapterError, generate_payload_runtime
from tests.main.payload_validation.models import GeneratedModelCache, PayloadBackend, SchemaCase
from tests.main.payload_validation.schema import _schema_exclusion_reason

if TYPE_CHECKING:
    from pathlib import Path


def test_allof_payload_strategy_classification() -> None:
    """Keep impossible intersections out of acceptance generation while retaining valid controls."""
    names = json.loads((DATA_PATH / "payloads/allof_payload_strategy_cases.json").read_text())
    payloads = json.loads((DATA_PATH / "payloads/allof_payload_strategy_values.json").read_text())
    results = {}
    for name in names:
        schema = json.loads((JSON_SCHEMA_DATA_PATH / "numeric_allof_types" / f"{name}.json").read_text())
        validator = Draft7Validator(schema)
        with assert_inputs_not_mutated({"schema": schema}):
            results[name] = {
                "empty_strategy": from_schema(deepcopy(schema)).is_empty,
                "classification": _schema_exclusion_reason(schema),
                "source_acceptance": [validator.is_valid(payload) for payload in payloads],
            }
    assert_output(
        json.dumps(results, indent=2) + "\n", EXPECTED_MAIN_PATH / "allof_payload_strategy_classification.txt"
    )


def test_payload_generation_reports_real_schema_failure(tmp_path: Path) -> None:
    """Keep actual generation errors visible when checking expected warnings."""
    source = JSON_SCHEMA_DATA_PATH / "payload_generation_missing_reference.json"
    schema = json.loads(source.read_text())
    case = SchemaCase(
        id="jsonschema/payload_generation_missing_reference.json",
        input_file_type="jsonschema",
        source_path=source,
        source_schema=schema,
        codegen_schema=schema,
        temp_input_suffix=".json",
    )
    with pytest.raises(PayloadAdapterError) as caught:
        generate_payload_runtime(
            case, GeneratedModelCache({"base": tmp_path, "adapters": {}}), PayloadBackend.PYDANTIC_V2
        )
    assert_output(str(caught.value) + "\n", EXPECTED_MAIN_PATH / "payload_generation_missing_reference.txt")
