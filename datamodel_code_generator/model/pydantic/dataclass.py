from typing import ClassVar, Tuple

from datamodel_code_generator.imports import Import
from datamodel_code_generator.model import DataModel
from datamodel_code_generator.model.pydantic.imports import IMPORT_DATACLASS


class DataClass(DataModel):
    TEMPLATE_FILE_PATH: ClassVar[str] = 'pydantic/dataclass.jinja2'
    DEFAULT_IMPORTS: ClassVar[Tuple[Import, ...]] = (IMPORT_DATACLASS,)
