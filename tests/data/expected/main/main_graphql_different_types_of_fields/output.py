# generated by datamodel-codegen:
#   filename:  different-types-of-fields.graphql
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from typing import List, Literal, Optional, TypeAlias

from pydantic import BaseModel, Field

# The `Boolean` scalar type represents `true` or `false`.
Boolean: TypeAlias = bool


# The `String` scalar type represents textual data, represented as UTF-8 character sequences. The String type is most often used by GraphQL to represent free-form human-readable text.
String: TypeAlias = str


class A(BaseModel):
    field: String
    listField: List[String]
    listListField: List[List[String]]
    listListOptionalField: List[List[Optional[String]]]
    listOptionalField: List[Optional[String]]
    listOptionalListField: List[Optional[List[String]]]
    listOptionalListOptionalField: List[Optional[List[Optional[String]]]]
    optionalField: Optional[String] = None
    optionalListListField: Optional[List[List[String]]] = Field(default_factory=list)
    optionalListListOptionalField: Optional[List[List[Optional[String]]]] = Field(
        default_factory=list
    )
    optionalListOptionalField: Optional[List[Optional[String]]] = Field(
        default_factory=list
    )
    optionalListOptionalListField: Optional[List[Optional[List[String]]]] = Field(
        default_factory=list
    )
    optionalListOptionalListOptionalField: Optional[
        List[Optional[List[Optional[String]]]]
    ] = Field(default_factory=list)
    typename__: Optional[Literal['A']] = Field('A', alias='__typename')
