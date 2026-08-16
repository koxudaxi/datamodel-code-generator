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
        "class_in_function_closure",
        "class_in_function_global_binding",
        "class_in_function_static_binding",
        "clean",
        "existing_import",
        "invalid_empty_prefix",
        "nested_scope",
        "nested_class",
        "no_match",
        "invalid_syntax",
        "invalid_prefix_syntax",
        "scope_resolution",
        "function_annotation",
        "header_boundaries",
        "pep695_empty_prefix",
        "pep695_existing_import",
        "pep695_invalid_syntax",
        "pep695_literal",
        "pep695_local_name",
        "pep695_prefix_load",
        "pep695_type_alias_name",
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


def test_add_math_imports_pep695_preserves_crlf_and_trailing_blank_line() -> None:
    """Keep CRLF output exact while resolving PEP 695 aliases on Python 3.11."""
    body = f"{(INPUT_PATH / 'pep695_crlf.py').read_text(encoding='utf-8')}\n".replace("\n", "\r\n")

    assert_output(f"{add_math_imports_for_non_finite_literals(body)!r}\n", EXPECTED_PATH / "pep695_crlf.txt")
