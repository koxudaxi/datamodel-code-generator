"""Construct source-proven literal witnesses without weakening regex intersections."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from jsonschema import ValidationError

from tests.conftest import assert_inputs_not_mutated

from .payload_validation import SchemaCase, payload_strategy, validate_with_source_schema

DATA_PATH = Path(__file__).parents[1] / "data" / "payloads" / "literal_witnesses_schemas.json"
SCHEMAS = json.loads(DATA_PATH.read_text(encoding="utf-8"))
CASES = {name: SchemaCase(name, "jsonschema", DATA_PATH, schema, schema, ".json") for name, schema in SCHEMAS.items()}


@pytest.mark.parametrize("name", CASES)
@settings(
    database=None,
    deadline=None,
    derandomize=True,
    max_examples=20,
    suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow],
)
@given(data=st.data())
def test_literal_source_payloads(name: str, data: st.DataObject) -> None:
    """Sample literal intersections, nonliteral regexes, nested schemas and ordinary primitives."""
    case = CASES[name]
    with assert_inputs_not_mutated({"schema": case.source_schema}):
        validate_with_source_schema(case, data.draw(payload_strategy(case)))


def test_literal_source_witnesses() -> None:
    """The unchanged source proves both literal orders and rejects incomplete intersections."""
    witnesses = json.loads(DATA_PATH.with_name("literal_witnesses_values.json").read_text(encoding="utf-8"))["unicode"]
    with assert_inputs_not_mutated({"schema": CASES["unicode"].source_schema, "witnesses": witnesses}):
        for payload in witnesses["valid"]:
            validate_with_source_schema(CASES["unicode"], payload)
        for payload in witnesses["invalid"]:
            with pytest.raises(ValidationError):
                validate_with_source_schema(CASES["unicode"], payload)
