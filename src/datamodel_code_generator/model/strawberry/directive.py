from __future__ import annotations

from datamodel_code_generator.model.base import DataModel, UNDEFINED
from datamodel_code_generator.model.strawberry.imports import IMPORT_STRAWBERRY_DIRECTIVE, IMPORT_STRAWBERRY_LOCATION


class Directive(DataModel):
    TEMPLATE_FILE_PATH: str = "strawberry/Directive.jinja2"
    BASE_CLASS: str = "object"
    DECORATOR: str = "@strawberry.schema_directive"

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
        locations=None,
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
        self._additional_imports.append(IMPORT_STRAWBERRY_DIRECTIVE)
        self.locations = locations or []
        if self.locations:
            self._additional_imports.append(IMPORT_STRAWBERRY_LOCATION)

    def set_base_class(self) -> None:
        """Override to not import built-in Python types."""
        # For Strawberry directives, we don't need to import object since it's built-in
        self.base_classes = []

    def render(self, *, class_name: str | None = None) -> str:
        """Override render to include locations in template context."""
        return self._render(
            class_name=class_name or self.class_name,
            fields=self.fields,
            decorators=self.decorators,
            base_class=self.base_class,
            methods=self.methods,
            description=self.description,
            locations=self.locations,
            **self.extra_template_data,
        )
