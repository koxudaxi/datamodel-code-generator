"""Tests for dataclass model field generation."""

from __future__ import annotations

import pytest

from datamodel_code_generator.model.dataclass import DataClass, DataModelField
from datamodel_code_generator.reference import Reference
from datamodel_code_generator.types import DataType


def test_data_model_field_process_const() -> None:
    """Test process_const method functionality."""
    field = DataModelField(name="test_field", data_type=DataType(type="str"), required=True, extras={"const": "v1"})

    field.process_const()

    assert field.const is True
    assert field.nullable is False
    assert field.data_type.literals == ["v1"]
    assert field.default == "v1"


def test_data_model_field_process_const_no_const() -> None:
    """Test process_const when no const is in extras."""
    field = DataModelField(name="test_field", data_type=DataType(type="str"), required=True, extras={})

    original_nullable = field.nullable
    original_default = field.default
    original_const = field.const

    field.process_const()

    assert field.const == original_const
    assert field.nullable == original_nullable
    assert field.default == original_default


@pytest.mark.parametrize(
    ("extras", "strip_default_none", "expected"),
    [
        pytest.param({"repr": False}, False, "field(repr=False, default=None)", id="metadata"),
        pytest.param({"kw_only": True}, False, "field(kw_only=True, default=None)", id="keyword-only"),
        pytest.param({"repr": False}, True, "field(repr=False)", id="stripped-metadata"),
        pytest.param({"init": False}, False, "field(init=False, default=None)", id="init-disabled"),
        pytest.param({"init": False}, True, "field(init=False, default=None)", id="stripped-init-disabled"),
    ],
)
def test_data_model_field_optional_none_preserves_field_semantics(
    extras: dict[str, bool],
    strip_default_none: bool,
    expected: str,
) -> None:
    """Preserve optional defaults whenever field metadata bypasses the template default."""
    field = DataModelField(
        name="value",
        data_type=DataType(type="str"),
        default=None,
        required=False,
        strip_default_none=strip_default_none,
        extras=extras,
    )

    assert str(field) == expected


def test_data_model_field_init_false_preserves_default_factory() -> None:
    """Do not add a competing None default when init-disabled fields use a factory."""
    field = DataModelField(
        name="value",
        data_type=DataType(type="list"),
        default=None,
        required=False,
        extras={"default_factory": "list", "init": False},
    )

    assert str(field) == "field(default_factory=list, init=False)"


def test_data_model_field_init_false_prefers_computed_nested_default_factory() -> None:
    """A computed nested factory must replace the otherwise necessary None default."""
    nested_reference = Reference(path="Nested", original_name="Nested", name="Nested")
    DataClass(reference=nested_reference, fields=[])
    field = DataModelField(
        name="value",
        data_type=DataType(reference=nested_reference),
        default=None,
        required=False,
        extras={"init": False},
        use_default_factory_for_optional_nested_models=True,
    )

    assert str(field) == "field(init=False, default_factory=Nested)"


@pytest.mark.parametrize(
    ("const", "default", "type_"),
    [
        (True, False, "bool"),
        (3, 0, "int"),
        ("fast", "", "str"),
    ],
)
def test_data_model_field_process_const_preserves_explicit_falsy_default(
    const: bool | int | str,
    default: bool | int | str,
    type_: str,
) -> None:
    """Do not treat explicit falsy schema defaults as missing defaults."""
    field = DataModelField(
        name="test_field",
        data_type=DataType(type=type_),
        default=default,
        has_default=True,
        extras={"const": const},
    )

    field.process_const()

    assert field.const is True
    assert field.nullable is False
    assert field.data_type.literals == [const]
    assert field.default == default
