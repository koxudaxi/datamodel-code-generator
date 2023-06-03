# generated by datamodel-codegen:
#   filename:  api.yaml
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from typing import List, Optional

from typing_extensions import NotRequired, TypedDict


class Pet(TypedDict):
    id: int
    name: str
    tag: NotRequired[Optional[str]]


Pets = List[Pet]


class User(TypedDict):
    id: int
    name: str
    tag: NotRequired[Optional[str]]


Users = List[User]


Id = str


Rules = List[str]


class Error(TypedDict):
    code: int
    message: str


class Api(TypedDict):
    apiKey: NotRequired[Optional[str]]
    apiVersionNumber: NotRequired[Optional[str]]
    apiUrl: NotRequired[Optional[str]]
    apiDocumentationUrl: NotRequired[Optional[str]]


Apis = List[Api]


class Event(TypedDict):
    name: NotRequired[Optional[str]]


class Result(TypedDict):
    event: NotRequired[Optional[Event]]
