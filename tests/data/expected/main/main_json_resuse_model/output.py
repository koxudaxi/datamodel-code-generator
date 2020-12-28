# generated by datamodel-codegen:
#   filename:  duplicate_models.json
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from pydantic import BaseModel, Field


class ArmRight(BaseModel):
    Joint_1: int = Field(..., alias='Joint 1')
    Joint_2: int = Field(..., alias='Joint 2')
    Joint_3: int = Field(..., alias='Joint 3')


class ArmLeft(BaseModel):
    Joint_1: int = Field(..., alias='Joint 1')
    Joint_2: int = Field(..., alias='Joint 2')
    Joint_3: int = Field(..., alias='Joint 3')


class Head(BaseModel):
    Joint_1: int = Field(..., alias='Joint 1')


class Model(BaseModel):
    Arm_Right: ArmRight = Field(..., alias='Arm Right')
    Arm_Left: ArmRight = Field(..., alias='Arm Left')
    Head: Head
