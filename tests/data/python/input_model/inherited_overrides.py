"""Inherited field overrides and unchanged inheritance controls."""
from __future__ import annotations
from pydantic import BaseModel, Field

class DefaultParent(BaseModel):
    before: int = 10
    value: int = 1
    after: int = 30

class DefaultChild(DefaultParent):
    value: int = 2
    added: int = 40

class SameChild(DefaultParent):
    value: int = 1
    added: int = 40

class RequiredChild(DefaultParent):
    value: int

class TypeChild(DefaultParent):
    value: str

class RequiredParent(BaseModel):
    value: int

class OptionalChild(RequiredParent):
    value: int = 2

class StrictParent(BaseModel):
    value: int = Field(ge=5)

class RelaxedChild(StrictParent):
    value: int = Field(ge=0)

class LooseParent(BaseModel):
    value: int = Field(ge=0)

class TightenedChild(LooseParent):
    value: int = Field(ge=5)

class AliasParent(BaseModel):
    value: int = Field(1, alias='old')

class AliasChild(AliasParent):
    value: int = Field(2, alias='new')

class UniqueParent(BaseModel):
    value: set[int]

class RepeatedChild(UniqueParent):
    value: list[int]

class GrandChild(DefaultChild):
    value: int = 3

class InheritedGrandChild(DefaultChild):
    extra: int = 50

class AliasSameChild(AliasParent):
    extra: int = 3

class AliasRequiredChild(AliasParent):
    value: int = Field(alias='new')

class AliasGrandChild(AliasChild):
    value: int = Field(3, alias='newest')

class OtherParent(BaseModel):
    other: str = 'other'
    value: int = 9

class MultipleChild(DefaultParent, OtherParent):
    value: int = 4

class UniquePairParent(BaseModel):
    value: set[int]
    retained: set[int]

class RepeatedPairChild(UniquePairParent):
    value: list[int]

class RepeatedGrandChild(RepeatedChild):
    extra: int = 1

class UniqueChild(RepeatedChild):
    value: set[int]

class NonemptyParent(BaseModel):
    value: list[int] = Field(min_length=2)

class EmptyChild(NonemptyParent):
    value: list[int]

class DifferentConstraintsParent(BaseModel):
    value: int = Field(ge=1, le=3)

class DifferentConstraintsChild(DifferentConstraintsParent):
    value: int = Field(ge=5, le=10)

from pydantic import AliasChoices, AliasPath

class ChoicesParent(BaseModel):
    value: int = Field(1, validation_alias=AliasChoices(AliasPath('nested', 0), 'old'), serialization_alias='old')

class ChoicesChild(ChoicesParent):
    value: int = Field(2, validation_alias=AliasChoices(AliasPath('new'), 'fallback'), serialization_alias='new')

class PathParent(BaseModel):
    value: int = Field(1, validation_alias=AliasChoices(AliasPath('nested', 0)))

class PathChild(PathParent):
    value: int = Field(2, validation_alias=AliasChoices(AliasPath('nested', 0)))

class SharedAliasParent(BaseModel):
    values: frozenset[int] = Field(alias='shared')

class SharedAliasChild(SharedAliasParent):
    items: list[int] = Field(alias='shared')
