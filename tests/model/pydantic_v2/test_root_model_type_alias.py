"""Tests for Pydantic v2 RootModel type alias generation."""

from __future__ import annotations

from datamodel_code_generator.model import DataModelFieldBase
from datamodel_code_generator.model.pydantic_v2.root_model_type_alias import RootModelTypeAlias
from datamodel_code_generator.reference import Reference
from datamodel_code_generator.types import DataType


def test_root_model_type_alias() -> None:
    """Test RootModelTypeAlias generates type alias format."""
    root_model = RootModelTypeAlias(
        fields=[
            DataModelFieldBase(
                name="root",
                data_type=DataType(type="str"),
                required=True,
            )
        ],
        reference=Reference(name="TestRootModel", path="test_root_model"),
    )

    assert root_model.name == "TestRootModel"
    assert root_model.IS_ALIAS is True
    assert root_model.render() == "TestRootModel = RootModel[str]"


def test_root_model_type_alias_with_union() -> None:
    """Test RootModelTypeAlias with union type."""
    root_model = RootModelTypeAlias(
        fields=[
            DataModelFieldBase(
                name="root",
                data_type=DataType(type="str | int"),
                required=True,
            )
        ],
        reference=Reference(name="StringOrInt", path="string_or_int"),
    )

    assert root_model.render() == "StringOrInt = RootModel[str | int]"


def test_root_model_type_alias_with_optional() -> None:
    """Test RootModelTypeAlias with optional type."""
    root_model = RootModelTypeAlias(
        fields=[
            DataModelFieldBase(
                name="root",
                data_type=DataType(type="str"),
                required=False,
            )
        ],
        reference=Reference(name="OptionalString", path="optional_string"),
    )

    assert root_model.render() == "OptionalString = RootModel[Optional[str]]"
