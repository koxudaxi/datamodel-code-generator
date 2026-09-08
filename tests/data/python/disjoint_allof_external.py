"""An independently maintained model used by explicit reference mappings."""

from __future__ import annotations

from pydantic import BaseModel


class Value(BaseModel):
    """The external reference target with observable instance identity."""

    value: str
