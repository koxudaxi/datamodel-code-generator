# @generated by datamodel-codegen:
#   filename:  modular.yaml
#   timestamp: 1985-10-26T08:21:00+00:00

from __future__ import annotations

from pydantic import BaseModel, Field


class FieldModel(BaseModel):
    __root__: str = Field(..., example='green')
