"""Dataclass models for --input-model tests."""

from dataclasses import dataclass


@dataclass
class User:
    """User dataclass with basic fields."""

    name: str
    age: int
