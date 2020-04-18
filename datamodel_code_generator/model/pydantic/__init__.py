from typing import List, Optional

from pydantic import BaseModel as _BaseModel

from .base_model import BaseModel, DataModelField
from .custom_root_type import CustomRootType
from .dataclass import DataClass


def dump_resolve_reference_action(class_names: List[str]) -> str:
    return '\n'.join(
        f'{class_name}.update_forward_refs()' for class_name in class_names
    )


class Config(_BaseModel):
    extra: Optional[str] = None
    title: Optional[str] = None


__all__ = [
    'BaseModel',
    'DataModelField',
    'CustomRootType',
    'DataClass',
    'dump_resolve_reference_action',
]
