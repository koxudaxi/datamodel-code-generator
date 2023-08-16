from __future__ import annotations

from typing import Iterable, Optional, Tuple

from pydantic import BaseModel as _BaseModel

from .base_model import BaseModel, DataModelField
from .root_model import RootModel
from .types import DataTypeManager


def dump_resolve_reference_action(class_names: Iterable[str]) -> str:
    return '\n'.join(f'{class_name}.model_rebuild()' for class_name in class_names)


class ConfigDict(_BaseModel):
    extra: Optional[str] = None
    title: Optional[str] = None
    populate_by_name: Optional[bool] = None
    allow_extra_fields: Optional[bool] = None
    frozen: Optional[bool] = None
    arbitrary_types_allowed: Optional[bool] = None
    protected_namespaces: Optional[Tuple[str, ...]] = None


__all__ = [
    'BaseModel',
    'DataModelField',
    'RootModel',
    'dump_resolve_reference_action',
    'DataTypeManager',
]
