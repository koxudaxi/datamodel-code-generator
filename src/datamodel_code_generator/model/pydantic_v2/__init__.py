"""Pydantic v2 model generator.

Provides BaseModel, RootModel, and DataModelField for generating
Pydantic v2 compatible data models with ConfigDict support.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from datamodel_code_generator.enums import UnionMode

from ._config import ConfigDict as ConfigDict
from .base_model import BaseModel, DataModelField
from .root_model import RootModel
from .root_model_type_alias import RootModelTypeAlias
from .types import DataTypeManager

if TYPE_CHECKING:
    from collections.abc import Iterable


def dump_resolve_reference_action(class_names: Iterable[str]) -> str:
    """Generate model_rebuild() calls for Pydantic v2 models."""
    return "\n".join(f"{class_name}.model_rebuild()" for class_name in class_names)


__all__ = [
    "BaseModel",
    "DataModelField",
    "DataTypeManager",
    "RootModel",
    "RootModelTypeAlias",
    "UnionMode",
    "dump_resolve_reference_action",
]
