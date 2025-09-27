from __future__ import annotations

from typing import ClassVar

from datamodel_code_generator.imports import IMPORT_TYPE_ALIAS, IMPORT_ANNOTATED
from datamodel_code_generator.model import DataModel


class TypeAlias(DataModel):
    TEMPLATE_FILE_PATH: ClassVar[str] = "type_alias.jinja2"
    BASE_CLASS: ClassVar[str] = ""
    DEFAULT_IMPORTS: ClassVar[tuple] = (IMPORT_TYPE_ALIAS, IMPORT_ANNOTATED)