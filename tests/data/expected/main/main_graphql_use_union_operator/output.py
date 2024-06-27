# generated by datamodel-codegen:
#   filename:  use-union-operator.graphql
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from typing import List, TypeAlias

from pydantic import BaseModel, Field
from typing_extensions import Literal

Boolean: TypeAlias = bool
"""
The `Boolean` scalar type represents `true` or `false`.
"""


String: TypeAlias = str
"""
The `String` scalar type represents textual data, represented as UTF-8 character sequences. The String type is most often used by GraphQL to represent free-form human-readable text.
"""


class A(BaseModel):
    field: String
    listField: List[String]
    listListField: List[List[String]]
    listListOptionalField: List[List[String | None]]
    listOptionalField: List[String | None]
    listOptionalListField: List[List[String] | None]
    listOptionalListOptionalField: List[List[String | None] | None]
    optionalField: String | None = None
    optionalListListField: List[List[String]] | None = Field(default_factory=list)
    optionalListListOptionalField: List[List[String | None]] | None = Field(
        default_factory=list
    )
    optionalListOptionalField: List[String | None] | None = Field(default_factory=list)
    optionalListOptionalListField: List[List[String] | None] | None = Field(
        default_factory=list
    )
    optionalListOptionalListOptionalField: List[
        List[String | None] | None
    ] | None = Field(default_factory=list)
    typename__: Literal['A'] | None = Field('A', alias='__typename')
