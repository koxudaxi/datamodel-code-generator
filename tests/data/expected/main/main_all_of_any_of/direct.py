# @generated by datamodel-codegen:
#   filename:  direct.json
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from typing import Any, Union

from pydantic import BaseModel


class Model(BaseModel):
    __root__: Any


class Target1(BaseModel):
    first: str


class Target2(BaseModel):
    second: str


class Target3(BaseModel):
    third: str


class Target4(Target1, Target3):
    pass


class Target5(Target2, Target3):
    pass


class Target(BaseModel):
    __root__: Union[Target4, Target5]
