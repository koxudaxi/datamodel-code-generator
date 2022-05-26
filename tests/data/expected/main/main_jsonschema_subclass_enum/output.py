# generated by datamodel-codegen:
#   filename:  subclass_enum.json
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class IntEnum(int, Enum):
    integer_1 = 1
    integer_2 = 2
    integer_3 = 3


class FloatEnum(float, Enum):
    number_1_1 = 1.1
    number_2_1 = 2.1
    number_3_1 = 3.1


class StrEnum(str, Enum):
    field_1 = '1'
    field_2 = '2'
    field_3 = '3'


class NonTypedEnum(Enum):
    field_1 = '1'
    field_2 = '2'
    field_3 = '3'


class Model(BaseModel):
    IntEnum: Optional[IntEnum] = None
    FloatEnum: Optional[FloatEnum] = None
    StrEnum: Optional[StrEnum] = None
    NonTypedEnum: Optional[NonTypedEnum] = None
