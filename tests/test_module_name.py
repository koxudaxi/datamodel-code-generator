"""Tests for dotted model-name interpretation."""

from __future__ import annotations

from pathlib import Path

from datamodel_code_generator._module_name import split_module_name
from tests.conftest import assert_output

EXPECTED_PATH = Path(__file__).parent / "data" / "expected" / "module_name"


def test_split_module_name() -> None:
    """Split only canonical Python paths unless module treatment is explicit."""
    cases = [
        ("models.Pet", None),
        ("pkg.日本語", None),
        ("match.case", None),
        ("pkg.1.Model", None),
        ("SaveTrifectaV2.1", None),
        ("pkg.class", None),
        ("pkg.user-name", None),
        (".Pet", None),
        ("pkg.", None),
        ("pkg..Pet", None),
        ("\N{KELVIN SIGN}.Model", None),
        ("pkg.\N{FULLWIDTH LATIN CAPITAL LETTER A}", None),
        ("", None),
        ("Pet", None),
        ("models.Pet", False),
        ("SaveTrifectaV2.1", False),
        ("models.Pet", True),
        ("SaveTrifectaV2.1", True),
    ]
    result = "".join(
        f"{treat_dot_as_module!r} | {name!r} -> {split_module_name(name, treat_dot_as_module=treat_dot_as_module)!r}\n"
        for name, treat_dot_as_module in cases
    )

    assert_output(result, EXPECTED_PATH / "split_module_name.txt")
