from __future__ import annotations

from datetime import date
from typing import List, Optional, Union

from pydantic import BaseModel


class Pet(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class Car(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class AnyOfItemItem(BaseModel):
    name: Optional[str] = None


class AnyOfItem(BaseModel):
    __root__: Union[Pet, Car, AnyOfItemItem]


class ItemItem(BaseModel):
    name: Optional[str] = None


class AnyOfobj(BaseModel):
    item: Optional[Union[Pet, Car, ItemItem]] = None


class AnyOfArrayItem(BaseModel):
    name: Optional[str] = None
    birthday: Optional[date] = None


class AnyOfArray(BaseModel):
    __root__: List[Union[Pet, Car, AnyOfArrayItem]]


class Error(BaseModel):
    code: int
    message: str
