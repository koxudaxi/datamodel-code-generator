"""
Custom module docstring header.

This is a multi-line docstring used for testing.
"""

from __future__ import annotations

from enum import Enum

from pydantic import AnyUrl, BaseModel, Field

from . import models


class Pets(BaseModel):
    __root__: list[models.Pet]


class Users(BaseModel):
    __root__: list[models.User]


class Rules(BaseModel):
    __root__: list[str]


class Stage(Enum):
    test = 'test'
    dev = 'dev'
    stg = 'stg'
    prod = 'prod'


class Api(BaseModel):
    apiKey: str | None = Field(
        None, description='To be used as a dataset parameter value'
    )
    apiVersionNumber: str | None = Field(
        None, description='To be used as a version parameter value'
    )
    apiUrl: AnyUrl | None = Field(
        None, description="The URL describing the dataset's fields"
    )
    apiDocumentationUrl: AnyUrl | None = Field(
        None, description='A URL to the API console for each API'
    )
    stage: Stage | None = None


class Apis(BaseModel):
    __root__: list[Api]
