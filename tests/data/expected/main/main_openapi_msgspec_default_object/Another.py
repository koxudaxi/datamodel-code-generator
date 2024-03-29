# generated by datamodel-codegen:
#   filename:  default_object.yaml
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from typing import List, Optional

from msgspec import Struct, convert, field

from . import Foo as Foo_1
from . import Nested

Foo = str


class Bar(Struct):
    original_foo: Optional[Foo_1] = field(
        default_factory=lambda: convert({'text': 'abc', 'number': 123}, type=Foo_1)
    )
    nested_foo: Optional[List[Nested.Foo]] = field(
        default_factory=lambda: convert(['abc', 'efg'], type=list[Nested.Foo])
    )
