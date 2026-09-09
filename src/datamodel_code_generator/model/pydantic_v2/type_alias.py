"""Compatibility aliases for older Pydantic dataclass runtimes."""

from __future__ import annotations

from typing import ClassVar

from datamodel_code_generator.imports import IMPORT_TYPE_ALIAS, IMPORT_TYPE_ALIAS_TYPE, Import
from datamodel_code_generator.model.type_alias import TypeAliasTypeBackport


class TypeAlias(TypeAliasTypeBackport):
    """Avoid named reference aliases that Pydantic before 2.10 cannot resolve."""

    TEMPLATE_FILE_PATH: ClassVar[str] = "PydanticV2TypeAlias.jinja2"

    @property
    def imports(self) -> tuple[Import, ...]:
        """Import the alias syntax selected by the compatibility template."""
        imports = super().imports
        if self.fields and self.fields[0].data_type.reference:
            return (*(value for value in imports if value != IMPORT_TYPE_ALIAS_TYPE), IMPORT_TYPE_ALIAS)
        return imports
