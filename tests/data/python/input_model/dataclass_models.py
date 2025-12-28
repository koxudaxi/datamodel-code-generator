"""Dataclass models for --input-model tests."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import FrozenSet, Set


@dataclass
class User:
    """User dataclass with basic fields."""

    name: str
    age: int


@dataclass
class DataclassWithPythonTypes:
    """Dataclass with types that need x-python-type preservation."""

    tags: Set[str]
    frozen_tags: FrozenSet[int]
    metadata: Mapping[str, int]
    items: Sequence[str]
