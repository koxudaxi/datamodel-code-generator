"""Python dataclass model generator.

Generates Python dataclasses using the @dataclass decorator.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Optional

from datamodel_code_generator import (
    DataclassArguments,
    DateClassType,
    DatetimeClassType,
    PythonVersion,
    PythonVersionMin,
)
from datamodel_code_generator.imports import (
    IMPORT_DATE,
    IMPORT_DATETIME,
    IMPORT_TIME,
    IMPORT_TIMEDELTA,
    Import,
)
from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.model.base import UNDEFINED
from datamodel_code_generator.model.imports import IMPORT_DATACLASS, IMPORT_FIELD
from datamodel_code_generator.model.pydantic.base_model import Constraints  # noqa: TC001 # needed for pydantic
from datamodel_code_generator.model.types import DataTypeManager as _DataTypeManager
from datamodel_code_generator.model.types import standard_primitive_type_map_factory, type_map_factory
from datamodel_code_generator.reference import Reference
from datamodel_code_generator.types import DataType, StrictTypes, Types, chain_as_tuple

if TYPE_CHECKING:
    from collections import defaultdict
    from collections.abc import Sequence
    from pathlib import Path


def has_field_assignment(field: DataModelFieldBase) -> bool:
    """Check if a dataclass field has a default value or field() assignment."""
    return bool(field.field) or not (
        field.required or (field.represented_default == "None" and field.strip_default_none)
    )


class DataClass(DataModel):
    """DataModel implementation for Python dataclasses."""

    TEMPLATE_FILE_PATH: ClassVar[str] = "dataclass.jinja2"
    DEFAULT_IMPORTS: ClassVar[tuple[Import, ...]] = (IMPORT_DATACLASS,)
    SUPPORTS_DISCRIMINATOR: ClassVar[bool] = True
    SUPPORTS_KW_ONLY: ClassVar[bool] = True

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
        treat_dot_as_module: bool | None = None,
        dataclass_arguments: DataclassArguments | None = None,
    ) -> None:
        """Initialize dataclass with fields sorted by field assignment requirement."""
        super().__init__(
            reference=reference,
            fields=sorted(fields, key=has_field_assignment),
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
        if dataclass_arguments is not None:
            self.dataclass_arguments = dataclass_arguments
        else:
            self.dataclass_arguments = {}
            if frozen:
                self.dataclass_arguments["frozen"] = True
            if keyword_only:
                self.dataclass_arguments["kw_only"] = True

    def create_reuse_model(self, base_ref: Reference) -> DataClass:
        """Create inherited model with empty fields pointing to base reference."""
        return self.__class__(
            fields=[],
            base_classes=[base_ref],
            description=self.description,
            reference=Reference(
                name=self.name,
                path=self.reference.path + "/reuse",
            ),
            custom_template_dir=self._custom_template_dir,
            custom_base_class=self.custom_base_class,
            keyword_only=self.keyword_only,
            frozen=self.frozen,
            treat_dot_as_module=self._treat_dot_as_module,
            dataclass_arguments=self.dataclass_arguments,
        )


class DataModelField(DataModelFieldBase):
    """Field implementation for dataclass models."""

    _FIELD_KEYS: ClassVar[set[str]] = {
        "default_factory",
        "init",
        "repr",
        "hash",
        "compare",
        "metadata",
        "kw_only",
    }
    constraints: Optional[Constraints] = None  # noqa: UP045

    def process_const(self) -> None:
        """Process const field constraint using literal type."""
        self._process_const_as_literal()

    @property
    def imports(self) -> tuple[Import, ...]:
        """Get imports including field() if needed."""
        field = self.field
        if field and field.startswith("field("):
            return chain_as_tuple(super().imports, (IMPORT_FIELD,))
        return super().imports

    @property
    def field(self) -> str | None:
        """For backwards compatibility."""
        result = str(self)
        if not result:
            return None
        return result

    def _get_default_factory_for_nested_model(self) -> str | None:
        """Get default_factory for nested dataclass model fields.

        Returns the class name if the field type references a DataClass,
        otherwise returns None.
        """
        for data_type in self.data_type.data_types or (self.data_type,):
            if data_type.is_dict:
                continue
            if data_type.reference and isinstance(data_type.reference.source, DataClass):
                return data_type.alias or data_type.reference.source.class_name
        return None

    def __str__(self) -> str:
        """Generate field() call or default value representation."""
        data: dict[str, Any] = {k: v for k, v in self.extras.items() if k in self._FIELD_KEYS}

        if self.default != UNDEFINED and self.default is not None:
            data["default"] = self.default

        if self.required:
            data = {
                k: v
                for k, v in data.items()
                if k
                not in {
                    "default",
                    "default_factory",
                }
            }

        if (
            self.use_default_factory_for_optional_nested_models
            and not self.required
            and (self.default is None or self.default is UNDEFINED)
            and "default_factory" not in data
        ):
            nested_model_name = self._get_default_factory_for_nested_model()
            if nested_model_name:
                data["default_factory"] = nested_model_name

        if not data:
            return ""

        if len(data) == 1 and "default" in data:
            default = data["default"]

            if isinstance(default, (list, dict, set)):
                if default:
                    from datamodel_code_generator.model.base import repr_set_sorted  # noqa: PLC0415

                    default_repr = repr_set_sorted(default) if isinstance(default, set) else repr(default)
                    return f"field(default_factory=lambda: {default_repr})"
                return f"field(default_factory={type(default).__name__})"
            return repr(default)
        kwargs = [f"{k}={v if k == 'default_factory' else repr(v)}" for k, v in data.items()]
        return f"field({', '.join(kwargs)})"


class DataTypeManager(_DataTypeManager):
    """Type manager for dataclass models."""

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        python_version: PythonVersion = PythonVersionMin,
        use_standard_collections: bool = False,  # noqa: FBT001, FBT002
        use_generic_container_types: bool = False,  # noqa: FBT001, FBT002
        strict_types: Sequence[StrictTypes] | None = None,
        use_non_positive_negative_number_constrained_types: bool = False,  # noqa: FBT001, FBT002
        use_decimal_for_multiple_of: bool = False,  # noqa: FBT001, FBT002
        use_union_operator: bool = False,  # noqa: FBT001, FBT002
        use_pendulum: bool = False,  # noqa: FBT001, FBT002
        use_standard_primitive_types: bool = False,  # noqa: FBT001, FBT002
        target_datetime_class: DatetimeClassType = DatetimeClassType.Datetime,
        target_date_class: DateClassType | None = None,  # noqa: ARG002
        treat_dot_as_module: bool | None = None,  # noqa: FBT001
        use_serialize_as_any: bool = False,  # noqa: FBT001, FBT002
    ) -> None:
        """Initialize type manager with datetime type mapping."""
        super().__init__(
            python_version=python_version,
            use_standard_collections=use_standard_collections,
            use_generic_container_types=use_generic_container_types,
            strict_types=strict_types,
            use_non_positive_negative_number_constrained_types=use_non_positive_negative_number_constrained_types,
            use_decimal_for_multiple_of=use_decimal_for_multiple_of,
            use_union_operator=use_union_operator,
            use_pendulum=use_pendulum,
            use_standard_primitive_types=use_standard_primitive_types,
            target_datetime_class=target_datetime_class,
            treat_dot_as_module=treat_dot_as_module,
            use_serialize_as_any=use_serialize_as_any,
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

        standard_primitive_map = (
            standard_primitive_type_map_factory(self.data_type) if use_standard_primitive_types else {}
        )

        self.type_map: dict[Types, DataType] = {
            **type_map_factory(self.data_type),
            **datetime_map,
            **standard_primitive_map,
        }
