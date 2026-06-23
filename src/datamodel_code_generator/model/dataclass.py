"""Python dataclass model generator.

Generates Python dataclasses using the @dataclass decorator.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Optional, cast

from datamodel_code_generator._format_types import (
    DateClassType,
    DatetimeClassType,
    PythonVersion,
    PythonVersionMin,
)
from datamodel_code_generator.model import DataModel, DataModelFieldBase, _rebuild_model_with_datamodel_namespace
from datamodel_code_generator.model.base import UNDEFINED, _nested_model_default_factory
from datamodel_code_generator.model.imports import IMPORT_DATACLASS, IMPORT_FIELD
from datamodel_code_generator.model.pydantic_base import Constraints  # noqa: TC001 # needed for pydantic
from datamodel_code_generator.model.types import DataTypeManager as _DataTypeManager
from datamodel_code_generator.python_literal import represent_python_value
from datamodel_code_generator.reference import Reference
from datamodel_code_generator.types import StrictTypes, chain_as_tuple

if TYPE_CHECKING:
    from collections import defaultdict
    from collections.abc import Sequence
    from pathlib import Path

    from datamodel_code_generator.enums import DataclassArguments
    from datamodel_code_generator.imports import Import


def has_field_assignment(field: DataModelFieldBase) -> bool:
    """Check if a dataclass field renders with an assignment or default value."""
    return (bool(field.field) and not field.use_annotated) or not (
        (field.required and not field.use_default_with_required) or field.should_strip_default_none()
    )


class _DataclassReuseMixin:
    def create_reuse_model(self, base_ref: Reference) -> DataModel:
        """Create inherited model with empty fields pointing to base reference."""
        model = cast("DataModel", self)
        model_cls = cast("Any", self.__class__)
        model_attrs = vars(model)
        return cast(
            "DataModel",
            model_cls(
                fields=[],
                base_classes=[base_ref],
                description=model.description,
                reference=Reference(
                    name=model.name,
                    path=model.reference.path + "/reuse",
                ),
                custom_template_dir=model_attrs["_custom_template_dir"],
                custom_base_class=model.custom_base_class,
                keyword_only=model.keyword_only,
                frozen=model.frozen,
                treat_dot_as_module=model_attrs["_treat_dot_as_module"],
                dataclass_arguments=model.dataclass_arguments,
            ),
        )


class DataClass(_DataclassReuseMixin, DataModel):
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
        custom_base_class: str | list[str] | None = None,
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
        self._set_deprecated_decorator()


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
        return _nested_model_default_factory(self, DataClass)

    def __str__(self) -> str:
        """Generate field() call or default value representation."""
        data: dict[str, Any] = {k: v for k, v in self.extras.items() if k in self._FIELD_KEYS}

        if self.default != UNDEFINED and self.default is not None:
            data["default"] = self.default

        if self.required and not self.use_default_with_required:
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
                    return f"field(default_factory=lambda: {represent_python_value(default)})"
                return f"field(default_factory={type(default).__name__})"
            return represent_python_value(default)
        kwargs = [f"{k}={v if k == 'default_factory' else represent_python_value(v)}" for k, v in data.items()]
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
        use_object_type: bool = False,  # noqa: FBT001, FBT002
        target_datetime_class: DatetimeClassType = DatetimeClassType.Datetime,
        target_date_class: DateClassType | None = None,
        treat_dot_as_module: bool | None = None,  # noqa: FBT001
        use_serialize_as_any: bool = False,  # noqa: FBT001, FBT002
    ) -> None:
        """Initialize type manager with dataclass datetime defaults."""
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
            use_object_type=use_object_type,
            target_datetime_class=target_datetime_class,
            target_date_class=target_date_class,
            treat_dot_as_module=treat_dot_as_module,
            use_serialize_as_any=use_serialize_as_any,
        )


_rebuild_model_with_datamodel_namespace(DataModelField)
