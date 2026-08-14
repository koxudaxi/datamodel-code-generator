"""Tests for field name resolver functionality."""

from __future__ import annotations

from typing import cast

import pytest

from datamodel_code_generator.reference import FieldNameResolver, ModelResolver, PydanticFieldNameResolver


@pytest.mark.parametrize(
    ("name", "expected_resolved"),
    [
        ("3a", "field_3a"),
        ("$in", "field_in"),
        ("field", "field"),
        ("ำ62", "field_ue33_62"),
    ],
)
def test_get_valid_field_name(name: str, expected_resolved: str) -> None:
    """Test field name resolution to valid Python identifiers."""
    resolver = FieldNameResolver()
    assert expected_resolved == resolver.get_valid_name(name)


@pytest.mark.parametrize(
    (
        "name",
        "excludes",
        "snake_case_field",
        "capitalise_enum_members",
        "ignore_snake_case_field",
        "upper_camel",
    ),
    [
        pytest.param("account_id", None, False, False, False, False, id="snake-case"),
        pytest.param("displayName", None, False, False, False, False, id="camel-case"),
        pytest.param("version2", None, False, False, False, False, id="trailing-number"),
        pytest.param("café", None, False, False, False, False, id="non-ascii-identifier"),
        pytest.param("json", None, False, False, False, False, id="pydantic-reserved"),
        pytest.param("display-name", None, False, False, False, False, id="non-identifier"),
        pytest.param("_private", None, False, False, False, False, id="private-name"),
        pytest.param("class", None, False, False, False, False, id="keyword"),
        pytest.param("account_id", {"account_id"}, False, False, False, False, id="excluded"),
        pytest.param("displayName", None, True, False, False, False, id="snake-case-conversion"),
        pytest.param("displayName", None, True, False, True, False, id="ignore-snake-case"),
        pytest.param("account_id", None, False, True, False, False, id="enum-capitalization"),
        pytest.param("account_id", None, False, False, False, True, id="upper-camel"),
    ],
)
def test_pydantic_field_name_fast_path_matches_conventional_resolution(
    name: str,
    excludes: set[str] | None,
    snake_case_field: bool,
    capitalise_enum_members: bool,
    ignore_snake_case_field: bool,
    upper_camel: bool,
) -> None:
    """Keep the built-in fast path equivalent to the conventional resolver."""
    resolver = PydanticFieldNameResolver(
        snake_case_field=snake_case_field,
        capitalise_enum_members=capitalise_enum_members,
    )
    conventional_resolver = _ConventionalPydanticFieldNameResolver(
        snake_case_field=snake_case_field,
        capitalise_enum_members=capitalise_enum_members,
    )
    assert resolver.get_valid_name(
        name,
        excludes=excludes,
        ignore_snake_case_field=ignore_snake_case_field,
        upper_camel=upper_camel,
    ) == conventional_resolver.get_valid_name(
        name,
        excludes=excludes,
        ignore_snake_case_field=ignore_snake_case_field,
        upper_camel=upper_camel,
    )


class _ConventionalPydanticFieldNameResolver(PydanticFieldNameResolver):
    """Use the conventional path to compare against the exact built-in resolver."""


class _CustomPydanticFieldNameResolver(PydanticFieldNameResolver):
    """Record validation calls made by the extension-compatible path."""

    def __init__(self) -> None:
        super().__init__()
        self.validation_calls = 0

    def _validate_field_name(self, field_name: str) -> bool:
        del field_name
        self.validation_calls += 1
        return True


def test_pydantic_field_name_fast_path_preserves_subclass_validation_behavior() -> None:
    """Keep custom Pydantic resolvers on the existing validation path."""
    resolver = _CustomPydanticFieldNameResolver()

    assert resolver.get_valid_name("account_id") == "account_id"
    assert resolver.validation_calls == 2


