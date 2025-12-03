"""Tests for field name resolver functionality."""

from __future__ import annotations

import pytest

from datamodel_code_generator.reference import FieldNameResolver


@pytest.mark.parametrize(
    ("name", "expected_resolved"),
    [
        ("3a", "field_3a"),
        ("$in", "field_in"),
        ("field", "field"),
    ],
)
def test_get_valid_field_name(name: str, expected_resolved: str) -> None:
    """Test field name resolution to valid Python identifiers."""
    resolver = FieldNameResolver()
    assert expected_resolved == resolver.get_valid_name(name)


def test_hierarchical_flat_alias() -> None:
    """Test traditional flat alias resolution."""
    resolver = FieldNameResolver(aliases={"name": "name_alias"})
    field_name, alias = resolver.get_valid_field_name_and_alias("name")
    assert field_name == "name_alias"
    assert alias == "name"


def test_hierarchical_scoped_alias() -> None:
    """Test scoped alias resolution (ClassName.field)."""
    resolver = FieldNameResolver(
        aliases={
            "User.name": "user_name",
            "Address.name": "address_name",
            "name": "default_name",
        }
    )

    field_name, alias = resolver.get_valid_field_name_and_alias("name", class_name="User")
    assert field_name == "user_name"
    assert alias == "name"

    field_name, alias = resolver.get_valid_field_name_and_alias("name", class_name="Address")
    assert field_name == "address_name"
    assert alias == "name"

    field_name, alias = resolver.get_valid_field_name_and_alias("name", class_name="Other")
    assert field_name == "default_name"
    assert alias == "name"


def test_hierarchical_alias_priority() -> None:
    """Test that scoped aliases have priority over flat aliases."""
    resolver = FieldNameResolver(
        aliases={
            "User.name": "scoped_name",
            "name": "flat_name",
        }
    )

    field_name, _ = resolver.get_valid_field_name_and_alias("name", class_name="User")
    assert field_name == "scoped_name"

    field_name, _ = resolver.get_valid_field_name_and_alias("name", class_name="Other")
    assert field_name == "flat_name"


def test_hierarchical_class_name_provided_but_no_scoped_aliases() -> None:
    """Test when class_name is provided but no scoped aliases are configured."""
    resolver = FieldNameResolver(aliases={"name": "name_alias"})
    field_name, alias = resolver.get_valid_field_name_and_alias("name", class_name="User")
    assert field_name == "name_alias"
    assert alias == "name"


def test_hierarchical_scoped_alias_not_matching() -> None:
    """Test when scoped alias exists but doesn't match current class."""
    resolver = FieldNameResolver(
        aliases={
            "Other.name": "other_name",
            "name": "default_name",
        }
    )
    field_name, alias = resolver.get_valid_field_name_and_alias("name", class_name="User")
    assert field_name == "default_name"
    assert alias == "name"


def test_hierarchical_no_alias_match() -> None:
    """Test that unmatched fields return valid name without alias."""
    resolver = FieldNameResolver(aliases={"other": "other_alias"})
    field_name, alias = resolver.get_valid_field_name_and_alias("name")
    assert field_name == "name"
    assert alias is None


def test_hierarchical_backward_compatibility() -> None:
    """Test that existing flat alias behavior is preserved."""
    resolver = FieldNameResolver(aliases={"name": "name_", "id": "id_"})
    field_name, alias = resolver.get_valid_field_name_and_alias("name")
    assert field_name == "name_"
    assert alias == "name"

    field_name, alias = resolver.get_valid_field_name_and_alias("id")
    assert field_name == "id_"
    assert alias == "id"


def test_hierarchical_dotted_field_name_alias() -> None:
    """Test that field names containing dots can be aliased (backward compat)."""
    resolver = FieldNameResolver(aliases={"filter.name": "filter_name_alias"})
    field_name, alias = resolver.get_valid_field_name_and_alias("filter.name")
    assert field_name == "filter_name_alias"
    assert alias == "filter.name"


def test_hierarchical_dotted_field_name_without_class_name() -> None:
    """Test dotted field name alias works without class_name parameter."""
    resolver = FieldNameResolver(
        aliases={
            "a.b": "a_b_alias",
            "User.name": "user_name",
        }
    )
    field_name, alias = resolver.get_valid_field_name_and_alias("a.b")
    assert field_name == "a_b_alias"
    assert alias == "a.b"


def test_hierarchical_path_parameter_backward_compatibility() -> None:
    """Test that path parameter is accepted but ignored."""
    resolver = FieldNameResolver(aliases={"name": "name_alias"})
    field_name, alias = resolver.get_valid_field_name_and_alias("name", path=["root", "properties", "name"])
    assert field_name == "name_alias"
    assert alias == "name"
