# generated by datamodel-codegen:
#   filename:  body_and_parameters_remote_ref.yaml
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class Pet(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class Error(BaseModel):
    code: int
    message: str


class PetForm(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None


class PetsGetResponse(BaseModel):
    __root__: List[Pet]


class FoodFoodIdGetResponse(BaseModel):
    __root__: List[int]
