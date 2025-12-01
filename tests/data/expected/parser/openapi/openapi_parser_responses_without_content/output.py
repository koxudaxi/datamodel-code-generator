from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class FoodFoodIdGetResponse(BaseModel):
    __root__: List[int]


class UserGetResponse(BaseModel):
    timestamp: datetime
    name: str
    age: Optional[str] = None


class UserPostRequest(BaseModel):
    timestamp: datetime
    name: str
    age: Optional[str] = None


class UsersGetResponseItem(BaseModel):
    timestamp: datetime
    name: str
    age: Optional[str] = None


class UsersGetResponse(BaseModel):
    __root__: List[UsersGetResponseItem]


class UsersPostRequestItem(BaseModel):
    timestamp: datetime
    name: str
    age: Optional[str] = None


class UsersPostRequest(BaseModel):
    __root__: List[UsersPostRequestItem]


class Error(BaseModel):
    code: int
    message: str


class Pet(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class PetForm(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None


class PetsGetResponse(BaseModel):
    __root__: List[Pet]
