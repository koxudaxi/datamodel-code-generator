(
    r"""Parenthesized module docstring."""
    """ Concatenated without allocating at runtime."""
)
from __future__ import annotations

type HeaderAlias[T] = list[T]

from pydantic import BaseModel


class Model(BaseModel):
    s: str