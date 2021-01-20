from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class Kind(Enum):
    dog = 'dog'
    cat = 'cat'


class Type(Enum):
    animal = 'animal'


class Pet(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None
    kind: Optional[Kind] = None
    type: Optional[Type] = None


class Pets(BaseModel):
    __root__: List[Pet]


class Kind1(Enum):
    snake = 'snake'
    rabbit = 'rabbit'


class Animal(BaseModel):
    kind: Optional[Kind1] = None


class Error(BaseModel):
    code: int
    message: str


class Type1(Enum):
    a = 'a'
    b = 'b'


class EnumObject(BaseModel):
    type: Optional[Type1] = None


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


class MultipleTypeEnum(Enum):
    red = 'red'
    amber = 'amber'
    green = 'green'
    NoneType_None = None
    int_42 = 42


class SingleEnum(Enum):
    pet = 'pet'
