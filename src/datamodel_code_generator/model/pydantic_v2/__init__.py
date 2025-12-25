"""Pydantic v2 model generator.

Provides BaseModel, RootModel, and DataModelField for generating
Pydantic v2 compatible data models with ConfigDict support.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional  # noqa: UP035

from pydantic import BaseModel as _BaseModel

from datamodel_code_generator.enums import UnionMode

from .base_model import BaseModel, DataModelField
from .root_model import RootModel
from .root_model_type_alias import RootModelTypeAlias
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
    populate_by_name: Optional[bool] = None  # noqa: UP045  # deprecated in v2.11+
    validate_by_name: Optional[bool] = None  # noqa: UP045  # v2.11+
    validate_by_alias: Optional[bool] = None  # noqa: UP045  # v2.11+
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
    json_schema_extra: Optional[Dict[str, Any]] = None  # noqa: UP006, UP045

    def dict(self, **kwargs: Any) -> dict[str, Any]:  # type: ignore[override]
        """Version-compatible dict method for templates."""
        from datamodel_code_generator.util import is_pydantic_v2  # noqa: PLC0415

        if is_pydantic_v2():
            return self.model_dump(**kwargs)
        return super().dict(**kwargs)


__all__ = [
    "BaseModel",
    "DataModelField",
    "DataTypeManager",
    "RootModel",
    "RootModelTypeAlias",
    "UnionMode",
    "dump_resolve_reference_action",
]
