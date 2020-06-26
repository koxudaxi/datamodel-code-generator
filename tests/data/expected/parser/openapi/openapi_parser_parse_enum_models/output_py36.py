from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class Pet(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class Pets(BaseModel):
    __root__: List['Pet']


class Error(BaseModel):
    code: int
    message: str


class Type(Enum):
    a = 'a'
    b = 'b'


class EnumObject(BaseModel):
    type: Optional['Type'] = None


class EnumRoot(Enum):
    a = 'a'
    b = 'b'


class IntEnum(Enum):
    number_1 = 1
    number_2 = 2


class AliasEnum(Enum):
    a = 1
    b = 2
    c = 3
