from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from . import foo, models
from .nested import foo as foo_1


class Id(BaseModel):
    __root__: str


class Error(BaseModel):
    code: int
    message: str


class Result(BaseModel):
    event: Optional[models.Event] = None


class Source(BaseModel):
    country: Optional[str] = None


class DifferentTea(BaseModel):
    foo: Optional[foo.Tea] = None
    nested: Optional[foo_1.Tea] = None
