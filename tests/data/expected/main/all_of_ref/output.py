# @generated by datamodel-codegen:
#   filename:  test.json
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from pydantic import BaseModel, Field


class First(BaseModel):
    second: str = Field(..., description='Second', examples=['second'])


class Test(First):
    pass
