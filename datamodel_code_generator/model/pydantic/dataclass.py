from typing import ClassVar, Tuple

from ...imports import Import
from .. import DataModel
from .imports import IMPORT_DATACLASS


class DataClass(DataModel):
    TEMPLATE_FILE_PATH: ClassVar[str] = 'pydantic/dataclass.jinja2'
    DEFAULT_IMPORTS: ClassVar[Tuple[Import, ...]] = (IMPORT_DATACLASS,)
