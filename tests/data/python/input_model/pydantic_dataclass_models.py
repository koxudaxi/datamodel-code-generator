"""Pydantic dataclass models for --input-model tests."""

from pydantic.dataclasses import dataclass


@dataclass
class User:
    """User pydantic dataclass with basic fields."""

    name: str
    age: int
