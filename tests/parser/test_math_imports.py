"""Tests for non-finite float math import helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from datamodel_code_generator.parser._math_imports import (
    add_math_imports_for_non_finite_literals,
    apply_math_imports_to_parse_result,
)
from datamodel_code_generator.parser.base import Result
from tests.conftest import assert_output, assert_parser_modules

DATA_PATH = Path(__file__).parents[1] / "data" / "math_imports"
INPUT_PATH = DATA_PATH / "input"
EXPECTED_PATH = DATA_PATH / "expected"


@pytest.mark.parametrize(
    "case",
    [
        "basic",
        "branches",
        "clean",
        "existing_import",
        "nested_scope",
        "no_match",
        "invalid_syntax",
        "scope_resolution",
        "function_annotation",
        "header_boundaries",
        "pep695_literal",
        "pep695_local_name",
        "pep695_type_alias_name",
        "pep695_existing_import",
    ],
)
def test_add_math_imports_for_non_finite_literals(case: str) -> None:
    """Resolve only unbound generated literals and preserve module headers."""
    body = (INPUT_PATH / f"{case}.py").read_text(encoding="utf-8")

    assert_output(add_math_imports_for_non_finite_literals(body), EXPECTED_PATH / f"{case}.py")


def test_apply_math_imports_to_parse_result_modules() -> None:
    """Apply imports to every generated module without mocks."""
    modules = {
        ("non_finite.py",): Result(body=(INPUT_PATH / "basic.py").read_text(encoding="utf-8")),
        ("clean.py",): Result(body=(INPUT_PATH / "clean.py").read_text(encoding="utf-8")),
    }

    apply_math_imports_to_parse_result(modules)

    assert_parser_modules(modules, EXPECTED_PATH / "modules")


def test_apply_math_imports_to_parse_result_string() -> None:
    """Apply imports to a single generated module body."""
    body = (INPUT_PATH / "basic.py").read_text(encoding="utf-8")

    assert_output(apply_math_imports_to_parse_result(body), EXPECTED_PATH / "basic.py")
