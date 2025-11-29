"""Pydantic v1 custom root type model.

Generates models with __root__ field for wrapping single types.
"""

from __future__ import annotations

from typing import ClassVar

from datamodel_code_generator.model.pydantic.base_model import BaseModel


class CustomRootType(BaseModel):
    """DataModel for Pydantic v1 custom root types (__root__ field)."""

    TEMPLATE_FILE_PATH: ClassVar[str] = "pydantic/BaseModel_root.jinja2"
    BASE_CLASS: ClassVar[str] = "pydantic.BaseModel"
