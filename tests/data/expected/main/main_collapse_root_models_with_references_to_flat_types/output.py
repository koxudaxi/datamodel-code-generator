# @generated by datamodel-codegen:
#   filename:  flat_type.jsonschema
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class FooModel(BaseModel):
    foo: Optional[str] = None
