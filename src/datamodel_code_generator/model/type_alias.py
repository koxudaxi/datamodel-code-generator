from __future__ import annotations

from typing import ClassVar

from datamodel_code_generator.imports import (
    IMPORT_ANNOTATED,
    IMPORT_TYPE_ALIAS_TYPE,
    Import,
)
from datamodel_code_generator.model import DataModel
from datamodel_code_generator.types import chain_as_tuple


class TypeAliasBackport(DataModel):
    TEMPLATE_FILE_PATH: ClassVar[str] = "TypeAliasType.jinja2"
    BASE_CLASS: ClassVar[str] = ""
    DEFAULT_IMPORTS: ClassVar[tuple[Import, ...]] = (IMPORT_TYPE_ALIAS_TYPE,)

    @property
    def imports(self) -> tuple[Import, ...]:
        imports = super().imports
        if self.fields and (self.fields[0].annotated or self.fields[0].field):
            imports = chain_as_tuple(imports, (IMPORT_ANNOTATED,))

        return imports


class TypeStatement(DataModel):
    TEMPLATE_FILE_PATH: ClassVar[str] = "TypeStatement.jinja2"
    BASE_CLASS: ClassVar[str] = ""
    DEFAULT_IMPORTS: ClassVar[tuple[Import, ...]] = ()

    @property
    def imports(self) -> tuple[Import, ...]:
        imports = super().imports
        if self.fields and (self.fields[0].annotated or self.fields[0].field):
            imports = chain_as_tuple(imports, (IMPORT_ANNOTATED,))

        return imports
