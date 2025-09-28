from __future__ import annotations

from typing import ClassVar

from datamodel_code_generator.imports import (
    IMPORT_ANNOTATED,
    IMPORT_TYPE_ALIAS,
    IMPORT_TYPE_ALIAS_BACKPORT,
    Import,
)
from datamodel_code_generator.model import DataModel


class TypeAlias(DataModel):
    TEMPLATE_FILE_PATH: ClassVar[str] = "type_alias.jinja2"
    BASE_CLASS: ClassVar[str] = ""
    DEFAULT_IMPORTS: ClassVar[tuple[Import, ...]] = (IMPORT_TYPE_ALIAS, IMPORT_ANNOTATED)


class TypeAliasBackport(DataModel):
    TEMPLATE_FILE_PATH: ClassVar[str] = "type_alias.jinja2"
    BASE_CLASS: ClassVar[str] = ""
    DEFAULT_IMPORTS: ClassVar[tuple[Import, ...]] = (IMPORT_TYPE_ALIAS_BACKPORT, IMPORT_ANNOTATED)
