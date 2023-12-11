# @generated by datamodel-codegen:
#   filename:  space_and_special_characters.json
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from pydantic import BaseModel, Field


class InitialParameters(BaseModel):
    V1: int
    V2: int


class Data(BaseModel):
    Length__m_: float = Field(..., alias='Length (m)')
    Symmetric_deviation____: float = Field(..., alias='Symmetric deviation (%)')
    Total_running_time__s_: int = Field(..., alias='Total running time (s)')
    Mass__kg_: float = Field(..., alias='Mass (kg)')
    Initial_parameters: InitialParameters = Field(..., alias='Initial parameters')
    class_: str = Field(..., alias='class')


class Values(BaseModel):
    field_1_Step: str = Field(..., alias='1 Step')
    field_2_Step: str = Field(..., alias='2 Step')


class Recursive1(BaseModel):
    value: float


class Sub(BaseModel):
    recursive: Recursive1


class Recursive(BaseModel):
    sub: Sub


class Model(BaseModel):
    Serial_Number: str = Field(..., alias='Serial Number')
    Timestamp: str
    Data: Data
    values: Values
    recursive: Recursive
