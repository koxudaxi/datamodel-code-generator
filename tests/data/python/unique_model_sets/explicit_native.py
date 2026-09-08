"""Independent native models for explicitly declared frozen sets."""
from __future__ import annotations

from enum import Enum
from typing import ClassVar, Literal, Optional

from pydantic import BaseModel, ConfigDict


class IdentityBase(BaseModel):
    __hash__ = object.__hash__


class Integer(BaseModel):
    model_config = ConfigDict(frozen=True)
    value: int


class Inherited(Integer):
    label: Optional[str] = 'x'


class Nested(BaseModel):
    model_config = ConfigDict(frozen=True)
    value: Integer


class Recursive(BaseModel):
    model_config = ConfigDict(frozen=True)
    value: int
    child: Optional[Recursive] = None


class TupleItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    value: tuple[int, ...]


class LiteralItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    value: Literal['a', 'b']


class Value(Enum):
    a = 'a'
    b = 'b'


class EnumItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    value: Value


class Classvar(Integer):
    shared: ClassVar[list[int]] = []


class MutableBase(BaseModel):
    value: int


class FrozenChild(MutableBase):
    model_config = ConfigDict(frozen=True)
    label: Optional[str] = 'x'


MODELS = {
    'inherited_mutable_base': FrozenChild,
    'integer': Integer, 'nested': Nested, 'inherited': Inherited,
    'recursive': Recursive, 'tuple': TupleItem, 'literal': LiteralItem,
    'enum': EnumItem, 'classvar': Classvar, 'packaged': Integer,
}
