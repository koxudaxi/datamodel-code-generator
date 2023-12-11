# @generated by datamodel-codegen:
#   filename:  special_field_name.json
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SpecialField(BaseModel):
    global_: Optional[str] = Field(None, alias='global')
    with_: Optional[str] = Field(None, alias='with')
    class_: Optional[int] = Field(None, alias='class')
    class_s: Optional[int] = Field(None, alias="class's")
    class_s_1: Optional[str] = Field(None, alias='class-s')
    field_: Optional[str] = Field(None, alias='#')
