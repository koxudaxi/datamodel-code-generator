# @generated by datamodel-codegen:
#   filename:  api.yaml
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from typing import List, Optional

from pydantic import AnyUrl, BaseModel, Extra, Field


class Pet(BaseModel):
    class Config:
        extra = Extra.allow

    id: int
    name: str
    tag: Optional[str] = None


class Pets(BaseModel):
    class Config:
        extra = Extra.allow

    __root__: List[Pet]


class User(BaseModel):
    class Config:
        extra = Extra.allow

    id: int
    name: str
    tag: Optional[str] = None


class Users(BaseModel):
    class Config:
        extra = Extra.allow

    __root__: List[User]


class Id(BaseModel):
    class Config:
        extra = Extra.allow

    __root__: str


class Rules(BaseModel):
    class Config:
        extra = Extra.allow

    __root__: List[str]


class Error(BaseModel):
    class Config:
        extra = Extra.allow

    code: int
    message: str


class Api(BaseModel):
    class Config:
        extra = Extra.allow

    apiKey: Optional[str] = Field(
        None, description='To be used as a dataset parameter value'
    )
    apiVersionNumber: Optional[str] = Field(
        None, description='To be used as a version parameter value'
    )
    apiUrl: Optional[AnyUrl] = Field(
        None, description="The URL describing the dataset's fields"
    )
    apiDocumentationUrl: Optional[AnyUrl] = Field(
        None, description='A URL to the API console for each API'
    )


class Apis(BaseModel):
    class Config:
        extra = Extra.allow

    __root__: List[Api]


class Event(BaseModel):
    class Config:
        extra = Extra.allow

    name: Optional[str] = None


class Result(BaseModel):
    class Config:
        extra = Extra.allow

    event: Optional[Event] = None
