"""Type alias model generators.

Provides classes for generating type aliases using different Python syntax:
TypeAlias annotation, TypeAliasType, and type statement (Python 3.12+).
"""

from __future__ import annotations

from functools import cached_property
from typing import ClassVar

from datamodel_code_generator.imports import (
    IMPORT_ANNOTATED,
    IMPORT_TYPE_ALIAS,
    IMPORT_TYPE_ALIAS_BACKPORT,
    IMPORT_TYPE_ALIAS_TYPE,
    Import,
)
from datamodel_code_generator.model import DataModel
from datamodel_code_generator.types import chain_as_tuple


class TypeAliasBase(DataModel):
    """Base class for all type alias implementations."""

    IS_ALIAS: bool = True
    _render_counter: ClassVar[int] = 0

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        """Track render order so later aliases can be detected as forward refs."""
        super().__init__(*args, **kwargs)
        TypeAliasBase._render_counter += 1
        self.render_index: int = TypeAliasBase._render_counter

    @cached_property
    def type_alias_quote_names(self) -> set[str]:
        """Names that should be treated as forward references within this alias."""
        if not self.fields:
            return set()

        names: set[str] = set()
        for data_type in self.fields[0].data_type.all_data_types:
            if not data_type.reference:
                continue

            if data_type.reference.path == self.reference.path:
                names.add(data_type.reference.short_name)
                names.add(data_type.reference.name)
                continue

            source = data_type.reference.source
            if (
                isinstance(source, TypeAliasBase)
                and not isinstance(source, TypeStatement)
                and source.render_index >= self.render_index
            ):
                names.add(data_type.reference.short_name)
                names.add(data_type.reference.name)
        return names

    @property
    def should_quote_type_alias(self) -> bool:
        """Return True when this alias contains TypeAlias references that need quoting."""
        return bool(self.type_alias_quote_names)

    @property
    def imports(self) -> tuple[Import, ...]:
        """Get imports including Annotated if needed."""
        imports = super().imports
        if self.fields and (self.fields[0].annotated or self.fields[0].field):
            imports = chain_as_tuple(imports, (IMPORT_ANNOTATED,))

        return imports

    def render(self, *, class_name: str | None = None) -> str:
        """Render the alias, passing quoting info for recursive aliases."""
        return self._render(
            class_name=class_name or self.class_name,
            fields=self.fields,
            decorators=self.decorators,
            base_class=self.base_class,
            methods=self.methods,
            description=self.description,
            dataclass_arguments=self.dataclass_arguments,
            type_alias_quote_names=self.type_alias_quote_names if self.should_quote_type_alias else None,
            **self.extra_template_data,
        )


class TypeAlias(TypeAliasBase):
    """TypeAlias annotation for Python 3.10+ (Name: TypeAlias = type)."""

    TEMPLATE_FILE_PATH: ClassVar[str] = "TypeAliasAnnotation.jinja2"
    BASE_CLASS: ClassVar[str] = ""
    DEFAULT_IMPORTS: ClassVar[tuple[Import, ...]] = (IMPORT_TYPE_ALIAS,)


class TypeAliasBackport(TypeAliasBase):
    """TypeAlias annotation for Python 3.9 (Name: TypeAlias = type) using typing_extensions."""

    TEMPLATE_FILE_PATH: ClassVar[str] = "TypeAliasAnnotation.jinja2"
    BASE_CLASS: ClassVar[str] = ""
    DEFAULT_IMPORTS: ClassVar[tuple[Import, ...]] = (IMPORT_TYPE_ALIAS_BACKPORT,)


class TypeAliasTypeBackport(TypeAliasBase):
    """TypeAliasType for Python 3.9-3.11 (Name = TypeAliasType("Name", type))."""

    TEMPLATE_FILE_PATH: ClassVar[str] = "TypeAliasType.jinja2"
    BASE_CLASS: ClassVar[str] = ""
    DEFAULT_IMPORTS: ClassVar[tuple[Import, ...]] = (IMPORT_TYPE_ALIAS_TYPE,)


class TypeStatement(TypeAliasBase):
    """Type statement for Python 3.12+ (type Name = type)."""

    TEMPLATE_FILE_PATH: ClassVar[str] = "TypeStatement.jinja2"
    BASE_CLASS: ClassVar[str] = ""
    DEFAULT_IMPORTS: ClassVar[tuple[Import, ...]] = ()

    @property
    def should_quote_type_alias(self) -> bool:
        """Type statements (3.12+) never need quoted self references."""
        return False