def test_get_valid_field_name_alias_for_unicode_ncname() -> None:
    """Keep the source name as an alias when XML NCName is not a Python identifier."""
    resolver = FieldNameResolver()
    field_name, alias = resolver.get_valid_field_name_and_alias("ำ62")
    assert field_name == "field_ue33_62"
    assert alias == "ำ62"


def test_get_valid_field_name_upper_camel_unicode_ncname() -> None:
    """Apply stable fallback names before upper-camel conversion."""
    resolver = FieldNameResolver()
    assert resolver.get_valid_name("ำ62", upper_camel=True) == "FieldUe3362"


def test_get_valid_field_name_enum_unicode_ncname() -> None:
    """Apply stable fallback names before enum member capitalization."""
    resolver = FieldNameResolver(capitalise_enum_members=True)
    assert resolver.get_valid_name("ำ62") == "FIELD_UE33_62"


def test_ascii_identifier_fallback_prefixes_empty_and_numeric_names() -> None:
    """Generate stable fallback names for values that cannot stand as identifiers."""
    resolver = FieldNameResolver()
    assert resolver._ascii_identifier_fallback("") == "field_"
    assert resolver._ascii_identifier_fallback("1") == "field_1"
    assert resolver._ascii_identifier_fallback("aำ") == "a_ue33_"


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


def test_multiple_aliases_flat() -> None:
    """Test multiple aliases return list including original field name."""
    resolver = FieldNameResolver(aliases={"my_field": ["my-field", "myField"]})
    field_name, aliases = resolver.get_valid_field_name_and_alias("my_field")
    assert field_name == "my_field"  # First alias validated to valid identifier
    assert aliases == ["my_field", "my-field", "myField"]  # Original + all aliases


def test_multiple_aliases_scoped() -> None:
    """Test multiple aliases with scoped format (ClassName.field)."""
    resolver = FieldNameResolver(
        aliases={
            "User.name": ["user-name", "userName"],
            "name": ["default-name", "defaultName"],
        }
    )

    field_name, aliases = resolver.get_valid_field_name_and_alias("name", class_name="User")
    assert field_name == "user_name"  # Hyphen converted to valid identifier
    assert aliases == ["name", "user-name", "userName"]

    field_name, aliases = resolver.get_valid_field_name_and_alias("name", class_name="Other")
    assert field_name == "default_name"  # Hyphen converted to valid identifier
    assert aliases == ["name", "default-name", "defaultName"]


def test_multiple_aliases_mixed_with_single() -> None:
    """Test mixing multiple aliases with single aliases."""
    resolver = FieldNameResolver(
        aliases={
            "multi": ["alias1", "alias2"],
            "single": "single_alias",
        }
    )

    field_name, aliases = resolver.get_valid_field_name_and_alias("multi")
    assert field_name == "alias1"
    assert aliases == ["multi", "alias1", "alias2"]

    field_name, alias = resolver.get_valid_field_name_and_alias("single")
    assert field_name == "single_alias"
    assert alias == "single"


def test_empty_list_aliases_flat() -> None:
    """Test empty list aliases are ignored and field is treated as no alias."""
    resolver = FieldNameResolver(aliases={"my_field": []})
    field_name, alias = resolver.get_valid_field_name_and_alias("my_field")
    assert field_name == "my_field"
    assert alias is None  # Empty list is ignored


def test_empty_list_aliases_scoped() -> None:
    """Test empty list aliases with scoped format are ignored."""
    resolver = FieldNameResolver(aliases={"User.name": []})
    field_name, alias = resolver.get_valid_field_name_and_alias("name", class_name="User")
    assert field_name == "name"
    assert alias is None  # Empty list is ignored


def test_unsupported_alias_values_are_ignored() -> None:
    """Alias values that are neither strings nor non-empty lists fall through."""
    resolver = FieldNameResolver(aliases=cast("dict[str, str | list[str]]", {"name": ("alias",)}))

    field_name, alias = resolver.get_valid_field_name_and_alias("name")

    assert field_name == "name"
    assert alias is None


