"""
Custom module docstring header.

This is a multi-line docstring used for testing.
"""


from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from . import foo as foo_1
from . import models
from .bar import FieldModel
from .collections import Api, Apis, Pets, Rules, Stage, Users
from .foo import Cocoa, Tea
from .models import Event, Pet, Species, User
from .nested import foo as foo_2

__all__ = [
    "Api",
    "Apis",
    "Cocoa",
    "DifferentTea",
    "Error",
    "Event",
    "FieldModel",
    "Id",
    "OptionalModel",
    "Pet",
    "Pets",
    "Result",
    "Rules",
    "Source",
    "Species",
    "Stage",
    "Tea",
    "User",
    "Users",
]


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
    foo: Optional[foo_1.Tea] = None
    nested: Optional[foo_2.Tea] = None
