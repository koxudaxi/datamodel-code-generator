# generated by datamodel-codegen:
#   filename:  api.yaml
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Pet:
    id: int
    name: str
    tag: Optional[str] = None


Pets = List[Pet]


@dataclass
class User:
    id: int
    name: str
    tag: Optional[str] = None


Users = List[User]


Id = str


Rules = List[str]


@dataclass
class Error:
    code: int
    message: str


@dataclass
class Api:
    apiKey: Optional[str] = None
    apiVersionNumber: Optional[str] = None
    apiUrl: Optional[str] = None
    apiDocumentationUrl: Optional[str] = None


Apis = List[Api]


@dataclass
class Event:
    name: Optional[str] = None


@dataclass
class Result:
    event: Optional[Event] = None
