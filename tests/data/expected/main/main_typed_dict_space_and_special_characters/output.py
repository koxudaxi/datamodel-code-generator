# @generated by datamodel-codegen:
#   filename:  space_and_special_characters.json
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from typing import TypedDict


class InitialParameters(TypedDict):
    V1: int
    V2: int


Data = TypedDict(
    'Data',
    {
        'Length (m)': float,
        'Symmetric deviation (%)': float,
        'Total running time (s)': int,
        'Mass (kg)': float,
        'Initial parameters': InitialParameters,
        'class': str,
    },
)


Values = TypedDict(
    'Values',
    {
        '1 Step': str,
        '2 Step': str,
    },
)


class Recursive1(TypedDict):
    value: float


class Sub(TypedDict):
    recursive: Recursive1


class Recursive(TypedDict):
    sub: Sub


Model = TypedDict(
    'Model',
    {
        'Serial Number': str,
        'Timestamp': str,
        'Data': Data,
        'values': Values,
        'recursive': Recursive,
    },
)
