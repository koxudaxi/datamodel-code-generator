from __future__ import annotations

from typing import Optional

from pydantic import BaseModel as _BaseModel

from .base_model import BaseModel, DataModelField
from .root_model import RootModel
from .types import DataTypeManager


class ConfigDict(_BaseModel):
    extra: Optional[str] = None
    title: Optional[str] = None
    populate_by_name: Optional[bool] = None
    allow_extra_fields: Optional[bool] = None
    frozen: Optional[bool] = None
    arbitrary_types_allowed: Optional[bool] = None


__all__ = ['BaseModel', 'DataModelField', 'RootModel', 'DataTypeManager']
