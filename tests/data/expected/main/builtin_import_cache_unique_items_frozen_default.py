from __future__ import annotations

from typing import Optional, Set

from pydantic import BaseModel, ConfigDict, Field


class Value(BaseModel):
    model_config = ConfigDict(
        frozen=True,
    )
    a: int


class Item(BaseModel):
    model_config = ConfigDict(
        frozen=True,
    )
    values: Optional[Set[Value]] = Field([{'a': 1}], validate_default=True)


class Left(BaseModel):
    model_config = ConfigDict(
        frozen=True,
    )
    item: Optional[Item] = None


class Model(BaseModel):
    model_config = ConfigDict(
        frozen=True,
    )
    left: Optional[Left] = None
    right: Optional[Left] = None
