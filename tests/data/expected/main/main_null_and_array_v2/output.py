# @generated by datamodel-codegen:
#   filename:  null_and_array.json
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel


class MyObjItem(BaseModel):
    items: Optional[List[Any]] = None


class Model(BaseModel):
    my_obj: List[MyObjItem]
