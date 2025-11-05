from __future__ import annotations

from datamodel_code_generator.model.enum import Enum as _Enum
from datamodel_code_generator.model.strawberry.imports import IMPORT_STRAWBERRY_ENUM


class Enum(_Enum):
    TEMPLATE_FILE_PATH: str = "strawberry/Enum.jinja2"
    BASE_CLASS: str = "Enum"
    DECORATOR: str = "@strawberry.enum"

    def __init__(
        self,
        *,
        reference,
        fields,
        decorators=None,
        base_classes=None,
        custom_base_class=None,
        custom_template_dir=None,
        extra_template_data=None,
        path=None,
        description=None,
        default=None,
        nullable=False,
        keyword_only=False,
        treat_dot_as_module=False,
    ) -> None:
        super().__init__(
            reference=reference,
            fields=fields,
            decorators=decorators,
            base_classes=base_classes,
            custom_base_class=custom_base_class,
            custom_template_dir=custom_template_dir,
            extra_template_data=extra_template_data,
            path=path,
            description=description,
            default=default,
            nullable=nullable,
            keyword_only=keyword_only,
            treat_dot_as_module=treat_dot_as_module,
        )
        self._additional_imports.append(IMPORT_STRAWBERRY_ENUM)

    def set_base_class(self) -> None:
        """Override to use Enum as base class without importing it."""
        # For Strawberry enums, we need Enum as base class but don't need to import it
        from datamodel_code_generator.model.base import BaseClassDataType
        from datamodel_code_generator.imports import Import
        
        # Create a base class reference without importing Enum
        enum_import = Import(import_="Enum", alias="Enum", from_="enum")
        self.base_classes = [BaseClassDataType.from_import(enum_import)]
