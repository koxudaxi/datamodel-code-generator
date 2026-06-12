"""Tests for Pydantic v2 version helpers."""

from __future__ import annotations

import pytest

from datamodel_code_generator.model.pydantic_v2.version import _version_tuple

pytestmark = pytest.mark.allow_direct_assert


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("2.7.3", (2, 7, 3)),
        ("2.7", (2, 7, 0)),
        ("not-a-version", (0, 0, 0)),
    ],
)
def test_version_tuple_parses_versions_and_falls_back(version: str, expected: tuple[int, int, int]) -> None:
    """Parse normal versions and fall back when no version tuple is present."""
    assert _version_tuple(version) == expected
