# generated by datamodel-codegen:
#   filename:  modular.yaml
#   timestamp: 1985-10-26T08:21:00+00:00

from __future__ import annotations

from typing import NotRequired, Optional, TypedDict

from . import foo, models
from .nested import foo as foo_1

OptionalModel = str


Id = str


class Error(TypedDict):
    code: int
    message: str


class Result(TypedDict):
    event: NotRequired[Optional[models.Event]]


class Source(TypedDict):
    country: NotRequired[Optional[str]]


class DifferentTea(TypedDict):
    foo: NotRequired[Optional[foo.Tea]]
    nested: NotRequired[Optional[foo_1.Tea]]
