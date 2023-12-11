# @generated by datamodel-codegen:
#   filename:  combined_array.json
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from enum import Enum
from typing import List, Optional, Union

from pydantic import BaseModel, Field


class Pet1(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None


class Pet(BaseModel):
    __root__: Union[List[Pet1], Pet1] = Field(..., title='Pet')


class CombinedEnum1(Enum):
    green = 'green'
    red = 'red'


class CombinedEnumField(Enum):
    green = 'green'
    red = 'red'


class CombinedObjectField1(BaseModel):
    color: Optional[str] = None


class CombinedSelf1(BaseModel):
    color: Optional[str] = None


class CombinedSelf(BaseModel):
    __root__: Union[List[CombinedSelf1], CombinedSelf1]


class CombinedSelfEnum1(BaseModel):
    color: Optional[str] = None


class CombinedSelfEnum2(Enum):
    green = 'green'
    red = 'red'


class CombinedSelfEnum(BaseModel):
    __root__: Union[
        List[Union[CombinedSelfEnum1, CombinedSelfEnum2]],
        CombinedSelfEnum1,
        CombinedSelfEnum2,
    ]


class CombinedSelfAllOf2(Enum):
    green = 'green'
    red = 'red'


class Kind(BaseModel):
    description: Optional[str] = None


class Id(BaseModel):
    id: Optional[int] = None


class CustomRootModel(BaseModel):
    __root__: str


class CombinedEnum(BaseModel):
    __root__: Union[List[Kind], CombinedEnum1]


class CombinedAllOf1(Kind, Id):
    pass


class CombinedAllOf(BaseModel):
    __root__: Union[List[Kind], CombinedAllOf1]


class CombinedAllOfField(Kind, Id):
    pass


class CombinedAllOfObjectField(Kind, Id):
    color: Optional[str] = None


class CombinedObjectField(BaseModel):
    CombinedEnumField: Optional[Union[List[Kind], CombinedEnumField]] = None
    CombinedAllOfField: Optional[Union[List[Kind], CombinedAllOfField]] = None
    CombinedObjectField: Optional[Union[List[Kind], CombinedObjectField1]] = None
    CombinedAllOfObjectField: Optional[
        Union[List[Kind], CombinedAllOfObjectField]
    ] = None


class CombinedSelfAllOf1(Kind, Id):
    color: Optional[str] = None


class CombinedSelfAllOf(BaseModel):
    __root__: Union[
        List[Union[CombinedSelfAllOf1, CombinedSelfAllOf2]],
        CombinedSelfAllOf1,
        CombinedSelfAllOf2,
    ]
