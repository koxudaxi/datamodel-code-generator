from typing import ClassVar

from datamodel_code_generator.model import DataModel
from datamodel_code_generator.model.pydantic.imports import IMPORT_DATACLASS


class DataClass(DataModel):
    TEMPLATE_FILE_PATH: ClassVar[str] = 'pydantic/dataclass.jinja2'

    def __post_init__(self) -> None:
        self._additional_imports.append(IMPORT_DATACLASS)
