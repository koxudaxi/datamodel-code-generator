# generated by datamodel-codegen:
#   filename:  direct.json
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class Model(BaseModel):
    __root__: Any


class TargetItem(BaseModel):
    first: str


class TargetItem1(BaseModel):
    second: str


class Target(BaseModel):
    third: str


class Target1(TargetItem, Target):
    pass


class Target2(TargetItem1, Target):
    pass
