"""Pydantic models for --input-model tests."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import FrozenSet, Optional, Set, Union

from pydantic import BaseModel


class User(BaseModel):
    """User model with basic fields."""

    name: str
    age: int


class Tag(BaseModel):
    """Nested model for testing x-python-type with nested models."""

    values: FrozenSet[str]


class ModelWithPythonTypes(BaseModel):
    """Model with types that need x-python-type preservation."""

    tags: Set[str]
    frozen_tags: FrozenSet[int]
    metadata: Mapping[str, int]
    items: Sequence[str]
    nested_mapping: Mapping[str, Set[int]]
    tag_obj: Tag
    nested_in_list: list[Set[int]]
    optional_set: Optional[Set[str]]
    nullable_frozenset: Union[None, FrozenSet[str]]
    optional_mapping: Mapping[str, str] | None


class RecursiveNode(BaseModel):
    """Recursive model for testing cycle detection."""

    value: Set[str]
    children: Optional[list[RecursiveNode]] = None
