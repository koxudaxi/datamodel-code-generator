"""Internal types for model module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(repr=False)
class WrappedDefault:
    """Represents a default value wrapped with its type constructor."""

    value: Any
    type_name: str

    def __repr__(self) -> str:
        """Return type constructor representation, e.g., 'CountType(10)'."""
        return f"{self.type_name}({self.value!r})"
