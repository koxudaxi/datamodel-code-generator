"""Tests for Pydantic v2 DataType helpers."""

from __future__ import annotations

import pytest

from datamodel_code_generator.model.pydantic_v2 import BaseModel, DataModelField
from datamodel_code_generator.model.pydantic_v2.imports import IMPORT_SERIALIZE_AS_ANY
from datamodel_code_generator.model.pydantic_v2.types import DataTypeManager, PydanticV2DataType
from datamodel_code_generator.reference import Reference
from datamodel_code_generator.types import DataType


class TypeHintErrorDataType(PydanticV2DataType):
    """DataType that fails if type_hint is evaluated."""

    @property
    def type_hint(self) -> str:
        """Fail when type_hint is evaluated."""
        raise AssertionError


@pytest.mark.allow_direct_assert
def test_imports_skip_serialize_as_any_type_hint_when_disabled() -> None:
    """Do not render type_hint just to reject SerializeAsAny imports."""
    data_type = TypeHintErrorDataType(type="User", use_serialize_as_any=False)

    assert list(data_type.imports) == []


@pytest.mark.allow_direct_assert
def test_imports_include_serialize_as_any_when_enabled() -> None:
    """Keep SerializeAsAny import when the reference structure needs it."""
    reference = Reference(path="#/$defs/User", name="User")
    model = BaseModel(
        fields=[DataModelField(name="name", data_type=DataType(type="str"), required=True)],
        reference=reference,
    )
    reference.children.append(model)
    data_type = PydanticV2DataType(reference=reference, use_serialize_as_any=True)

    assert list(data_type.imports) == [IMPORT_SERIALIZE_AS_ANY]


@pytest.mark.allow_direct_assert
def test_imports_skip_serialize_as_any_without_reference() -> None:
    """Do not render type_hint or assert when no reference can be wrapped."""
    data_type = TypeHintErrorDataType(type="User", use_serialize_as_any=True)

    assert list(data_type.imports) == []


@pytest.mark.allow_direct_assert
def test_transform_kwargs_iterates_filter_when_kwargs_are_larger() -> None:
    """Keep schema-to-model kwarg mapping stable when filtered keys are fewer."""
    data_type_manager = DataTypeManager()

    assert data_type_manager.transform_kwargs(
        {
            "minimum": 1,
            "maximum": 9,
            "multipleOf": 2,
            "pattern": "ignored",
            "extra": "ignored",
        },
        ("minimum", "maximum", "multipleOf"),
    ) == {"ge": 1, "le": 9, "multiple_of": 2}
