# generated by datamodel-codegen:
#   filename:  special_field_name_with_inheritance_model.json
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from typing import Optional, TypedDict


class NestedBase(TypedDict):
    age: Optional[str]


class Base(NestedBase):
    name: Optional[str]


SpecialField = TypedDict(
    'SpecialField',
    {
        'age': Optional[str],
        'name': Optional[str],
        'global': Optional[str],
        'with': Optional[str],
        'class': Optional[int],
        'class\'s': Optional[int],
        'class-s': Optional[str],
        '#': Optional[str],
    },
)
