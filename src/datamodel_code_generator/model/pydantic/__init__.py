"""Pydantic v1 model generator.

Provides BaseModel, CustomRootType, and DataModelField for generating
Pydantic v1 compatible data models.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel as _BaseModel

from .base_model import BaseModel, DataModelField
from .custom_root_type import CustomRootType
from .types import DataTypeManager

if TYPE_CHECKING:
    from collections.abc import Iterable


def dump_resolve_reference_action(class_names: Iterable[str]) -> str:
    """Generate update_forward_refs() calls for Pydantic v1 models."""
    return "\n".join(f"{class_name}.update_forward_refs()" for class_name in class_names)


class Config(_BaseModel):
    """Pydantic model config options."""

    extra: Optional[str] = None  # noqa: UP045
    title: Optional[str] = None  # noqa: UP045
    allow_population_by_field_name: Optional[bool] = None  # noqa: UP045
    allow_extra_fields: Optional[bool] = None  # noqa: UP045
    extra_fields: Optional[str] = None  # noqa: UP045
    allow_mutation: Optional[bool] = None  # noqa: UP045
    arbitrary_types_allowed: Optional[bool] = None  # noqa: UP045
    orm_mode: Optional[bool] = None  # noqa: UP045
    validate_assignment: Optional[bool] = None  # noqa: UP045

    def dict(self, **kwargs: Any) -> dict[str, Any]:  # type: ignore[override]
        """Version-compatible dict method for templates."""
        from datamodel_code_generator.util import model_dump  # noqa: PLC0415

        return model_dump(self, **kwargs)


__all__ = [
    "BaseModel",
    "CustomRootType",
    "DataModelField",
    "DataTypeManager",
    "dump_resolve_reference_action",
]
