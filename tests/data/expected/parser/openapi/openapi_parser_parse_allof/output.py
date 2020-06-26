from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, conint


class Pet(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class Car(BaseModel):
    number: str


class AllOfref(Pet, Car):
    pass


class AllOfobj(BaseModel):
    name: Optional[str] = None
    number: Optional[str] = None


class AllOfCombine(Pet):
    birthdate: Optional[date] = None
    size: Optional[conint(ge=1)] = None


class AnyOfCombine(Pet, Car):
    age: Optional[str] = None


class Item(Pet, Car):
    age: Optional[str] = None


class AnyOfCombineInObject(BaseModel):
    item: Optional[Item] = None


class AnyOfCombineInArrayItem(Pet, Car):
    age: Optional[str] = None


class AnyOfCombineInArray(BaseModel):
    __root__: List[AnyOfCombineInArrayItem]


class AnyOfCombineInRoot(Pet, Car):
    age: Optional[str] = None
    birthdate: Optional[datetime] = None


class Error(BaseModel):
    code: int
    message: str
