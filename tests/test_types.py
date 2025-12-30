"""Tests for type manipulation utilities."""

from __future__ import annotations

import pytest

from datamodel_code_generator.types import (
    _remove_none_from_union,
    extract_qualified_names,
    get_optional_type,
    get_subscript_args,
    get_type_base_name,
)


@pytest.mark.parametrize(
    ("input_", "use_union_operator", "expected"),
    [
        ("List[str]", False, "Optional[List[str]]"),
        ("List[str, int, float]", False, "Optional[List[str, int, float]]"),
        ("List[str, int, None]", False, "Optional[List[str, int, None]]"),
        ("Union[str]", False, "Optional[str]"),
        ("Union[str, int, float]", False, "Optional[Union[str, int, float]]"),
        ("Union[str, int, None]", False, "Optional[Union[str, int]]"),
        ("Union[str, int, None, None]", False, "Optional[Union[str, int]]"),
        (
            "Union[str, int, List[str, int, None], None]",
            False,
            "Optional[Union[str, int, List[str, int, None]]]",
        ),
        (
            "Union[str, int, List[str, Dict[int, str | None]], None]",
            False,
            "Optional[Union[str, int, List[str, Dict[int, str | None]]]]",
        ),
        ("List[str]", True, "List[str] | None"),
        ("List[str | int | float]", True, "List[str | int | float] | None"),
        ("List[str | int | None]", True, "List[str | int | None] | None"),
        ("str", True, "str | None"),
        ("str | int | float", True, "str | int | float | None"),
        ("str | int | None", True, "str | int | None"),
        ("str | int | None | None", True, "str | int | None"),
        (
            "str | int | List[str | Dict[int | Union[str | None]]] | None",
            True,
            "str | int | List[str | Dict[int | Union[str | None]]] | None",
        ),
    ],
)
def test_get_optional_type(input_: str, use_union_operator: bool, expected: str) -> None:
    """Test get_optional_type function with various type strings."""
    assert get_optional_type(input_, use_union_operator) == expected


@pytest.mark.parametrize(
    ("type_str", "use_union_operator", "expected"),
    [
        # Traditional Union syntax
        ("Union[str, None]", False, "str"),
        ("Union[str, int, None]", False, "Union[str, int]"),
        ("Union[None, str]", False, "str"),
        ("Union[None]", False, "None"),
        ("Union[None, None]", False, "None"),
        ("Union[Union[str, None], int]", False, "Union[str, int]"),
        # Union for constraint strings with pattern or regex
        (
            "Union[constr(pattern=r'^a,b$'), None]",
            False,
            "constr(pattern=r'^a,b$')",
        ),
        (
            "Union[constr(regex=r'^a,b$'), None]",
            False,
            "constr(regex=r'^a,b$')",
        ),
        (
            "Union[constr(pattern=r'^\\d+,\\w+$'), None]",
            False,
            "constr(pattern=r'^\\d+,\\w+$')",
        ),
        (
            "Union[constr(regex=r'^\\d+,\\w+$'), None]",
            False,
            "constr(regex=r'^\\d+,\\w+$')",
        ),
        # Union operator syntax
        ("str | None", True, "str"),
        ("int | str | None", True, "int | str"),
        ("None | str", True, "str"),
        ("None | None", True, "None"),
        ("constr(pattern='0|1') | None", True, "constr(pattern='0|1')"),
        ("constr(pattern='0  |1') | int | None", True, "constr(pattern='0  |1') | int"),
        # Complex nested types - traditional syntax
        ("Union[str, int] | None", True, "Union[str, int]"),
        (
            "Optional[List[Dict[str, Any]]] | None",
            True,
            "Optional[List[Dict[str, Any]]]",
        ),
        # Union for constraint strings with pattern or regex on nested types
        (
            "Union[constr(pattern=r'\\['), Union[str, None], int]",
            False,
            "Union[constr(pattern=r'\\['), str, int]",
        ),
        (
            "Union[constr(regex=r'\\['), Union[str, None], int]",
            False,
            "Union[constr(regex=r'\\['), str, int]",
        ),
        # Complex nested types - union operator syntax
        ("List[str | None] | None", True, "List[str | None]"),
        (
            "List[constr(pattern='0|1') | None] | None",
            True,
            "List[constr(pattern='0|1') | None]",
        ),
        (
            "List[constr(pattern='0 | 1') | None] | None",
            True,
            "List[constr(pattern='0 | 1') | None]",
        ),
        (
            "List[constr(pattern='0  | 1') | None] | None",
            True,
            "List[constr(pattern='0  | 1') | None]",
        ),
        ("Dict[str, int] | None | List[str]", True, "Dict[str, int] | List[str]"),
        # Edge cases that test the fixed regex pattern issue
        ("List[str] | None", True, "List[str]"),
        ("Dict[str, int] | None", True, "Dict[str, int]"),
        ("Tuple[int, ...] | None", True, "Tuple[int, ...]"),
        ("Callable[[int], str] | None", True, "Callable[[int], str]"),
        # Non-union types (should be returned as-is)
        ("str", False, "str"),
        ("List[str]", False, "List[str]"),
    ],
)
def test_remove_none_from_union(type_str: str, use_union_operator: bool, expected: str) -> None:
    """Test _remove_none_from_union function with various type strings."""
    assert _remove_none_from_union(type_str, use_union_operator=use_union_operator) == expected