def test_alias_lists_with_non_string_values_are_ignored() -> None:
    """Alias lists must contain only strings before they are used."""
    resolver = FieldNameResolver(aliases=cast("dict[str, str | list[str]]", {"name": [123, "alias"]}))

    field_name, alias = resolver.get_valid_field_name_and_alias("name")

    assert field_name == "name"
    assert alias is None


def test_model_resolver_unique_name_hints_keep_numbered_sequence() -> None:
    """Keep duplicate model names in the same numbered order while storing the next hint."""
    resolver = ModelResolver()

    names = [resolver.add(["models", str(index)], "Name", class_name=True).name for index in range(5)]

    assert names == ["Name", "Name1", "Name2", "Name3", "Name4"]
    assert resolver._unique_name_start_hints["Name", "", ""] == 5


def test_model_resolver_unique_name_direct_probe_does_not_consume_hint() -> None:
    """Keep direct uniqueness probes stable when the returned name is not registered."""
    resolver = ModelResolver()
    resolver.add(["models", "0"], "Name", class_name=True)

    assert resolver._get_unique_name("Name", camel=True) == "Name1"
    assert resolver._get_unique_name("Name", camel=True) == "Name1"


def test_model_resolver_unique_name_hints_reuse_deleted_suffix() -> None:
    """Reuse a freed duplicate suffix after deleting a reference."""
    resolver = ModelResolver()
    for index in range(4):
        resolver.add(["models", str(index)], "Name", class_name=True)

    resolver.delete(["models", "1"])

    assert resolver.add(["models", "next"], "Name", class_name=True).name == "Name1"


def test_model_resolver_unique_name_hints_reuse_renamed_suffix() -> None:
    """Reuse a freed duplicate suffix after renaming an existing reference."""
    resolver = ModelResolver()
    for index in range(3):
        resolver.add(["models", str(index)], "Name", class_name=True)

    resolver.add(["models", "1"], "Other", class_name=True)

    assert resolver.add(["models", "next"], "Name", class_name=True).name == "Name1"


def test_model_resolver_unique_name_hints_clear_on_reuse_reset() -> None:
    """Clear duplicate-name hints when the resolver naming state is reset."""
    resolver = ModelResolver()
    for index in range(3):
        resolver.add(["models", str(index)], "Name", class_name=True)

    resolver._reset_for_reuse({"Name"})

    assert resolver._unique_name_start_hints == {}
    assert resolver.add(["models", "next"], "Name", class_name=True).name == "Name1"


def test_model_resolver_unique_name_hints_reuse_custom_suffix() -> None:
    """Reuse a freed duplicate suffix when duplicate-name-suffix is configured."""
    resolver = ModelResolver(duplicate_name_suffix_map={"model": "Schema"})
    names = [resolver.add(["models", str(index)], "Name", class_name=True).name for index in range(4)]

    assert names == ["Name", "NameSchema", "NameSchema1", "NameSchema2"]

    resolver.delete(["models", "1"])

    assert resolver.add(["models", "next"], "Name", class_name=True).name == "NameSchema"


def test_model_resolver_unique_name_hints_invalidate_delimited_suffix() -> None:
    """Invalidate suffix hints for non-camel duplicate names."""
    resolver = ModelResolver()
    resolver._unique_name_start_hints["Name", "Schema", "_"] = 3

    resolver._invalidate_unique_name_hints("Name_Schema_1")

    assert resolver._unique_name_start_hints == {}


def test_model_resolver_unique_name_hints_scale_same_enum_names() -> None:
    """Keep hundreds of duplicate enum names in the same numbered order."""
    resolver = ModelResolver()

    names = [
        resolver.add(["enums", str(index)], "Status", class_name=True, model_type="enum").name for index in range(300)
    ]

    assert names[:4] == ["Status", "Status1", "Status2", "Status3"]
    assert names[-1] == "Status299"
