"""Tests for XML Schema parser helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from datamodel_code_generator.parser.base import Result
from datamodel_code_generator.parser.jsonschema import JsonSchemaParser
from datamodel_code_generator.parser.xmlschema import (
    XMLSchemaParser,
    _safe_date_expression,
    _safe_datetime_expression,
    _safe_day_time_duration_expression,
    _safe_float,
    _safe_time_expression,
)


@pytest.mark.allow_direct_assert
@pytest.mark.parametrize("value", ["inf", "+inf", "-inf", "nan"])
def test_safe_float_rejects_python_only_non_finite_literals(value: str) -> None:
    """Reject non-finite spellings outside the XML Schema lexical space."""
    assert _safe_float(value) is None


@pytest.mark.allow_direct_assert
@pytest.mark.parametrize(
    ("parse", "value"),
    [
        (_safe_date_expression, "not-a-date"),
        (_safe_date_expression, "2026-02-31"),
        (_safe_time_expression, "25:00:00"),
        (_safe_datetime_expression, "2026-02-31T00:00:00"),
        (_safe_day_time_duration_expression, "1D"),
        (_safe_day_time_duration_expression, "P"),
        (_safe_day_time_duration_expression, "PT0.0000001S"),
    ],
)
def test_temporal_expression_helpers_reject_invalid_lexical_values(parse: Any, value: str) -> None:
    """Reject temporal defaults outside the supported XML Schema lexical space."""
    assert parse(value) is None


@pytest.mark.allow_direct_assert
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("P1D", "datetime_module.timedelta(days=1)"),
        ("PT2H", "datetime_module.timedelta(hours=2)"),
        ("PT3M", "datetime_module.timedelta(minutes=3)"),
        ("PT4S", "datetime_module.timedelta(seconds=4)"),
        ("PT0.5S", "datetime_module.timedelta(microseconds=500000)"),
        ("-P1D", "-datetime_module.timedelta(days=1)"),
    ],
)
def test_safe_day_time_duration_expression_parses_supported_components(value: str, expected: str) -> None:
    """Parse XML Schema dayTimeDuration components into datetime.timedelta expressions."""
    expression = _safe_day_time_duration_expression(value)

    assert expression is not None
    assert repr(expression) == expected


@pytest.mark.allow_direct_assert
def test_parse_adds_non_finite_float_imports_to_module_results(monkeypatch: pytest.MonkeyPatch) -> None:
    """Add math imports for non-finite defaults in modular parser results."""
    modules = {
        ("models.py",): Result(body="class Model:\n    value: float = -inf"),
        ("other.py",): Result(body="class Other:\n    value: float = nan"),
        ("bounds.py",): Result(
            body=(
                "from pydantic import BaseModel, confloat\n"
                "\n"
                "\n"
                "class Bounds(BaseModel):\n"
                "    value: confloat(ge=-inf, lt=inf) | None = None"
            )
        ),
    }

    def parse(_self: JsonSchemaParser, *_args: Any, **_kwargs: Any) -> dict[tuple[str, ...], Result]:
        return modules

    monkeypatch.setattr(JsonSchemaParser, "parse", parse)

    result = XMLSchemaParser(Path("schema.xsd")).parse()

    assert result is modules
    assert modules["bounds.py",].body == (
        "from math import inf\n"
        "from pydantic import BaseModel, confloat\n"
        "\n"
        "\n"
        "class Bounds(BaseModel):\n"
        "    value: confloat(ge=-inf, lt=inf) | None = None"
    )
    assert modules["models.py",].body == "from math import inf\nclass Model:\n    value: float = -inf"
    assert modules["other.py",].body == "from math import nan\nclass Other:\n    value: float = nan"
