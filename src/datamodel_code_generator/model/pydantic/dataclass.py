from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Tuple

from datamodel_code_generator.model import DataModel
from datamodel_code_generator.model.pydantic.imports import IMPORT_DATACLASS

if TYPE_CHECKING:
    from datamodel_code_generator.imports import Import


class DataClass(DataModel):
    TEMPLATE_FILE_PATH: ClassVar[str] = "pydantic/dataclass.jinja2"
    DEFAULT_IMPORTS: ClassVar[Tuple[Import, ...]] = (IMPORT_DATACLASS,)  # noqa: UP006
