"""Tests for msgspec model helpers."""

from __future__ import annotations

import pytest

from datamodel_code_generator.model.msgspec import _add_unset_type, get_neither_required_nor_nullable_type


@pytest.mark.allow_direct_assert
@pytest.mark.parametrize(
    ("type_hint", "use_union_operator", "expected"),
    [
        ("Optional[str]", False, "Union[str, UnsetType]"),
        ("Union[str, int]", False, "Union[str, int, UnsetType]"),
        ("Union[str, None]", False, "Union[str, UnsetType]"),
        (
            "Annotated[Optional[str], Meta(min_length=1)]",
            False,
            "Union[Annotated[Optional[str], Meta(min_length=1)], UnsetType]",
        ),
        ("list[Union[str, int]]", False, "Union[list[Union[str, int]], UnsetType]"),
        ("str | None", True, "str | UnsetType"),
    ],
)
def test_get_neither_required_nor_nullable_type(type_hint: str, use_union_operator: bool, expected: str) -> None:
    """Add UnsetType without relying on string prefix checks."""
    assert get_neither_required_nor_nullable_type(type_hint, use_union_operator) == expected


@pytest.mark.allow_direct_assert
@pytest.mark.parametrize(
    ("type_hint", "use_union_operator", "expected"),
    [
        ("Optional[str]", False, "Union[str, None, UnsetType]"),
        ("Union[str, int]", False, "Union[str, int, UnsetType]"),
        ("Union[str, None]", False, "Union[str, None, UnsetType]"),
        (
            "Annotated[Optional[str], Meta(min_length=1)]",
            False,
            "Union[Annotated[Optional[str], Meta(min_length=1)], UnsetType]",
        ),
        ("list[Union[str, int]]", False, "Union[list[Union[str, int]], UnsetType]"),
        ("str | None", True, "str | None | UnsetType"),
    ],
)
def test_add_unset_type(type_hint: str, use_union_operator: bool, expected: str) -> None:
    """Add UnsetType to optional fields while preserving existing type hint shapes."""
    assert _add_unset_type(type_hint, use_union_operator) == expected
