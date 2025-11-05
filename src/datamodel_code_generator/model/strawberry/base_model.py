from __future__ import annotations

from datamodel_code_generator.model.base import DataModel, UNDEFINED
from datamodel_code_generator.model.strawberry.imports import IMPORT_STRAWBERRY_TYPE


class BaseModel(DataModel):
    TEMPLATE_FILE_PATH: str = "strawberry/BaseModel.jinja2"
    BASE_CLASS: str = "object"
    DECORATOR: str = "@strawberry.type"

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
        default=UNDEFINED,
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
        self._additional_imports.append(IMPORT_STRAWBERRY_TYPE)
        # Add scalars import for default values
        from datamodel_code_generator.model.strawberry.imports import IMPORT_STRAWBERRY_SCALARS
        self._additional_imports.append(IMPORT_STRAWBERRY_SCALARS)

    def set_base_class(self) -> None:
        """Override to not import built-in Python types."""
        # For Strawberry types, we don't need to import object since it's built-in
        self.base_classes = []
