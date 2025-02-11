from __future__ import annotations

from typing import Iterable, Optional, Tuple

from pydantic import BaseModel as _BaseModel

from .base_model import BaseModel, DataModelField, UnionMode
from .root_model import RootModel
from .types import DataTypeManager


def dump_resolve_reference_action(class_names: Iterable[str]) -> str:
    return "\n".join(f"{class_name}.model_rebuild()" for class_name in class_names)


class ConfigDict(_BaseModel):
    extra: Optional[str] = None  # noqa: UP045
    title: Optional[str] = None  # noqa: UP045
    populate_by_name: Optional[bool] = None  # noqa: UP045
    allow_extra_fields: Optional[bool] = None  # noqa: UP045
    from_attributes: Optional[bool] = None  # noqa: UP045
    frozen: Optional[bool] = None  # noqa: UP045
    arbitrary_types_allowed: Optional[bool] = None  # noqa: UP045
    protected_namespaces: Optional[Tuple[str, ...]] = None  # noqa: UP006, UP045
    regex_engine: Optional[str] = None  # noqa: UP045
    use_enum_values: Optional[bool] = None  # noqa: UP045


__all__ = [
    "BaseModel",
    "DataModelField",
    "DataTypeManager",
    "RootModel",
    "UnionMode",
    "dump_resolve_reference_action",
]
