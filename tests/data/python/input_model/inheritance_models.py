"""Pydantic models with inheritance for --input-model tests."""

from __future__ import annotations

from pydantic import BaseModel


class GrandParent(BaseModel):
    """Base model at the top of the hierarchy."""

    grand_field: str


class Parent(GrandParent):
    """Parent model inheriting from GrandParent."""

    parent_field: int


class ChildA(Parent):
    """Child model A - one branch of inheritance."""

    child_a_field: float


class ChildB(Parent):
    """Child model B - another branch of inheritance."""

    child_b_field: bool


class Intermediate(Parent):
    """Intermediate model between Parent and GrandChild."""

    intermediate_field: str


class GrandChild(Intermediate):
    """Grand child model with multi-level inheritance."""

    grandchild_field: list[str]


class NoInheritance(BaseModel):
    """Model with no inheritance (direct BaseModel subclass)."""

    simple_field: str


class EmptyChild(Parent):
    """Child model that adds no new properties - inherits all from Parent."""

    pass


class OptionalOnlyChild(Parent):
    """Child model that adds only optional fields (no new required)."""

    optional_field: str | None = None
