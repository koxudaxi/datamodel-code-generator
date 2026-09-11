from __future__ import annotations

from typing import Set

from pydantic import BaseModel, ConfigDict


class Item(BaseModel):
    model_config = ConfigDict(
        frozen=True,
    )
    value: int


class Container(BaseModel):
    model_config = ConfigDict(
        frozen=True,
    )
    items: Set[Item]
