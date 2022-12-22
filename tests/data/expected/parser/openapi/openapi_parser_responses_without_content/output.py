from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


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
