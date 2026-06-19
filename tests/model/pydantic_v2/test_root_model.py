"""Tests for Pydantic v2 RootModel generation."""

from __future__ import annotations

from collections import defaultdict

import pytest

from datamodel_code_generator.model import DataModelFieldBase, pydantic_v2
from datamodel_code_generator.model.pydantic_v2.base_model import _CONFIG_ITEMS_TEMPLATE_DATA_KEY
from datamodel_code_generator.model.pydantic_v2.imports import IMPORT_CONFIG_DICT
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


def test_root_model_rebuilds_template_items_for_existing_config() -> None:
    """RootModel keeps template config data consistent for externally supplied config."""
    root_model = RootModel(
        fields=[
            DataModelFieldBase(
                name="a",
                data_type=DataType(type="str"),
                required=True,
            )
        ],
        reference=Reference(name="TestRootModel", path="test_root_model"),
        extra_template_data=defaultdict(
            dict,
            {"test_root_model": {"config": pydantic_v2.ConfigDict(regex_engine='"python-re"')}},
        ),
    )

    assert root_model.extra_template_data[_CONFIG_ITEMS_TEMPLATE_DATA_KEY] == [("regex_engine", '"python-re"')]
    assert 'regex_engine="python-re"' in root_model.render()


def test_root_model_drops_unrenderable_existing_config() -> None:
    """RootModel does not render config unless it can supply template items."""

    class UnrenderableConfig:
        regex_engine = '"python-re"'

    root_model = RootModel(
        fields=[
            DataModelFieldBase(
                name="a",
                data_type=DataType(type="str"),
                required=True,
            )
        ],
        reference=Reference(name="TestRootModel", path="test_root_model"),
        extra_template_data=defaultdict(
            dict,
            {"test_root_model": {"config": UnrenderableConfig()}},
        ),
    )

    assert "config" not in root_model.extra_template_data
    assert _CONFIG_ITEMS_TEMPLATE_DATA_KEY not in root_model.extra_template_data
    assert "model_config" not in root_model.render()


def test_root_model_syncs_config_added_after_init() -> None:
    """RootModel keeps config template data valid when shared data changes after init."""
    root_model = RootModel(
        fields=[
            DataModelFieldBase(
                name="a",
                data_type=DataType(type="str"),
                required=True,
            )
        ],
        reference=Reference(name="TestRootModel", path="test_root_model"),
    )

    root_model.extra_template_data["config"] = pydantic_v2.ConfigDict(regex_engine='"python-re"')

    assert IMPORT_CONFIG_DICT in root_model.imports
    assert root_model.extra_template_data[_CONFIG_ITEMS_TEMPLATE_DATA_KEY] == [("regex_engine", '"python-re"')]
    assert 'regex_engine="python-re"' in root_model.render()


def test_root_model_template_ignores_non_iterable_config_items() -> None:
    """RootModel template ignores non-iterable optional sequence values."""

    class _MissingType:
        pass

    root_model = RootModel(
        fields=[
            DataModelFieldBase(
                name="a",
                data_type=DataType(type="str"),
                required=True,
            )
        ],
        reference=Reference(name="TestRootModel", path="test_root_model"),
    )

    rendered = root_model.template.render(
        class_name=root_model.class_name,
        fields=root_model.rendered_fields,
        decorators=root_model.decorators,
        base_class=root_model.base_class,
        methods=root_model.methods,
        description=root_model.rendered_description,
        dataclass_arguments=root_model.dataclass_arguments,
        path=root_model.path,
        config=pydantic_v2.ConfigDict(extra="'forbid'"),
        config_items=_MissingType(),
        class_body_lines=_MissingType(),
    )

    assert "model_config" not in rendered
    assert rendered == "class TestRootModel(RootModel[str]):\n    root: str"
