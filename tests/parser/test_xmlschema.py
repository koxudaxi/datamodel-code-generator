"""Tests for XML Schema parser helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from datamodel_code_generator.parser.base import Result
from datamodel_code_generator.parser.jsonschema import JsonSchemaParser
from datamodel_code_generator.parser.xmlschema import (
    XMLSchemaParser,
    _collect_python_expression_imports,
    _safe_bool,
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
    ("value", "expected"),
    [
        (" true ", True),
        ("\t1\n", True),
        ("\rfalse\t", False),
        ("\n0 ", False),
    ],
)
def test_safe_bool_collapses_xml_schema_whitespace(value: str, expected: bool) -> None:
    """Apply XML Schema whiteSpace=collapse before parsing boolean literals."""
    assert _safe_bool(value) is expected


@pytest.mark.allow_direct_assert
@pytest.mark.parametrize("value", ["True", "False", " true false "])
def test_safe_bool_rejects_values_outside_xml_schema_lexical_space(value: str) -> None:
    """Reject Python-only spellings and invalid collapsed boolean values."""
    assert _safe_bool(value) is None


@pytest.mark.allow_direct_assert
@pytest.mark.parametrize(
    ("parse", "value"),
    [
        (_safe_date_expression, "not-a-date"),
        (_safe_date_expression, "2026-02-31"),
        (_safe_date_expression, "2026-06-04+09:00"),
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
    ("parse", "value", "expected"),
    [
        (_safe_date_expression, "2026-06-04", "datetime_module.date.fromisoformat('2026-06-04')"),
        (_safe_time_expression, "14:30:00", "datetime_module.time.fromisoformat('14:30:00')"),
        (_safe_time_expression, "14:30:00Z", "datetime_module.time.fromisoformat('14:30:00+00:00')"),
        (
            _safe_datetime_expression,
            "2026-06-04T14:30:00",
            "datetime_module.datetime.fromisoformat('2026-06-04T14:30:00')",
        ),
        (
            _safe_datetime_expression,
            "2026-06-04T14:30:00Z",
            "datetime_module.datetime.fromisoformat('2026-06-04T14:30:00+00:00')",
        ),
    ],
)
def test_temporal_expression_helpers_parse_supported_lexical_values(parse: Any, value: str, expected: str) -> None:
    """Parse supported XML Schema temporal lexical values."""
    expression = parse(value)

    assert expression is not None
    assert repr(expression) == expected


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
        (
            "P1DT2H3M4.5S",
            "datetime_module.timedelta(days=1, hours=2, minutes=3, seconds=4, microseconds=500000)",
        ),
    ],
)
def test_safe_day_time_duration_expression_parses_supported_components(value: str, expected: str) -> None:
    """Parse XML Schema dayTimeDuration components into datetime.timedelta expressions."""
    expression = _safe_day_time_duration_expression(value)

    assert expression is not None
    assert repr(expression) == expected


@pytest.mark.allow_direct_assert
def test_collect_python_expression_imports_from_dict_values() -> None:
    """Collect imports from Python expressions nested in mapping defaults."""
    expression = _safe_date_expression("2026-06-04")

    assert expression is not None
    assert _collect_python_expression_imports({"eventDate": expression}) == expression.imports


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
