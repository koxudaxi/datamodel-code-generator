# @generated by datamodel-codegen:
#   filename:  bar.json
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from pydantic import BaseModel, Field


class Bar(BaseModel):
    pass


class LogLevels(BaseModel):
    __root__: str = Field(..., description='Supported logging levels')
