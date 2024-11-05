# generated by datamodel-codegen:
#   filename:  duration.json
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from datetime import timedelta
from typing import Any, Optional

from pydantic import BaseModel, Field, RootModel


class Model(RootModel[Any]):
    root: Any


class Test(BaseModel):
    s_duration: Optional[timedelta] = Field(None, examples=['PT2H33M3S'])