"""Pydantic models for --input-model tests."""

from pydantic import BaseModel


class User(BaseModel):
    """User model with basic fields."""

    name: str
    age: int
