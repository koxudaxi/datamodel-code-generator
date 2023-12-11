# @generated by datamodel-codegen:
#   filename:  special_yaml_keywords.yaml
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from pydantic import BaseModel, Field


class None1(BaseModel):
    pass


class False1(BaseModel):
    pass


class True1(BaseModel):
    pass


class On(BaseModel):
    pass


class NestedKeywords(BaseModel):
    None_: None1 = Field(..., alias='None')
    false: False1
    True_: True1 = Field(..., alias='True')
    on: On
