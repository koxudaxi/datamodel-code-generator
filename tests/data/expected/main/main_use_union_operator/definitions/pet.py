# @generated by datamodel-codegen:
#   filename:  definitions/pet.json
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from pydantic import BaseModel

from . import fur


class Pet(BaseModel):
    name: str | None = None
    age: int | None = None
    fur: fur.Fur | None = None
