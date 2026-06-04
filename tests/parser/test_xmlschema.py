"""Tests for XML Schema parser helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from datamodel_code_generator.parser.base import Result
from datamodel_code_generator.parser.jsonschema import JsonSchemaParser
from datamodel_code_generator.parser.xmlschema import XMLSchemaParser, _safe_float


@pytest.mark.allow_direct_assert
@pytest.mark.parametrize("value", ["inf", "+inf", "-inf", "nan"])
def test_safe_float_rejects_python_only_non_finite_literals(value: str) -> None:
    """Reject non-finite spellings outside the XML Schema lexical space."""
    assert _safe_float(value) is None


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
