# @generated by datamodel-codegen:
#   filename:  modular.yaml
#   timestamp: 1985-10-26T08:21:00+00:00

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import AnyUrl, BaseModel, Field

from . import models


class CustomPets(BaseModel):
    __root__: List[models.CustomPet]


class CustomUsers(BaseModel):
    __root__: List[models.CustomUser]


class CustomRules(BaseModel):
    __root__: List[str]


class CustomStage(Enum):
    test = 'test'
    dev = 'dev'
    stg = 'stg'
    prod = 'prod'


class CustomApi(BaseModel):
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
    stage: Optional[CustomStage] = None


class CustomApis(BaseModel):
    __root__: List[CustomApi]
