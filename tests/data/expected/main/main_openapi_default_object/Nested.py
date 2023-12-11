# @generated by datamodel-codegen:
#   filename:  default_object.yaml
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from . import Foo as Foo_1


class Foo(BaseModel):
    __root__: str


class Bar(BaseModel):
    foo: Optional[Foo_1] = Field(
        default_factory=lambda: Foo_1.parse_obj({'text': 'abc', 'number': 123})
    )
    baz: Optional[List[Foo_1]] = Field(
        default_factory=lambda: [
            Foo_1.parse_obj(v)
            for v in [{'text': 'abc', 'number': 123}, {'text': 'efg', 'number': 456}]
        ]
    )
    nested_foo: Optional[Foo] = Field(
        default_factory=lambda: Foo.parse_obj('default foo')
    )
