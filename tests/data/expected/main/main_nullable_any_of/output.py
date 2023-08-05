# generated by datamodel-codegen:
#   filename:  nullable_any_of.json
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Extra, Field


class ConfigItem(BaseModel):
    __root__: str = Field(..., description='d2', min_length=1, title='t2')


class In(BaseModel):
    class Config:
        extra = Extra.forbid

    input_dataset_path: Optional[str] = Field(
        None, description='d1', min_length=1, title='Path to the input dataset'
    )
    config: Optional[ConfigItem] = None


class ValidatingSchemaId1(BaseModel):
    class Config:
        extra = Extra.forbid

    in_: Optional[In] = Field(None, alias='in')
    n1: Optional[int] = None