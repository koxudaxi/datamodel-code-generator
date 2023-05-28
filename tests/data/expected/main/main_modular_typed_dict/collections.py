# generated by datamodel-codegen:
#   filename:  modular.yaml
#   timestamp: 1985-10-26T08:21:00+00:00

from __future__ import annotations

from enum import Enum
from typing import List, Optional, TypedDict

from . import models

Pets = List[models.Pet]


Users = List[models.User]


Rules = List[str]


class Stage(Enum):
    test = 'test'
    dev = 'dev'
    stg = 'stg'
    prod = 'prod'


class Api(TypedDict):
    apiKey: Optional[str]
    apiVersionNumber: Optional[str]
    apiUrl: Optional[str]
    apiDocumentationUrl: Optional[str]
    stage: Optional[Stage]


Apis = List[Api]
