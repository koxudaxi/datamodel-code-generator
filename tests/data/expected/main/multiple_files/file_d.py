# @generated by datamodel-codegen:
#   filename:  file_d.json
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from . import file_a


class ModelD(BaseModel):
    firstName: Optional[str] = None
    modelA: Optional[file_a.ModelA] = None
