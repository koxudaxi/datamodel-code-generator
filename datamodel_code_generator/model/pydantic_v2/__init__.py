from __future__ import annotations

from typing import Optional

from pydantic import BaseModel as _BaseModel

from .base_model import BaseModel, DataModelField
from .root_model import RootModel
from .types import DataTypeManager


class Config(_BaseModel):
    extra: Optional[str] = None
    title: Optional[str] = None
    allow_population_by_field_name: Optional[bool] = None
    allow_extra_fields: Optional[bool] = None
    allow_mutation: Optional[bool] = None
    arbitrary_types_allowed: Optional[bool] = None


__all__ = ['BaseModel', 'DataModelField', 'RootModel', 'DataTypeManager']
