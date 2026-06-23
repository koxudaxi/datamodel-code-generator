"""Tests for msgspec model helpers."""

from __future__ import annotations

import pytest

from datamodel_code_generator.model.msgspec import (
    _add_unset_type,
    _get_top_level_typing_args,
    _get_top_level_typing_subscript,
    get_neither_required_nor_nullable_type,
)


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


@pytest.mark.allow_direct_assert
@pytest.mark.parametrize(
    ("type_hint", "expected"),
    [
        ("Optional[str]", ("Optional", "str")),
        ("Union[str, int]", ("Union", "str, int")),
        ("typing.Optional[str]", None),
        ("list[Union[str, int]]", None),
        ("str", None),
        ("[", None),
    ],
)
def test_get_top_level_typing_subscript(type_hint: str, expected: tuple[str, str] | None) -> None:
    """Parse only top-level Optional and Union wrappers."""
    assert _get_top_level_typing_subscript(type_hint) == expected


@pytest.mark.allow_direct_assert
@pytest.mark.parametrize(
    ("type_hint", "expected_name", "expected"),
    [
        ("Optional[str]", "Optional", "str"),
        ("Optional[str]", "Union", None),
        ("list[str]", "Optional", None),
    ],
)
def test_get_top_level_typing_args(type_hint: str, expected_name: str, expected: str | None) -> None:
    """Return args only for the requested wrapper name."""
    assert _get_top_level_typing_args(type_hint, expected_name) == expected


@pytest.mark.allow_direct_assert
def test_get_top_level_typing_subscript_without_source_segment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return None when ast cannot provide a source segment."""
    monkeypatch.setattr("datamodel_code_generator.model.msgspec.ast.get_source_segment", lambda *_: None)
    _get_top_level_typing_subscript.cache_clear()

    try:
        assert _get_top_level_typing_subscript("Optional[str]") is None
    finally:
        _get_top_level_typing_subscript.cache_clear()
