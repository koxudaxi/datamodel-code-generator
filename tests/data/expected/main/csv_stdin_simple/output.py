# @generated by datamodel-codegen:
#   filename:  <stdin>
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from pydantic import BaseModel, Field


class Model(BaseModel):
    id: str
    name: str
    tel: str
    zip_code: str = Field(..., alias='zip code')
