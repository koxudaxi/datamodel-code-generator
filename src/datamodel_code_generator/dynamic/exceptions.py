"""Custom exceptions for dynamic model generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datamodel_code_generator.types import DataType


class DynamicModelError(Exception):
    """Base exception for dynamic model generation."""


class TypeResolutionError(DynamicModelError):
    """Failed to resolve a type to a Python type object."""

    def __init__(self, type_info: DataType, model_name: str, field_name: str) -> None:
        """Initialize with type info and context."""
        self.type_info = type_info
        self.model_name = model_name
        self.field_name = field_name
        super().__init__(f"Cannot resolve type for field '{field_name}' in model '{model_name}': {type_info}")
