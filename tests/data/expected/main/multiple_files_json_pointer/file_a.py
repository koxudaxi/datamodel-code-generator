# @generated by datamodel-codegen:
#   filename:  file_a.json
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from typing import Optional, Union

from pydantic import BaseModel, Extra, Field

from . import file_b


class PersonA(BaseModel):
    class Config:
        extra = Extra.forbid

    name: Optional[str] = Field(None, title='name')
    pet: Optional[Union[file_b.Cat, file_b.Dog]] = Field(None, title='pet')
