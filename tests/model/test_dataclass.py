"""Tests for dataclass model field generation."""

from __future__ import annotations

import pytest

from datamodel_code_generator.model.dataclass import DataModelField
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
