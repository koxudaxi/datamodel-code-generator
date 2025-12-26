"""TypedDict models for --input-model tests."""

from typing import TypedDict


class User(TypedDict):
    """User TypedDict with basic fields."""

    name: str
    age: int
