"""Native frozen set items with stable value equality and hashing."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Item(BaseModel):
    """Independently defined immutable item."""

    model_config = ConfigDict(frozen=True)
    value: int


class Container(BaseModel):
    """Native model validating a set of immutable items."""

    items: set[Item]
