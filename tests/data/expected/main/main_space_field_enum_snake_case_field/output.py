# generated by datamodel-codegen:
#   filename:  space_field_enum.json
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SpaceIF(Enum):
    space_field = 'Space Field'


class Model(BaseModel):
    space_if: Optional[SpaceIF] = Field(None, alias='SpaceIF')
