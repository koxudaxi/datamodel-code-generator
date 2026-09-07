# Compound property names

from __future__ import annotations

from typing import Any

from pydantic import Field, RootModel


class Root1(RootModel[Any]):
    root: Any = Field(..., pattern='^a')


class Root2(RootModel[Any]):
    root: Any = Field(..., pattern='^b')


class Root(RootModel[dict[Any | Root1 | Root2, Any]]):
    root: dict[Any | Root1 | Root2, Any] = Field(..., title='Root')
