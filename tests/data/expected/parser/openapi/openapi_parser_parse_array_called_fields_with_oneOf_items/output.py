from __future__ import annotations

from typing import List, Optional, Union

from pydantic import BaseModel, Field


class FieldItem(BaseModel):
    a: Optional[str] = None


class FieldItem1(BaseModel):
    b: Optional[str] = Field(None, regex='^[a-zA-Z_]+$')


class BadSchema(BaseModel):
    fields: Optional[List[Union[FieldItem, FieldItem1]]] = None
