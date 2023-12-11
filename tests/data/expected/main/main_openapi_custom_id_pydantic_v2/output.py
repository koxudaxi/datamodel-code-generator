# @generated by datamodel-codegen:
#   filename:  custom_id.yaml
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, RootModel


class CustomId(RootModel[UUID]):
    root: UUID = Field(..., description='My custom ID')


class Model(BaseModel):
    custom_id: Optional[CustomId] = None
