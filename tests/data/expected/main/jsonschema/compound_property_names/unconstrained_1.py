# Compound property names

from __future__ import annotations

from typing import Any

from pydantic import Field, RootModel


class Root1(RootModel[Any]):
    root: Any = Field(..., pattern='^a')


class Root(RootModel[dict[Any | Root1, int]]):
    root: dict[Any | Root1, int] = Field(..., title='Root')
