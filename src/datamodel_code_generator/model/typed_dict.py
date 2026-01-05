"""TypedDict model generator.

Generates Python TypedDict classes for use with type checkers.
"""

from __future__ import annotations

import keyword
from typing import TYPE_CHECKING, Any, ClassVar

from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.model.base import UNDEFINED
from datamodel_code_generator.model.imports import (
    IMPORT_NOT_REQUIRED,
    IMPORT_NOT_REQUIRED_BACKPORT,
    IMPORT_READ_ONLY,
    IMPORT_READ_ONLY_BACKPORT,
    IMPORT_TYPED_DICT,
    IMPORT_TYPED_DICT_BACKPORT,
)
from datamodel_code_generator.types import NOT_REQUIRED_PREFIX, READ_ONLY_PREFIX

if TYPE_CHECKING:
    from collections import defaultdict
    from collections.abc import Iterator
    from pathlib import Path

    from datamodel_code_generator.imports import Import
    from datamodel_code_generator.reference import Reference


escape_characters = str.maketrans({
    "\\": r"\\",
    "'": r"\'",
    "\b": r"\b",
    "\f": r"\f",
    "\n": r"\n",
    "\r": r"\r",
    "\t": r"\t",
})


def _is_valid_field_name(field: DataModelFieldBase) -> bool:
    name = field.original_name or field.name
    if name is None:  # pragma: no cover
        return False
    return name.isidentifier() and not keyword.iskeyword(name)


class TypedDict(DataModel):
    """DataModel implementation for Python TypedDict."""

    TEMPLATE_FILE_PATH: ClassVar[str] = "TypedDict.jinja2"
    BASE_CLASS: ClassVar[str] = "typing.TypedDict"
    DEFAULT_IMPORTS: ClassVar[tuple[Import, ...]] = (IMPORT_TYPED_DICT,)

    def __init__(  # noqa: PLR0913
        self,
        *,
        reference: Reference,
        fields: list[DataModelFieldBase],
        decorators: list[str] | None = None,
        base_classes: list[Reference] | None = None,
        custom_base_class: str | list[str] | None = None,
        custom_template_dir: Path | None = None,
        extra_template_data: defaultdict[str, dict[str, Any]] | None = None,
        methods: list[str] | None = None,
        path: Path | None = None,
        description: str | None = None,
        default: Any = UNDEFINED,
        nullable: bool = False,
        keyword_only: bool = False,
        treat_dot_as_module: bool | None = None,
    ) -> None:
        """Initialize TypedDict model."""
        super().__init__(
            reference=reference,
            fields=fields,
            decorators=decorators,
            base_classes=base_classes,
            custom_base_class=custom_base_class,
            custom_template_dir=custom_template_dir,
            extra_template_data=extra_template_data,
            methods=methods,
            path=path,
            description=description,
            default=default,
            nullable=nullable,
            keyword_only=keyword_only,
            treat_dot_as_module=treat_dot_as_module,
        )
        self._setup_closed_extra_items()

    def _setup_closed_extra_items(self) -> None:
        """Set up closed and extra_items kwargs based on additionalProperties.

        For PEP 728 TypedDict support:
        - additionalProperties: false -> closed=True
        - additionalProperties: { type: X } -> extra_items=X

        Note: closed=True is not applied to TypedDicts used as base classes,
        as PEP 728 doesn't allow child TypedDicts to add new fields when
        parent has closed=True.
        """
        additional_props = self.extra_template_data.get("additionalProperties")
        additional_props_type = self.extra_template_data.get("additionalPropertiesType")
        is_base_class = self.extra_template_data.get("is_base_class", False)

        typed_dict_kwargs: dict[str, str] = {}

        if additional_props is False and not is_base_class:
            typed_dict_kwargs["closed"] = "True"
        elif additional_props_type and not is_base_class:
            typed_dict_kwargs["extra_items"] = additional_props_type

        if typed_dict_kwargs:
            self.extra_template_data["typed_dict_kwargs"] = typed_dict_kwargs
            kwargs_str = ", ".join(f"{k}={v}" for k, v in typed_dict_kwargs.items())
            self.extra_template_data["typed_dict_kwargs_suffix"] = f", {kwargs_str}"

    @property
    def _has_typed_dict_kwargs(self) -> bool:
        """Check if this TypedDict has closed or extra_items kwargs."""
        return bool(self.extra_template_data.get("typed_dict_kwargs"))

    @property
    def _use_typeddict_backport(self) -> bool:
        """Check if this TypedDict needs typing_extensions.TypedDict for closed/extra_items."""
        return bool(self.extra_template_data.get("use_typeddict_backport"))

    @property
    def base_class(self) -> str:
        """Get base class string with kwargs if needed.

        For PEP 728 support, includes closed=True or extra_items=X in the base class.
        """
        base = super().base_class
        typed_dict_kwargs = self.extra_template_data.get("typed_dict_kwargs")
        if typed_dict_kwargs:
            kwargs_str = ", ".join(f"{k}={v}" for k, v in typed_dict_kwargs.items())
            return f"{base}, {kwargs_str}"
        return base

    @property
    def imports(self) -> tuple[Import, ...]:
        """Get imports, using backport TypedDict when closed/extra_items are used on Python < 3.13."""
        base_imports = list(super().imports)

        if self._use_typeddict_backport and self._has_typed_dict_kwargs:
            base_imports = [i for i in base_imports if i != IMPORT_TYPED_DICT]
            base_imports.append(IMPORT_TYPED_DICT_BACKPORT)

        return tuple(base_imports)

    @property
    def is_functional_syntax(self) -> bool:
        """Check if TypedDict requires functional syntax."""
        return any(not _is_valid_field_name(f) for f in self.fields)

    @property
    def all_fields(self) -> Iterator[DataModelFieldBase]:
        """Iterate over all fields including inherited ones."""
        yield from self.iter_all_fields()

    def render(self, *, class_name: str | None = None) -> str:
        """Render TypedDict class with appropriate syntax."""
        return self._render(
            class_name=class_name or self.class_name,
            fields=self.fields,
            decorators=self.decorators,
            base_class=self.base_class,
            methods=self.methods,
            description=self.description,
            is_functional_syntax=self.is_functional_syntax,
            all_fields=self.all_fields,
            **self.extra_template_data,
        )


