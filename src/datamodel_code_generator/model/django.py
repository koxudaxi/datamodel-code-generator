from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Optional

from datamodel_code_generator import DatetimeClassType, PythonVersion, PythonVersionMin
from datamodel_code_generator.imports import (
    IMPORT_DATE,
    IMPORT_DATETIME,
    IMPORT_TIME,
    IMPORT_TIMEDELTA,
    Import,
)
from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.model.base import UNDEFINED
from datamodel_code_generator.model.types import DataTypeManager as _DataTypeManager
from datamodel_code_generator.model.types import type_map_factory
from datamodel_code_generator.types import DataType, StrictTypes, Types

if TYPE_CHECKING:
    from collections import defaultdict
    from collections.abc import Sequence
    from pathlib import Path

    from datamodel_code_generator.reference import Reference

from datamodel_code_generator.model.pydantic.base_model import Constraints  # noqa: TC001

# Django-specific imports
IMPORT_DJANGO_MODELS = Import.from_full_path("django.db.models")


class DjangoModel(DataModel):
    TEMPLATE_FILE_PATH: ClassVar[str] = "django.jinja2"
    BASE_CLASS: ClassVar[str] = "models.Model"
    DEFAULT_IMPORTS: ClassVar[tuple[Import, ...]] = (IMPORT_DJANGO_MODELS,)

    def __init__(  # noqa: PLR0913
        self,
        *,
        reference: Reference,
        fields: list[DataModelFieldBase],
        decorators: list[str] | None = None,
        base_classes: list[Reference] | None = None,
        custom_base_class: str | None = None,
        custom_template_dir: Path | None = None,
        extra_template_data: defaultdict[str, dict[str, Any]] | None = None,
        methods: list[str] | None = None,
        path: Path | None = None,
        description: str | None = None,
        default: Any = UNDEFINED,
        nullable: bool = False,
        keyword_only: bool = False,
        frozen: bool = False,
        treat_dot_as_module: bool = False,
    ) -> None:
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
            frozen=frozen,
            treat_dot_as_module=treat_dot_as_module,
        )

    def set_base_class(self) -> None:
        """Override to handle Django models base class correctly."""
        base_class = self.custom_base_class or self.BASE_CLASS
        if not base_class:
            self.base_classes = []
            return

        # For Django models, we don't need to create an additional import
        # since we already import django.db.models as models
        from datamodel_code_generator.types import DataType  # noqa: PLC0415

        # Create a simple DataType for the base class without additional imports
        base_class_data_type = DataType(type=base_class)
        self.base_classes = [base_class_data_type]


