# generated by datamodel-codegen:
#   filename:  max_items_enum.yaml
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class BarEnum(Enum):
    hello = 'hello'
    goodbye = 'goodbye'


class Foo(BaseModel):
    bar: Optional[List[BarEnum]] = Field(None, max_items=3)
