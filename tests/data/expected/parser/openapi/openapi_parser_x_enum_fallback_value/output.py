from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class EnumTypeWithFallback(Enum):
    a = 'a'
    b = 'b'
    unknown = 'unknown'

    @classmethod
    def _missing_(cls, value):
        return EnumTypeWithFallback.unknown


class EnumTypeWithFallbackExistingField(Enum):
    a = 'a'
    b = 'b'
    unknown = 'unknown'

    @classmethod
    def _missing_(cls, value):
        return EnumTypeWithFallbackExistingField.unknown


class EnumTypeWithFallbackAndDifferentDefault(Enum):
    a = 'a'
    b = 'b'
    unknown = 'unknown'

    @classmethod
    def _missing_(cls, value):
        return EnumTypeWithFallbackAndDifferentDefault.unknown


class EnumTypeWithFallbackAndSameDefault(Enum):
    a = 'a'
    b = 'b'
    unknown = 'unknown'

    @classmethod
    def _missing_(cls, value):
        return EnumTypeWithFallbackAndSameDefault.unknown


class TopLevelModel(BaseModel):
    enum_field: EnumTypeWithFallback
    enum_field_with_default: Optional[EnumTypeWithFallbackAndDifferentDefault] = 'a'
    enum_field_with_default_fallback: Optional[
        EnumTypeWithFallbackAndSameDefault
    ] = 'unknown'
