# generated by datamodel-codegen:
#   filename:  root_model_with_additional_properties.json
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from enum import Enum
from typing import Dict, Optional, Union

from pydantic import BaseModel, Extra, Field


class Result(BaseModel):
    class Config:
        extra = Extra.allow

    __root__: int


class NestedObjectResult(BaseModel):
    class Config:
        extra = Extra.allow

    status: int


class NestedEnumResult(Enum):
    red = 'red'
    green = 'green'


class OneOfResultItem(BaseModel):
    description: Optional[str] = None


class AnyOfResultItem(BaseModel):
    description: Optional[str] = None


class User(BaseModel):
    name: Optional[str] = None


class AllOfResult(User):
    description: Optional[str] = None


class Model(BaseModel):
    test_id: str = Field(..., description='test ID')
    test_ip: str = Field(..., description='test IP')
    result: Dict[str, Result]
    nested_object_result: Dict[str, NestedObjectResult]
    nested_enum_result: Dict[str, NestedEnumResult]
    all_of_result: Optional[Dict[str, AllOfResult]] = None
    one_of_result: Optional[Dict[str, Union[User, OneOfResultItem]]] = None
    any_of_result: Optional[Dict[str, Union[User, AnyOfResultItem]]] = None
