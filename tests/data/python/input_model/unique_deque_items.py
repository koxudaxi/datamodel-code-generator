"""Frozen model whose preserved standard-library container has no value hash."""

from __future__ import annotations

from collections import deque

from pydantic import BaseModel, ConfigDict, Field


class Item(BaseModel):
    """A frozen object with an unhashable field."""

    model_config = ConfigDict(frozen=True)
    value: deque[int] = Field(default_factory=deque)


class Container(BaseModel):
    """Request unique values using a source schema constraint."""

    items: list[Item] = Field(json_schema_extra={"uniqueItems": True})
