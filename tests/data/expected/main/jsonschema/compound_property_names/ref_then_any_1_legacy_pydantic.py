# Compound property names

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field, RootModel


class Name(Enum):
    a = 'a'
    b = 'b'


class Root(RootModel[dict[Name | Any, Any]]):
    root: dict[Name | Any, Any] = Field(..., title='Root')
