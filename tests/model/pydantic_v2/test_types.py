"""Tests for Pydantic v2 DataType helpers."""

from __future__ import annotations

import pytest

from datamodel_code_generator.model.pydantic_v2.imports import IMPORT_SERIALIZE_AS_ANY
from datamodel_code_generator.model.pydantic_v2.types import PydanticV2DataType


class TypeHintErrorDataType(PydanticV2DataType):
    """DataType that fails if type_hint is evaluated."""

    @property
    def type_hint(self) -> str:
        """Fail when type_hint is evaluated."""
        raise AssertionError


class SerializeAsAnyDataType(PydanticV2DataType):
    """DataType that renders a SerializeAsAny wrapper."""

    @property
    def type_hint(self) -> str:
        """Return a SerializeAsAny type hint."""
        return "SerializeAsAny[User]"


@pytest.mark.allow_direct_assert
def test_imports_skip_serialize_as_any_type_hint_when_disabled() -> None:
    """Do not render type_hint just to reject SerializeAsAny imports."""
    data_type = TypeHintErrorDataType(type="User", use_serialize_as_any=False)

    assert list(data_type.imports) == []


@pytest.mark.allow_direct_assert
def test_imports_include_serialize_as_any_when_enabled() -> None:
    """Keep SerializeAsAny import when the rendered type hint uses it."""
    data_type = SerializeAsAnyDataType(type="User", use_serialize_as_any=True)

    assert list(data_type.imports) == [IMPORT_SERIALIZE_AS_ANY]
