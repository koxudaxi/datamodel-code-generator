from __future__ import annotations

from datamodel_code_generator.model.rootmodel import RootModel as _RootModel
from datamodel_code_generator.model.strawberry.imports import IMPORT_STRAWBERRY_TYPE


class RootModel(_RootModel):
    TEMPLATE_FILE_PATH: str = "strawberry/RootModel.jinja2"
    BASE_CLASS: str = "strawberry.type"
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
        self._additional_imports.append(IMPORT_STRAWBERRY_TYPE)
