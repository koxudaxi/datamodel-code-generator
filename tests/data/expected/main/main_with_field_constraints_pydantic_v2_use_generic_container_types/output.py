# @generated by datamodel-codegen:
#   filename:  api_constrained.yaml
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from typing import Optional, Sequence, Union

from pydantic import AnyUrl, BaseModel, Field, RootModel


class Pet(BaseModel):
    id: int = Field(..., ge=0, le=9223372036854775807)
    name: str = Field(..., max_length=256)
    tag: Optional[str] = Field(None, max_length=64)


class Pets(RootModel[Sequence[Pet]]):
    root: Sequence[Pet] = Field(..., max_length=10, min_length=1)


class UID(RootModel[int]):
    root: int = Field(..., ge=0)


class Phone(RootModel[str]):
    root: str = Field(..., min_length=3)


class FaxItem(RootModel[str]):
    root: str = Field(..., min_length=3)


class User(BaseModel):
    id: int = Field(..., ge=0)
    name: str = Field(..., max_length=256)
    tag: Optional[str] = Field(None, max_length=64)
    uid: UID
    phones: Optional[Sequence[Phone]] = Field(None, max_length=10)
    fax: Optional[Sequence[FaxItem]] = None
    height: Optional[Union[int, float]] = Field(None, ge=1.0, le=300.0)
    weight: Optional[Union[float, int]] = Field(None, ge=1.0, le=1000.0)
    age: Optional[int] = Field(None, gt=0, le=200)
    rating: Optional[float] = Field(None, gt=0.0, le=5.0)


class Users(RootModel[Sequence[User]]):
    root: Sequence[User]


class Id(RootModel[str]):
    root: str


class Rules(RootModel[Sequence[str]]):
    root: Sequence[str]


class Error(BaseModel):
    code: int
    message: str


class Api(BaseModel):
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


class Apis(RootModel[Sequence[Api]]):
    root: Sequence[Api]


class Event(BaseModel):
    name: Optional[str] = None


class Result(BaseModel):
    event: Optional[Event] = None