class DataModelField(DataModelFieldBase):
    """Field implementation for TypedDict models.

    For Python 3.13+: uses typing.NotRequired and typing.ReadOnly.
    """

    DEFAULT_IMPORTS: ClassVar[tuple[Import, ...]] = (IMPORT_NOT_REQUIRED,)
    DEFAULT_READ_ONLY_IMPORTS: ClassVar[tuple[Import, ...]] = (IMPORT_READ_ONLY,)

    def process_const(self) -> None:
        """Process const field constraint using literal type."""
        self._process_const_as_literal()

    @property
    def key(self) -> str:
        """Get escaped field key for TypedDict."""
        return (self.original_name or self.name or "").translate(  # pragma: no cover
            escape_characters
        )

    @property
    def type_hint(self) -> str:
        """Get type hint with ReadOnly and/or NotRequired wrapper if needed."""
        type_hint = super().type_hint
        # Apply ReadOnly first (inner), then NotRequired (outer)
        if self._read_only:
            type_hint = f"{READ_ONLY_PREFIX}{type_hint}]"
        if self._not_required:
            type_hint = f"{NOT_REQUIRED_PREFIX}{type_hint}]"
        return type_hint

    @property
    def _not_required(self) -> bool:
        """Check if field should be marked as NotRequired."""
        return not self.required and isinstance(self.parent, TypedDict)

    @property
    def _read_only(self) -> bool:
        """Check if field should be marked as ReadOnly."""
        return self.use_frozen_field and self.read_only and isinstance(self.parent, TypedDict)

    @property
    def fall_back_to_nullable(self) -> bool:
        """Check if field should fall back to nullable."""
        return not self._not_required

    @property
    def imports(self) -> tuple[Import, ...]:
        """Get imports including NotRequired and ReadOnly if needed."""
        return (
            *super().imports,
            *(self.DEFAULT_IMPORTS if self._not_required else ()),
            *(self.DEFAULT_READ_ONLY_IMPORTS if self._read_only else ()),
        )


class DataModelFieldReadOnlyBackport(DataModelField):
    """Field implementation for TypedDict models using typing_extensions.ReadOnly.

    For Python 3.11-3.12: uses typing.NotRequired and typing_extensions.ReadOnly.
    """

    DEFAULT_READ_ONLY_IMPORTS: ClassVar[tuple[Import, ...]] = (IMPORT_READ_ONLY_BACKPORT,)


class DataModelFieldBackport(DataModelField):
    """Field implementation for TypedDict models using typing_extensions.

    For Python 3.10: uses typing_extensions.NotRequired and typing_extensions.ReadOnly.
    """

    DEFAULT_IMPORTS: ClassVar[tuple[Import, ...]] = (IMPORT_NOT_REQUIRED_BACKPORT,)
    DEFAULT_READ_ONLY_IMPORTS: ClassVar[tuple[Import, ...]] = (IMPORT_READ_ONLY_BACKPORT,)
