from __future__ import annotations

from typing import Iterable, Tuple

from pydantic import BaseModel as _BaseModel

from .base_model import BaseModel, DataModelField, UnionMode
from .root_model import RootModel
from .types import DataTypeManager


def dump_resolve_reference_action(class_names: Iterable[str]) -> str:
    return "\n".join(f"{class_name}.model_rebuild()" for class_name in class_names)


class ConfigDict(_BaseModel):
    extra: str | None = None
    title: str | None = None
    populate_by_name: bool | None = None
    allow_extra_fields: bool | None = None
    from_attributes: bool | None = None
    frozen: bool | None = None
    arbitrary_types_allowed: bool | None = None
    protected_namespaces: Tuple[str, ...] | None = None
    regex_engine: str | None = None
    use_enum_values: bool | None = None


__all__ = [
    "BaseModel",
    "DataModelField",
    "DataTypeManager",
    "RootModel",
    "UnionMode",
    "dump_resolve_reference_action",
]
