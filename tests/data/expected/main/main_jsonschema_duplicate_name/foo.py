# generated by datamodel-codegen:
#   filename:  foo.json
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from pydantic import BaseModel, Field


class Foo(BaseModel):
    pass


class LogLevels(BaseModel):
    __root__: str = Field(..., description='Supported logging levels')
