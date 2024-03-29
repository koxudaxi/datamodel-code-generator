# generated by datamodel-codegen:
#   filename:  nested_enum.json
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class State(Enum):
    field_1 = '1'
    field_2 = '2'


class NestedState1(Enum):
    field_1 = '1'
    field_2 = '2'


class NestedState2(Enum):
    field_1 = '1'
    field_2 = '2'


class Result1(BaseModel):
    state: NestedState1


class Result2(BaseModel):
    state: NestedState2