@pytest.mark.parametrize(
    ("type_str", "use_union_operator", "expected"),
    [
        ("(", False, "("),
        (")", False, ")"),
        ("()", False, "()"),
        ("a(", False, "a("),
        ("constr()", False, "constr()"),
        ("constr(pattern=')')", False, "constr(pattern=')')"),
        ("Union[constr()]", False, "constr()"),
        ("a | b", True, "a | b"),
        ("(a)", True, "(a)"),
    ],
)
def test_remove_none_from_union_short_strings(type_str: str, use_union_operator: bool, expected: str) -> None:
    """Test _remove_none_from_union with short strings to verify index bounds safety."""
    assert _remove_none_from_union(type_str, use_union_operator=use_union_operator) == expected


def test_datatype_deepcopy_with_circular_references() -> None:
    """Test that DataType.__deepcopy__ handles circular references via parent/children.

    This test verifies the fix for the recursion error that occurred when deepcopying
    DataType objects with circular references through parent and children fields.
    """
    from copy import deepcopy

    # Import DataModelFieldBase first to trigger model_rebuild
    from datamodel_code_generator.model.base import DataModelFieldBase  # noqa: F401
    from datamodel_code_generator.types import DataType

    # Create parent and child DataTypes with circular references
    parent = DataType(type="ParentType")
    child1 = DataType(type="ChildType1", parent=parent)
    child2 = DataType(type="ChildType2", parent=parent)
    parent.children = [child1, child2]

    # This should not cause infinite recursion
    copied_parent = deepcopy(parent)

    # Verify the copy was successful
    assert copied_parent.type == "ParentType"
    # parent and children should be None in the copy (excluded from deepcopy)
    assert copied_parent.parent is None
    assert copied_parent.children is None


def test_datatype_deepcopy_with_nested_data_types() -> None:
    """Test that DataType.__deepcopy__ properly copies nested data_types."""
    from copy import deepcopy

    # Import DataModelFieldBase first to trigger model_rebuild
    from datamodel_code_generator.model.base import DataModelFieldBase  # noqa: F401
    from datamodel_code_generator.types import DataType

    # Create nested DataTypes
    inner = DataType(type="InnerType", is_optional=True)
    outer = DataType(type="OuterType", data_types=[inner], is_list=True)

    # Deepcopy should work and create independent copies
    copied_outer = deepcopy(outer)

    # Verify the structure is preserved
    assert copied_outer.type == "OuterType"
    assert copied_outer.is_list is True
    assert len(copied_outer.data_types) == 1
    assert copied_outer.data_types[0].type == "InnerType"
    assert copied_outer.data_types[0].is_optional is True

    # Verify it's a deep copy (modifying original doesn't affect copy)
    inner.type = "ModifiedInnerType"
    assert copied_outer.data_types[0].type == "InnerType"


def test_datatype_deepcopy_memo_prevents_duplicate_copies() -> None:
    """Test that the memo dictionary prevents duplicate copies of the same object."""
    from copy import deepcopy

    # Import DataModelFieldBase first to trigger model_rebuild
    from datamodel_code_generator.model.base import DataModelFieldBase  # noqa: F401
    from datamodel_code_generator.types import DataType

    # Create a shared DataType referenced by multiple parents
    shared = DataType(type="SharedType")
    container1 = DataType(type="Container1", data_types=[shared])
    container2 = DataType(type="Container2", data_types=[shared])
    root = DataType(type="Root", data_types=[container1, container2])

    # Deepcopy should handle the shared reference
    copied_root = deepcopy(root)

    # Verify structure is correct
    assert copied_root.type == "Root"
    assert len(copied_root.data_types) == 2
    assert copied_root.data_types[0].type == "Container1"
    assert copied_root.data_types[1].type == "Container2"

    # Both containers should have copies of the shared type
    assert copied_root.data_types[0].data_types[0].type == "SharedType"
    assert copied_root.data_types[1].data_types[0].type == "SharedType"

    # Verify that the same object is returned from memo (memoization behavior)
    assert copied_root.data_types[0].data_types[0] is copied_root.data_types[1].data_types[0]


def test_datatype_deepcopy_with_none_memo() -> None:
    """Test __deepcopy__ when called with memo=None (covers memo initialization)."""
    # Import DataModelFieldBase first to trigger model_rebuild
    from datamodel_code_generator.model.base import DataModelFieldBase  # noqa: F401
    from datamodel_code_generator.types import DataType

    data_type = DataType(type="TestType", is_optional=True)

    # Call __deepcopy__ directly with None memo to cover the `if memo is None` branch
    copied = data_type.__deepcopy__(None)  # noqa: PLC2801

    assert copied.type == "TestType"
    assert copied.is_optional is True
    assert copied is not data_type


