from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from . import models


class OptionalModel(BaseModel):
    __root__: str


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
    foo: Optional[Tea] = None
    nested: Optional[Tea_1] = None


class Tea(BaseModel):
    flavour: Optional[str] = None
    id: Optional[Id] = None


class Cocoa(BaseModel):
    quality: Optional[int] = None


class Tea_1(BaseModel):
    flavour: Optional[str] = None
    id: Optional[Id] = None
    self: Optional[Tea_1] = None
    optional: Optional[List[OptionalModel]] = None


class TeaClone(BaseModel):
    flavour: Optional[str] = None
    id: Optional[Id] = None
    self: Optional[Tea_1] = None
    optional: Optional[List[OptionalModel]] = None


class ListModel(BaseModel):
    __root__: List[Tea_1]
