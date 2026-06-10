"""Enumeration model generator.

Provides Enum, StrEnum, and specialized enum classes for code generation.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Any, ClassVar, Optional

from datamodel_code_generator.imports import IMPORT_ANY, IMPORT_ENUM, IMPORT_INT_ENUM, IMPORT_STR_ENUM, Import
from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.model.base import UNDEFINED, BaseClassDataType
from datamodel_code_generator.types import DataType, Types

if TYPE_CHECKING:
    from collections import defaultdict
    from pathlib import Path

    from datamodel_code_generator.reference import Reference


_INT: str = "int"
_FLOAT: str = "float"
_BYTES: str = "bytes"
_STR: str = "str"


def evaluate_member_value(default: Any) -> Any:
    """Return the runtime value of a member default rendered as a Python literal."""
    if not isinstance(default, str):
        return default
    try:
        return ast.literal_eval(default)
    except (SyntaxError, ValueError):
        return default


def _json_value_equal(member_value: Any, value: Any) -> bool:
    """Compare values with JSON semantics: numbers compare across int/float, bool and str only to themselves."""
    if isinstance(member_value, bool) or isinstance(value, bool):
        return type(member_value) is type(value) and member_value == value
    if isinstance(member_value, (int, float)) and isinstance(value, (int, float)):
        return member_value == value
    return type(member_value) is type(value) and member_value == value


SUBCLASS_BASE_CLASSES: dict[Types, str] = {
    Types.int32: _INT,
    Types.int64: _INT,
    Types.integer: _INT,
    Types.float: _FLOAT,
    Types.double: _FLOAT,
    Types.number: _FLOAT,
    Types.byte: _BYTES,
    Types.string: _STR,
}


class Enum(DataModel):
    """DataModel implementation for Python enumerations."""

    TEMPLATE_FILE_PATH: ClassVar[str] = "Enum.jinja2"
    BASE_CLASS: ClassVar[str] = "enum.Enum"
    DEFAULT_IMPORTS: ClassVar[tuple[Import, ...]] = (IMPORT_ENUM,)
    SUPPORTS_GENERIC_BASE_CLASS: ClassVar[bool] = False

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
        type_: Types | None = None,
        default: Any = UNDEFINED,
        nullable: bool = False,
        keyword_only: bool = False,
        treat_dot_as_module: bool | None = None,
    ) -> None:
        """Initialize Enum with optional specialized base class based on type."""
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
        if not base_classes and type_ and (base_class := SUBCLASS_BASE_CLASSES.get(type_)):
            self.base_classes: list[BaseClassDataType] = [
                BaseClassDataType(type=base_class),
                *self.base_classes,
            ]

    @classmethod
    def get_data_type(cls, types: Types, **kwargs: Any) -> DataType:
        """Get data type for enum (not implemented)."""
        raise NotImplementedError

    def get_member(self, field: DataModelFieldBase) -> Member:
        """Create a Member instance for the given field."""
        return Member(self, field)

    def find_member(self, value: Any, *, coerce_strings: bool = False) -> Member | None:
        """Find the enum member whose value equals the given schema value.

        coerce_strings lets a string value match a non-string member with the same
        string representation, as required for OpenAPI discriminator mapping keys.
        """
        for field in self.fields:
            if field.default is None:
                continue
            member_value = evaluate_member_value(field.default)
            if _json_value_equal(member_value, value):
                return self.get_member(field)
            if (
                coerce_strings
                and isinstance(value, str)
                and not isinstance(member_value, str)
                and str(member_value) == value
            ):
                return self.get_member(field)
        return None

    @property
    def imports(self) -> tuple[Import, ...]:
        """Get imports excluding Any."""
        return tuple(i for i in super().imports if i != IMPORT_ANY)


class StrEnum(Enum):
    """String enumeration type."""

    BASE_CLASS: ClassVar[str] = "enum.StrEnum"
    DEFAULT_IMPORTS: ClassVar[tuple[Import, ...]] = (IMPORT_STR_ENUM,)


class IntEnum(Enum):
    """Integer enumeration type."""

    BASE_CLASS: ClassVar[str] = "enum.IntEnum"
    DEFAULT_IMPORTS: ClassVar[tuple[Import, ...]] = (IMPORT_INT_ENUM,)


SPECIALIZED_ENUM_TYPE_MATCH: dict[Types, type[Enum]] = {
    Types.int32: IntEnum,
    Types.int64: IntEnum,
    Types.integer: IntEnum,
    Types.string: StrEnum,
}
"""
Map specialized enum types to their corresponding Enum subclasses.
"""


class Member:
    """Represents an enum member with its parent enum and field."""

    def __init__(self, enum: Enum, field: DataModelFieldBase) -> None:
        """Initialize enum member."""
        self.enum: Enum = enum
        self.field: DataModelFieldBase = field
        self.alias: Optional[str] = None  # noqa: UP045

    def __repr__(self) -> str:
        """Return string representation of enum member."""
        return f"{self.alias or self.enum.class_name}.{self.field.name}"
