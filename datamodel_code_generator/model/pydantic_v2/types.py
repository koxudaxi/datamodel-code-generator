from __future__ import annotations

from typing import ClassVar

from datamodel_code_generator.model.pydantic import DataTypeManager as _DataTypeManager


class DataTypeManager(_DataTypeManager):
    PATTERN_KEY: ClassVar[str] = 'pattern'
