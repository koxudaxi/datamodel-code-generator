# generated by datamodel-codegen:
#   filename:  use_default_with_const.json
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class UseDefaultWithConst(BaseModel):
    foo: Literal['foo'] = 'foo'
