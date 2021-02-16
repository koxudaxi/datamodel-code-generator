from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, constr


class Pet(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class Car(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class OneOfItemItem(BaseModel):
    name: Optional[str] = None


class OneOfItem(BaseModel):
    __root__: Union[Pet, Car, OneOfItemItem, constr(max_length=5000)]


class ItemItem(BaseModel):
    name: Optional[str] = None


class OneOfobj(BaseModel):
    item: Optional[Union[Pet, Car, ItemItem, constr(max_length=5000)]] = None


class OneOfArrayItem(BaseModel):
    name: Optional[str] = None
    birthday: Optional[date] = None


class OneOfArray(BaseModel):
    __root__: List[Union[Pet, Car, OneOfArrayItem, constr(max_length=5000)]]


class Error(BaseModel):
    code: int
    message: str


class Config(BaseModel):
    setting: Optional[Dict[str, Union[str, List[str]]]] = None
