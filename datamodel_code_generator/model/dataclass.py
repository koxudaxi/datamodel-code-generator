from __future__ import annotations

from typing import ClassVar, Tuple

from datamodel_code_generator.imports import IMPORT_DATACLASS, Import
from datamodel_code_generator.model import DataModel


class DataClass(DataModel):
    TEMPLATE_FILE_PATH: ClassVar[str] = 'dataclass.jinja2'
    DEFAULT_IMPORTS: ClassVar[Tuple[Import, ...]] = (IMPORT_DATACLASS,)
