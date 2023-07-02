from __future__ import annotations

from typing import ClassVar

from datamodel_code_generator.model.pydantic import DataTypeManager


class DataTypeManager(DataTypeManager):
    PATTERN_KEY: ClassVar[str] = 'pattern'
