from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class Pet(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class PetUpdate(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    tag: Optional[str] = None


class PetNewPostRequest(BaseModel):
    __root__: Pet


class PetUpdatedPostRequest(BaseModel):
    __root__: PetUpdate