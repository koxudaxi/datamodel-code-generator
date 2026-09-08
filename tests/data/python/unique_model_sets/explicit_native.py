"""Independent native models for explicitly declared frozen sets."""
from __future__ import annotations

from enum import Enum
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID
from typing import ClassVar, Literal, Optional

from pydantic import AwareDatetime, BaseModel, ConfigDict, NaiveDatetime


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


class DateItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    value: date


class DatetimeItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    value: AwareDatetime


class LocalDatetimeItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    value: datetime


class NaiveDatetimeItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    value: NaiveDatetime


class TimeItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    value: time


class DurationItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    value: timedelta


class UUIDItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    value: UUID


class DecimalItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    value: Decimal


class OptionalDateItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    value: Optional[date]


class NestedDateItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    value: DateItem


class UnhashableDate(date):
    __hash__ = None


class UnhashableUUID(UUID):
    __hash__ = None


MODELS.update({
    'opaque': DateItem, 'standard_datetime': DatetimeItem,
    'standard_plain_datetime': LocalDatetimeItem, 'standard_local_datetime': NaiveDatetimeItem, 'standard_naive_datetime': NaiveDatetimeItem,
    'standard_time': TimeItem, 'standard_duration': DurationItem, 'standard_uuid': UUIDItem,
    'standard_decimal': DecimalItem, 'standard_optional': OptionalDateItem,
    'standard_nested': NestedDateItem, 'standard_inherited': DateItem,
})
SUBCLASS_VALUES = {
    'opaque': UnhashableDate(2024, 1, 2),
    'standard_uuid': UnhashableUUID('550e8400-e29b-41d4-a716-446655440000'),
}


class FixedTupleItem(TupleItem):
    """Native frozen model for the transported tuple comparison."""

    value: tuple[int, str]


class NestedTupleItem(TupleItem):
    """Native frozen model for the transported tuple comparison."""

    value: tuple[tuple[int, str], frozenset[int]]


class OptionalTupleItem(TupleItem):
    """Native frozen model for the transported tuple comparison."""

    value: tuple[int | None, ...]


class EmptyTupleItem(TupleItem):
    """Native frozen model for the transported tuple comparison."""

    value: tuple[()]


class FrozenTupleItem(TupleItem):
    """Native frozen model for the transported tuple comparison."""

    value: tuple[frozenset[int]]


class ScalarTupleItem(TupleItem):
    """Native frozen model for the transported tuple comparison."""

    value: tuple[float, bool, bytes, None]


MODELS.update({
    "tuple_fixed": FixedTupleItem,
    "tuple_typing": FixedTupleItem,
    "tuple_builtin": FixedTupleItem,
    "tuple_nested": NestedTupleItem,
    "tuple_optional": OptionalTupleItem,
    "tuple_empty": EmptyTupleItem,
    "tuple_frozen_typing": FrozenTupleItem,
    "tuple_scalars": ScalarTupleItem,
    "tuple_packaged": TupleItem,
})

MODELS["tuple_collision"] = TupleItem