def test_datatype_deepcopy_memo_cache_hit() -> None:
    """Test that memo cache returns the same object for repeated references."""
    # Import DataModelFieldBase first to trigger model_rebuild
    from datamodel_code_generator.model.base import DataModelFieldBase  # noqa: F401
    from datamodel_code_generator.types import DataType

    data_type = DataType(type="TestType")
    memo: dict[int, DataType] = {}

    # First call - should create new object and store in memo
    copied1 = data_type.__deepcopy__(memo)  # noqa: PLC2801
    assert copied1 is not data_type
    assert id(data_type) in memo

    # Second call with same memo - should return cached object (covers memo hit branch)
    copied2 = data_type.__deepcopy__(memo)  # noqa: PLC2801
    assert copied2 is copied1  # Same object from memo


@pytest.mark.parametrize(
    ("type_str", "expected"),
    [
        # Simple types
        ("str", "str"),
        ("int", "int"),
        ("List", "List"),
        # Subscripted types
        ("List[str]", "List"),
        ("Dict[str, int]", "Dict"),
        ("Optional[int]", "Optional"),
        ("Union[str, int]", "Union"),
        # Qualified names
        ("foo.bar.Baz", "Baz"),
        ("datamodel_code_generator.model.base.DataModel", "DataModel"),
        # Subscripted with qualified names
        ("type[foo.bar.Baz]", "type"),
        ("List[foo.Bar]", "List"),
        # Invalid syntax (fallback to string parsing)
        ("List[", "List"),
        ("[invalid", ""),  # splits on "[" giving empty string
    ],
)
def test_get_type_base_name(type_str: str, expected: str) -> None:
    """Test get_type_base_name extracts base type correctly."""
    assert get_type_base_name(type_str) == expected


@pytest.mark.parametrize(
    ("type_str", "expected"),
    [
        # Simple types (no subscript)
        ("str", []),
        ("int", []),
        # Single argument
        ("List[str]", ["str"]),
        ("Optional[int]", ["int"]),
        ("type[Foo]", ["Foo"]),
        # Multiple arguments
        ("Dict[str, int]", ["str", "int"]),
        ("Union[str, int, None]", ["str", "int", "None"]),
        ("Tuple[int, str, float]", ["int", "str", "float"]),
        # Union operator syntax
        ("str | int", ["str", "int"]),
        ("str | int | None", ["str", "int", "None"]),
        ("List[str] | None", ["List[str]", "None"]),
        # Complex nested types
        ("Dict[str, List[int]]", ["str", "List[int]"]),
        ("Union[List[str], Dict[str, int]]", ["List[str]", "Dict[str, int]"]),
        # Qualified names in arguments
        ("type[foo.bar.Baz]", ["foo.bar.Baz"]),
        ("Dict[a.B, c.D]", ["a.B", "c.D"]),
        # Invalid syntax
        ("List[", []),
        ("[invalid", []),
    ],
)
def test_get_subscript_args(type_str: str, expected: list[str]) -> None:
    """Test get_subscript_args extracts type arguments correctly."""
    assert get_subscript_args(type_str) == expected


@pytest.mark.parametrize(
    ("type_str", "expected"),
    [
        # No qualified names
        ("str", []),
        ("List[str]", []),
        ("Union[str, int]", []),
        # Single qualified name
        ("foo.Bar", ["foo.Bar"]),
        ("foo.bar.Baz", ["foo.bar.Baz"]),
        ("datamodel_code_generator.model.base.DataModel", ["datamodel_code_generator.model.base.DataModel"]),
        # Qualified names in subscript
        ("type[foo.bar.Baz]", ["foo.bar.Baz"]),
        ("List[foo.Bar]", ["foo.Bar"]),
        ("Optional[a.b.C]", ["a.b.C"]),
        # Multiple qualified names
        ("Dict[a.B, c.D]", ["a.B", "c.D"]),
        ("Union[foo.Bar, baz.Qux]", ["foo.Bar", "baz.Qux"]),
        # Mixed with simple types
        ("Dict[str, foo.Bar]", ["foo.Bar"]),
        ("Union[int, a.B, None]", ["a.B"]),
        # Union operator syntax
        ("foo.Bar | None", ["foo.Bar"]),
        ("a.B | c.D", ["a.B", "c.D"]),
        # Complex nested
        ("Dict[str, List[foo.Bar]]", ["foo.Bar"]),
        ("type[datamodel_code_generator.types.DataTypeManager]", ["datamodel_code_generator.types.DataTypeManager"]),
        # Attribute on non-Name (function call result) - should not extract
        ("foo().bar", []),
        ("func().attr.name", []),
        # Invalid syntax
        ("foo.Bar[", []),
    ],
)
def test_extract_qualified_names(type_str: str, expected: list[str]) -> None:
    """Test extract_qualified_names finds all fully qualified names."""
    assert extract_qualified_names(type_str) == expected
