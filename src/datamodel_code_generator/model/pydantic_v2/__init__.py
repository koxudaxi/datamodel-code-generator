"""Pydantic v2 model generator.

Provides BaseModel, RootModel, and DataModelField for generating
Pydantic v2 compatible data models with ConfigDict support.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel as _BaseModel

from .base_model import BaseModel, DataModelField, UnionMode
from .root_model import RootModel
from .types import DataTypeManager

if TYPE_CHECKING:
    from collections.abc import Iterable


def dump_resolve_reference_action(class_names: Iterable[str]) -> str:
    """Generate model_rebuild() calls for Pydantic v2 models."""
    return "\n".join(f"{class_name}.model_rebuild()" for class_name in class_names)


class ConfigDict(_BaseModel):
    """Pydantic v2 model_config options."""

    extra: Optional[str] = None  # noqa: UP045
    title: Optional[str] = None  # noqa: UP045
    populate_by_name: Optional[bool] = None  # noqa: UP045
    allow_extra_fields: Optional[bool] = None  # noqa: UP045
    extra_fields: Optional[str] = None  # noqa: UP045
    from_attributes: Optional[bool] = None  # noqa: UP045
    frozen: Optional[bool] = None  # noqa: UP045
    arbitrary_types_allowed: Optional[bool] = None  # noqa: UP045
    protected_namespaces: Optional[tuple[str, ...]] = None  # noqa: UP045
    regex_engine: Optional[str] = None  # noqa: UP045
    use_enum_values: Optional[bool] = None  # noqa: UP045
    coerce_numbers_to_str: Optional[bool] = None  # noqa: UP045
    use_attribute_docstrings: Optional[bool] = None  # noqa: UP045


__all__ = [
    "BaseModel",
    "DataModelField",
    "DataTypeManager",
    "RootModel",
    "UnionMode",
    "dump_resolve_reference_action",
]
