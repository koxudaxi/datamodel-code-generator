# @generated by datamodel-codegen:
#   filename:  array_in_additional_properties.json
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel


class MyJsonOfListOfString(BaseModel):
    __root__: Optional[Dict[str, List[str]]] = None
