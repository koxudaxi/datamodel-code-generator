# generated by datamodel-codegen:
#   filename:  modular.yaml
#   timestamp: 1985-10-26T08:21:00+00:00

from __future__ import annotations

from typing import Optional, TypedDict

from . import foo, models
from .nested import foo as foo_1

OptionalModel = str


Id = str


class Error(TypedDict):
    code: int
    message: str


class Result(TypedDict):
    event: Optional[models.Event]


class Source(TypedDict):
    country: Optional[str]


class DifferentTea(TypedDict):
    foo: Optional[foo.Tea]
    nested: Optional[foo_1.Tea]
