"""Tests for Pydantic v2 RootModel generation."""

from __future__ import annotations

from collections import defaultdict

import pytest

from datamodel_code_generator.model import DataModelFieldBase
from datamodel_code_generator.model.pydantic_v2.base_model import _CONFIG_ITEMS_TEMPLATE_DATA_KEY
from datamodel_code_generator.model.pydantic_v2.root_model import RootModel
from datamodel_code_generator.reference import Reference
from datamodel_code_generator.types import DataType


def test_root_model() -> None:
    """Test RootModel generation with optional field."""
    root_model = RootModel(
        fields=[
            DataModelFieldBase(
                name="a",
                data_type=DataType(type="str"),
                default="abc",
                required=False,
            )
        ],
        reference=Reference(name="TestRootModel", path="test_root_model"),
    )

    assert root_model.name == "TestRootModel"
    assert root_model.fields == [
        DataModelFieldBase(
            name="a",
            data_type=DataType(type="str"),
            default="abc",
            required=False,
            parent=root_model,
        )
    ]

    assert root_model.base_class == "RootModel"
    assert root_model.custom_base_class is None
    assert root_model.render() == ("class TestRootModel(RootModel[Optional[str]]):\n    root: Optional[str] = 'abc'")


def test_root_model_sequence_methods() -> None:
    """RootModel can render sequence helpers."""
    root_model = RootModel(
        fields=[
            DataModelFieldBase(
                name="a",
                data_type=DataType(
                    type="str",
                    is_list=True,
                    data_types=[DataType(type="str")],
                    use_standard_collections=True,
                ),
                required=True,
            )
        ],
        reference=Reference(name="TestRootModel", path="test_root_model"),
    )

    root_model.add_sequence_methods("str", "list[str]")

    assert root_model.render() == (
        "class TestRootModel(RootModel[list[str]]):\n"
        "    root: list[str]\n\n"
        "    def __iter__(self) -> Iterator[str]:\n"
        "        return iter(self.root)\n\n"
        "    @overload\n"
        "    def __getitem__(self, index: SupportsIndex) -> str: ...\n\n"
        "    @overload\n"
        "    def __getitem__(self, index: slice) -> list[str]: ...\n\n"
        "    def __getitem__(self, index: SupportsIndex | slice) -> str | list[str]:\n"
        "        return self.root[index]\n\n"
        "    def __len__(self) -> int:\n"
        "        return len(self.root)"
    )
    assert any(import_.import_ == "Iterator" for import_ in root_model.imports)
    assert any(import_.import_ == "overload" for import_ in root_model.imports)
    assert any(import_.import_ == "SupportsIndex" for import_ in root_model.imports)


def test_root_model_sequence_methods_add_any_import() -> None:
    """Sequence helpers import Any when the wrapped item type is Any."""
    root_model = RootModel(
        fields=[
            DataModelFieldBase(
                name="a",
                data_type=DataType(is_list=True, data_types=[DataType()]),
                required=True,
            )
        ],
        reference=Reference(name="TestRootModel", path="test_root_model"),
    )

    root_model.add_sequence_methods("Any", "list[Any]")

    assert "def __iter__(self) -> Iterator[Any]" in root_model.render()
    assert any(import_.import_ == "Any" for import_ in root_model.imports)


def test_root_model_custom_base_class_is_ignored() -> None:
    """Verify that passing a custom_base_class is ignored."""
    root_model = RootModel(
        custom_base_class="test.Test",
        fields=[
            DataModelFieldBase(
                name="a",
                data_type=DataType(type="str"),
                default="abc",
                required=False,
            )
        ],
        reference=Reference(name="TestRootModel", path="test_root_model"),
    )

    assert root_model.name == "TestRootModel"
    assert root_model.fields == [
        DataModelFieldBase(
            name="a",
            data_type=DataType(type="str"),
            default="abc",
            required=False,
            parent=root_model,
        )
    ]

    assert root_model.base_class == "RootModel"
    assert root_model.custom_base_class is None  # make sure it's ignored
    assert root_model.render() == ("class TestRootModel(RootModel[Optional[str]]):\n    root: Optional[str] = 'abc'")


@pytest.mark.parametrize("additional_properties", [True, False])
def test_root_model_ignores_extra_config(additional_properties: bool) -> None:
    """RootModel must not render ConfigDict(extra=...) because Pydantic rejects it."""
    root_model = RootModel(
        fields=[
            DataModelFieldBase(
                name="a",
                data_type=DataType(type="str"),
                required=True,
            )
        ],
        reference=Reference(name="TestRootModel", path="test_root_model"),
        extra_template_data=defaultdict(dict, {"test_root_model": {"additionalProperties": additional_properties}}),
    )

    assert "model_config" not in root_model.render()
    assert _CONFIG_ITEMS_TEMPLATE_DATA_KEY not in root_model.extra_template_data


def test_root_model_ignores_arbitrary_types_config() -> None:
    """RootModel must not render arbitrary_types_allowed for custom root types."""
    root_model = RootModel(
        fields=[
            DataModelFieldBase(
                name="a",
                data_type=DataType(type="ExternalType", is_custom_type=True),
                required=True,
            )
        ],
        reference=Reference(name="TestRootModel", path="test_root_model"),
    )

    assert "model_config" not in root_model.render()
