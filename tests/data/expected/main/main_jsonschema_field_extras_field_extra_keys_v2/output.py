# @generated by datamodel-codegen:
#   filename:  extras.json
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class Extras(BaseModel):
    name: Optional[str] = Field(
        None,
        description='normal key',
        examples=['example'],
        invalid_key_1='abc',
        key2=456,
        repr=True,
    )
    age: Optional[int] = Field(None, example=12, examples=[13, 20])