class DataModelField(DataModelFieldBase):
    """Django model field implementation."""

    constraints: Optional[Constraints] = None  # noqa: UP045

    def self_reference(self) -> bool:  # pragma: no cover
        return isinstance(self.parent, DjangoModel) and self.parent.reference.path in {
            d.reference.path for d in self.data_type.all_data_types if d.reference
        }

    @property
    def django_field_type(self) -> str:
        """Map Python types to Django field types."""
        type_hint = self.type_hint

        # Handle basic types
        if type_hint == "str":
            # Check if this is a datetime field based on field name or format
            if hasattr(self, "extras") and self.extras:
                format_type = self.extras.get("format")
                if format_type == "date-time":
                    return "models.DateTimeField"
                if format_type == "date":
                    return "models.DateField"
                if format_type == "time":
                    return "models.TimeField"
                if format_type == "email":
                    return "models.EmailField"

            # Check field name patterns
            field_name = getattr(self, "name", "").lower()
            if "email" in field_name:
                return "models.EmailField"
            if field_name.endswith(("_at", "_time")) or "date" in field_name:
                return "models.DateTimeField"

            return "models.CharField"
        if type_hint == "int":
            return "models.IntegerField"
        if type_hint == "float":
            return "models.FloatField"
        if type_hint == "bool":
            return "models.BooleanField"
        if type_hint == "datetime":
            return "models.DateTimeField"
        if type_hint == "date":
            return "models.DateField"
        if type_hint == "time":
            return "models.TimeField"
        if type_hint == "timedelta":
            return "models.DurationField"
        if type_hint == "Decimal":
            return "models.DecimalField"
        if type_hint == "bytes":
            return "models.BinaryField"

        # Handle Optional types
        if type_hint.startswith("Optional["):
            inner_type = type_hint[9:-1]  # Remove "Optional[" and "]"
            return self._get_field_type_for_inner(inner_type)

        # Handle Union types (simplified)
        if type_hint.startswith("Union["):
            return "models.TextField"  # Default to TextField for complex unions

        # Handle List types
        if type_hint.startswith(("List[", "list[")):
            return "models.JSONField"  # Use JSONField for lists

        # Handle Dict types
        if type_hint.startswith(("Dict[", "dict[")):
            return "models.JSONField"  # Use JSONField for dicts

        # Default to TextField for unknown types
        return "models.TextField"

    def _get_field_type_for_inner(self, inner_type: str) -> str:
        """Get Django field type for inner type (used for Optional types)."""
        if inner_type == "str":
            # Check if this is a datetime field based on field name or format
            if hasattr(self, "extras") and self.extras:
                format_type = self.extras.get("format")
                if format_type == "date-time":
                    return "models.DateTimeField"
                if format_type == "date":
                    return "models.DateField"
                if format_type == "time":
                    return "models.TimeField"
                if format_type == "email":
                    return "models.EmailField"

            # Check field name patterns
            field_name = getattr(self, "name", "").lower()
            if "email" in field_name:
                return "models.EmailField"
            if field_name.endswith(("_at", "_time")) or "date" in field_name:
                return "models.DateTimeField"

            return "models.CharField"
        if inner_type == "int":
            return "models.IntegerField"
        if inner_type == "float":
            return "models.FloatField"
        if inner_type == "bool":
            return "models.BooleanField"
        if inner_type == "datetime":
            return "models.DateTimeField"
        if inner_type == "date":
            return "models.DateField"
        if inner_type == "time":
            return "models.TimeField"
        if inner_type == "timedelta":
            return "models.DurationField"
        if inner_type == "Decimal":
            return "models.DecimalField"
        if inner_type == "bytes":
            return "models.BinaryField"
        return "models.TextField"

    @property
    def django_field_options(self) -> str:
        """Generate Django field options."""
        options = []

        # Handle nullable fields
        if not self.required:
            options.extend(("null=True", "blank=True"))

        # Handle max_length for CharField and EmailField
        field_type = self.django_field_type
        if field_type in {"models.CharField", "models.EmailField"}:
            options.append("max_length=255")  # Default max_length

        # Handle decimal places for DecimalField
        if field_type == "models.DecimalField":
            options.extend(("max_digits=10", "decimal_places=2"))

        # Handle default values
        if self.default != UNDEFINED and self.default is not None:
            if isinstance(self.default, str):
                options.append(f"default='{self.default}'")
            else:
                options.append(f"default={self.default}")

        # Handle help_text from field description
        description = self.extras.get("description")
        if description:
            # Escape single quotes in the description and wrap in single quotes
            escaped_description = description.replace("'", "\\'")
            options.append(f"help_text='{escaped_description}'")

        return ", ".join(options)

    @property
    def field(self) -> str | None:
        """Generate the Django field definition."""
        field_type = self.django_field_type
        options = self.django_field_options

        if options:
            return f"{field_type}({options})"
        return f"{field_type}()"


class DataTypeManager(_DataTypeManager):
    def __init__(  # noqa: PLR0913, PLR0917
        self,
        python_version: PythonVersion = PythonVersionMin,
        use_standard_collections: bool = False,  # noqa: FBT001, FBT002
        use_generic_container_types: bool = False,  # noqa: FBT001, FBT002
        strict_types: Sequence[StrictTypes] | None = None,
        use_non_positive_negative_number_constrained_types: bool = False,  # noqa: FBT001, FBT002
        use_union_operator: bool = False,  # noqa: FBT001, FBT002
        use_pendulum: bool = False,  # noqa: FBT001, FBT002
        target_datetime_class: DatetimeClassType = DatetimeClassType.Datetime,
        treat_dot_as_module: bool = False,  # noqa: FBT001, FBT002
    ) -> None:
        super().__init__(
            python_version,
            use_standard_collections,
            use_generic_container_types,
            strict_types,
            use_non_positive_negative_number_constrained_types,
            use_union_operator,
            use_pendulum,
            target_datetime_class,
            treat_dot_as_module,
        )

        datetime_map = (
            {
                Types.time: self.data_type.from_import(IMPORT_TIME),
                Types.date: self.data_type.from_import(IMPORT_DATE),
                Types.date_time: self.data_type.from_import(IMPORT_DATETIME),
                Types.timedelta: self.data_type.from_import(IMPORT_TIMEDELTA),
            }
            if target_datetime_class is DatetimeClassType.Datetime
            else {}
        )

        self.type_map: dict[Types, DataType] = {
            **type_map_factory(self.data_type),
            **datetime_map,
        }

    def get_data_type(
        self,
        types: Types,
        **kwargs: Any,
    ) -> DataType:
        return self.type_map[types]


def dump_resolve_reference_action(class_names: list[str]) -> str:
    """Django models don't need forward reference resolution."""
    return ""
