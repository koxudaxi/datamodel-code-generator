"""Pydantic v1 dataclass model.

Generates pydantic.dataclasses.dataclass decorated classes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from datamodel_code_generator.model import DataModel
from datamodel_code_generator.model.pydantic.imports import IMPORT_DATACLASS

if TYPE_CHECKING:
    from datamodel_code_generator.imports import Import


class DataClass(DataModel):
    """DataModel for Pydantic v1 dataclasses."""

    TEMPLATE_FILE_PATH: ClassVar[str] = "pydantic/dataclass.jinja2"
    DEFAULT_IMPORTS: ClassVar[tuple[Import, ...]] = (IMPORT_DATACLASS,)
