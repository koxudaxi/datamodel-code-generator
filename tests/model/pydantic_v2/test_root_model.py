"""Tests for Pydantic v2 RootModel generation."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

import pytest

from datamodel_code_generator import Error
from datamodel_code_generator.model import DataModelFieldBase
from datamodel_code_generator.model.pydantic_v2.base_model import _CONFIG_ITEMS_TEMPLATE_DATA_KEY
from datamodel_code_generator.model.pydantic_v2.root_model import RootModel
from datamodel_code_generator.reference import Reference
from datamodel_code_generator.types import DataType

if TYPE_CHECKING:
    from pathlib import Path


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


def test_root_model_sequence_interface() -> None:
    """RootModel can render sequence interface helpers."""
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

    root_model.add_sequence_interface("str", "list[str]")

    assert root_model.render() == (
        "class TestRootModel(RootModel[list[str]], Sequence[str]):\n"
        "    root: list[str]\n\n"
        "    def __iter__(self) -> Iterator[str]:\n"
        "        return iter(self.root)\n\n"
        "    @overload\n"
        "    def __getitem__(self, index: SupportsIndex) -> str:\n"
        "        pass\n\n"
        "    @overload\n"
        "    def __getitem__(self, index: slice) -> list[str]:\n"
        "        pass\n\n"
        "    def __getitem__(self, index: SupportsIndex | slice) -> str | list[str]:\n"
        "        return self.root[index]\n\n"
        "    def __len__(self) -> int:\n"
        "        return len(self.root)"
    )
    assert any(import_.import_ == "Iterator" for import_ in root_model.imports)
    assert any(import_.import_ == "Sequence" for import_ in root_model.imports)
    assert any(import_.import_ == "overload" for import_ in root_model.imports)
    assert any(import_.import_ == "SupportsIndex" for import_ in root_model.imports)


def test_root_model_sequence_interface_with_decorator() -> None:
    """RootModel sequence interface keeps decorators before the class definition."""
    root_model = RootModel(
        decorators=["@some_decorator"],
        fields=[
            DataModelFieldBase(
                name="a",
                data_type=DataType(type="str", is_list=True, data_types=[DataType(type="str")]),
                required=True,
            )
        ],
        reference=Reference(name="TestRootModel", path="test_root_model"),
    )

    root_model.add_sequence_interface("str", "list[str]")

    rendered_lines = root_model.render().splitlines()
    assert rendered_lines[0] == "@some_decorator"
    assert rendered_lines[1] == "class TestRootModel(RootModel[List[str]], Sequence[str]):"


def test_root_model_sequence_interface_rejects_unsupported_custom_template(tmp_path: Path) -> None:
    """Unsupported custom RootModel templates fail when sequence interface helpers are requested."""
    template_path = tmp_path / "pydantic_v2" / "RootModel.jinja2"
    template_path.parent.mkdir()
    template_path.write_text(
        "class {{ class_name }}({{ base_class }}):\n    root: {{ fields[0].type_hint }}\n",
        encoding="utf-8",
    )
    root_model = RootModel(
        custom_template_dir=tmp_path,
        fields=[
            DataModelFieldBase(
                name="a",
                data_type=DataType(type="str", is_list=True, data_types=[DataType(type="str")]),
                required=True,
            )
        ],
        reference=Reference(name="TestRootModel", path="test_root_model"),
    )

    root_model.add_sequence_interface("str", "List[str]")

    with pytest.raises(Error, match="does not support --use-root-model-sequence-interface"):
        root_model.render()


def test_root_model_sequence_interface_accepts_supported_custom_template(tmp_path: Path) -> None:
    """Custom RootModel templates can opt in by rendering sequence_base_class and methods."""
    template_path = tmp_path / "pydantic_v2" / "RootModel.jinja2"
    template_path.parent.mkdir()
    template_path.write_text(
        "class {{ class_name }}({{ base_class }}{% if sequence_base_class is defined %}, "
        "{{ sequence_base_class }}{% endif %}):\n"
        "    root: {{ fields[0].type_hint }}\n"
        "{%- for method in methods %}\n\n"
        "    {{ method }}\n"
        "{%- endfor %}\n",
        encoding="utf-8",
    )
    root_model = RootModel(
        custom_template_dir=tmp_path,
        fields=[
            DataModelFieldBase(
                name="a",
                data_type=DataType(type="str", is_list=True, data_types=[DataType(type="str")]),
                required=True,
            )
        ],
        reference=Reference(name="TestRootModel", path="test_root_model"),
    )

    root_model.add_sequence_interface("str", "List[str]")
    rendered = root_model.render()

    assert "class TestRootModel(RootModel, Sequence[str]):" in rendered
    assert "def __iter__(self) -> Iterator[str]:" in rendered
    assert "def __getitem__(self, index: SupportsIndex) -> str:" in rendered
    assert "def __len__(self) -> int:" in rendered


def test_root_model_sequence_interface_add_any_import() -> None:
    """Sequence interface helpers import Any when the wrapped item type is Any."""
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

    root_model.add_sequence_interface("Any", "list[Any]")

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
