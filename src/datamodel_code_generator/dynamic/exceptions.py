"""Custom exceptions for dynamic model generation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

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


class CircularReferenceError(DynamicModelError):
    """Circular reference that cannot be resolved."""

    def __init__(self, cycle_path: list[str]) -> None:
        """Initialize with the cycle path."""
        self.cycle_path = cycle_path
        super().__init__(f"Unresolvable circular reference: {' -> '.join(cycle_path)}")


class ConstraintConversionError(DynamicModelError):
    """Failed to convert schema constraints to Pydantic Field."""

    def __init__(self, constraint_name: str, constraint_value: Any, reason: str) -> None:
        """Initialize with constraint details and reason."""
        self.constraint_name = constraint_name
        self.constraint_value = constraint_value
        self.reason = reason
        super().__init__(f"Cannot convert constraint '{constraint_name}={constraint_value}': {reason}")


class UnsupportedModelTypeError(DynamicModelError):
    """Model type not supported for dynamic generation."""

    def __init__(self, model_type: str) -> None:
        """Initialize with the unsupported model type."""
        self.model_type = model_type
        super().__init__(f"Dynamic generation not supported for model type: {model_type}")
