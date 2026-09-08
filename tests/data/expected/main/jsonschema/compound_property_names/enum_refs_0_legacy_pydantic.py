# Compound property names

from __future__ import annotations

from enum import Enum

from pydantic import Field, RootModel


class A(Enum):
    a = 'a'


class B(Enum):
    b = 'b'


class Root(RootModel[dict[A | B, int]]):
    root: dict[A | B, int] = Field(..., title='Root')
