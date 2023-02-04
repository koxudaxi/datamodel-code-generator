from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

class GetPetsParametersQuery(BaseModel):
    limit: Optional[int] = 0
    HomeAddress: Optional[str] = 'Unknown'
    kind: Optional[str] = 'dog'

class Pet(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class Error(BaseModel):
    code: int
    message: str
