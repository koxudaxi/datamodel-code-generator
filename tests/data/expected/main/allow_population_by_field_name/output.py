# generated by datamodel-codegen:
#   filename:  api.yaml
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from typing import List, Optional

from pydantic import AnyUrl, BaseModel, Field


class Pet(BaseModel):
    class Config:
        allow_population_by_field_name = True

    id: int
    name: str
    tag: Optional[str] = None


class Pets(BaseModel):
    class Config:
        allow_population_by_field_name = True

    __root__: List[Pet]


class User(BaseModel):
    class Config:
        allow_population_by_field_name = True

    id: int
    name: str
    tag: Optional[str] = None


class Users(BaseModel):
    __root__: List[User]


class Id(BaseModel):
    __root__: str


class Rules(BaseModel):
    __root__: List[str]


class Error(BaseModel):
    class Config:
        allow_population_by_field_name = True

    code: int
    message: str


class Api(BaseModel):
    class Config:
        allow_population_by_field_name = True

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
    __root__: List[Api]


class Event(BaseModel):
    class Config:
        allow_population_by_field_name = True

    name: Optional[str] = None


class Result(BaseModel):
    class Config:
        allow_population_by_field_name = True

    event: Optional[Event] = None
