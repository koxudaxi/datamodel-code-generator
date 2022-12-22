from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Pet(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class Error(BaseModel):
    code: int
    message: str


class PetForm(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None


class UserGetResponse(BaseModel):
    timestamp: datetime
    name: str
    age: Optional[str] = None


class UserPostRequest(BaseModel):
    timestamp: datetime
    name: str
    age: Optional[str] = None


class UsersGetResponse(BaseModel):
    timestamp: datetime
    name: str
    age: Optional[str] = None


class UsersPostRequest(BaseModel):
    timestamp: datetime
    name: str
    age: Optional[str] = None
