from __future__ import annotations

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


class PetsGetParametersQuery(BaseModel):
    limit: Optional[int] = 0
    HomeAddress: Optional[str] = 'Unknown'
    kind: Optional[str] = 'dog'


class PetsGetResponse(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class PetsPostRequest(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
