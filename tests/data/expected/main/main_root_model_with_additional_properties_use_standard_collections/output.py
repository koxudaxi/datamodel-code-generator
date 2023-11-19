# generated by datamodel-codegen:
#   filename:  root_model_with_additional_properties.json
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel, Field


class NestedObjectResult(BaseModel):
    status: int


class NestedEnumResult(Enum):
    red = 'red'
    green = 'green'


class OneOfResult(BaseModel):
    description: Optional[str] = None


class AnyOfResult(BaseModel):
    description: Optional[str] = None


class User(BaseModel):
    name: Optional[str] = None


class AllOfResult(User):
    description: Optional[str] = None


class Model(BaseModel):
    test_id: str = Field(..., description='test ID')
    test_ip: str = Field(..., description='test IP')
    result: dict[str, int]
    nested_object_result: dict[str, NestedObjectResult]
    nested_enum_result: dict[str, NestedEnumResult]
    all_of_result: Optional[dict[str, AllOfResult]] = None
    one_of_result: Optional[dict[str, Union[User, OneOfResult]]] = None
    any_of_result: Optional[dict[str, Union[User, AnyOfResult]]] = None
    all_of_with_unknown_object: Optional[dict[str, User]] = None
    objectRef: Optional[dict[str, User]] = None
    deepNestedObjectRef: Optional[dict[str, dict[str, dict[str, User]]]] = None
