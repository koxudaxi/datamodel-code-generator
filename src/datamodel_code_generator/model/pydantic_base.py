"""Shared base classes for Pydantic model implementations.

Provides Constraints, DataModelField, and BaseModelBase used by Pydantic v2 models.
"""

from __future__ import annotations

from abc import ABC
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Optional

from pydantic import Field

from datamodel_code_generator import cached_path_exists
from datamodel_code_generator.model import (
    UNDEFINED,
    ConstraintsBase,
    DataModel,
    DataModelFieldBase,
    _rebuild_model_with_datamodel_namespace,
)
from datamodel_code_generator.model._pydantic_imports import IMPORT_ANYURL, IMPORT_FIELD
from datamodel_code_generator.model.base import _nested_model_default_factory
from datamodel_code_generator.python_literal import represent_python_value
from datamodel_code_generator.types import (
    UnionIntFloat,
    chain_as_tuple,
    merge_normalized_constraint,
    normalize_integer_constraint,
)

if TYPE_CHECKING:
    from collections import defaultdict

    from datamodel_code_generator.imports import Import
    from datamodel_code_generator.reference import Reference
    from datamodel_code_generator.types import DataType


class Constraints(ConstraintsBase):
    """Pydantic field constraints (gt, ge, lt, le, regex, etc.)."""

    gt: Optional[UnionIntFloat] = Field(None, alias="exclusiveMinimum")  # noqa: UP045
    ge: Optional[UnionIntFloat] = Field(None, alias="minimum")  # noqa: UP045
    lt: Optional[UnionIntFloat] = Field(None, alias="exclusiveMaximum")  # noqa: UP045
    le: Optional[UnionIntFloat] = Field(None, alias="maximum")  # noqa: UP045
    multiple_of: Optional[float] = Field(None, alias="multipleOf")  # noqa: UP045
    min_items: Optional[int] = Field(None, alias="minItems")  # noqa: UP045
    max_items: Optional[int] = Field(None, alias="maxItems")  # noqa: UP045
    min_length: Optional[int] = Field(None, alias="minLength")  # noqa: UP045
    max_length: Optional[int] = Field(None, alias="maxLength")  # noqa: UP045
    regex: Optional[str] = Field(None, alias="pattern")  # noqa: UP045


class PatternConstraints(Constraints):  # noqa: D101
    regex: Optional[str] = Field(None, alias="regex")  # noqa: UP045
    pattern: Optional[str] = Field(None, alias="pattern")  # noqa: UP045


class DataModelField(DataModelFieldBase):
    """Field implementation for Pydantic models."""

    _EXCLUDE_FIELD_KEYS: ClassVar[set[str]] = {
        "alias",
        "default",
        "const",
        "gt",
        "ge",
        "lt",
        "le",
        "multiple_of",
        "min_items",
        "max_items",
        "min_length",
        "max_length",
        "regex",
    }
    _COMPARE_EXPRESSIONS: ClassVar[set[str]] = {"gt", "ge", "lt", "le"}
    _INTEGER_CONSTRAINTS: ClassVar[set[str]] = _COMPARE_EXPRESSIONS | {"multiple_of"}
    constraints: Optional[Constraints] = None  # noqa: UP045

    @property
    def has_default_factory_in_field(self) -> bool:
        """Check if this field has a default_factory in Field() including computed ones."""
        return "default_factory" in self.extras or self.__dict__.get("_computed_default_factory") is not None

    @property
    def method(self) -> str | None:
        """Get the validation method name."""
        return self.validator

    @property
    def validator(self) -> str | None:
        """Get the validator name."""
        return None
        # TODO refactor this method for other validation logic

    @property
    def field(self) -> str | None:
        """For backwards compatibility."""
        if self.is_class_var:
            return None
        result = str(self)
        if (
            self.use_default_kwarg
            and not result.startswith("Field(...")
            and not result.startswith("Field(default_factory=")
        ):
            # Use `default=` for fields that have a default value so that type
            # checkers using @dataclass_transform can infer the field as
            # optional in __init__.
            result = result.replace("Field(", "Field(default=")
        if not result:
            return None
        return result

    def _has_field_statement(self) -> bool:
        """Return whether rendering this field will require a Field() call."""
        if self.is_class_var:
            self.__dict__["_computed_default_factory"] = None
            return False

        has_field_metadata = (
            self.extras
            or self.alias
            or self.const
            or self.constraints is not None
            or (self.use_frozen_field and self.read_only)
            or self.validation_aliases
            or self.serialization_alias is not None
            or self.use_serialization_alias
        )
        needs_required_nullable_field = self.nullable and self.required and not self.use_default_with_required
        needs_optional_nested_factory = (
            self.use_default_factory_for_optional_nested_models
            and not self.required
            and (self.default is None or self.default is UNDEFINED)
        )
        if not has_field_metadata and not needs_required_nullable_field and not needs_optional_nested_factory:
            self.__dict__["_computed_default_factory"] = None
            return False

        data, default_factory = self._get_field_data_and_default_factory()

        if default_factory or any(v is not None for v in data.values()):
            return True
        return bool(self.nullable and self.required and not self.use_default_with_required)

    def _has_numeric_data_type(self, type_name: str, strict_import_part: str) -> bool:
        """Return whether any field data type is the given builtin or strict numeric type."""
        return any(
            data_type.type == type_name
            or (data_type.strict and data_type.import_ and strict_import_part in data_type.import_.import_)
            for data_type in self.data_type.all_data_types
        )

    def _get_strict_field_constraint(
        self, constraint: str, value: Any, *, is_float_type: bool, is_int_type: bool
    ) -> tuple[str, Any] | None:
        if value is None or constraint not in self._INTEGER_CONSTRAINTS:
            return constraint, value
        if is_float_type:
            return constraint, float(value)
        if is_int_type:
            return normalize_integer_constraint(constraint, value)
        if isinstance(value, float) and value.is_integer():
            return constraint, int(value)
        return constraint, value

    def _get_normalized_constraint_data(self) -> dict[str, Any]:
        """Build constraint data with integer-safe values, merging colliding bounds."""
        assert self.constraints is not None
        dumped = self.constraints._exclude_unset_dump  # noqa: SLF001
        has_integer_constraints = bool(self._INTEGER_CONSTRAINTS & dumped.keys())
        is_float_type = has_integer_constraints and self._has_numeric_data_type("float", "Float")
        is_int_type = has_integer_constraints and not is_float_type and self._has_numeric_data_type("int", "Int")
        constraint_data: dict[str, Any] = {}
        for k, v in dumped.items():
            if (
                normalized := self._get_strict_field_constraint(
                    k, v, is_float_type=is_float_type, is_int_type=is_int_type
                )
            ) is not None:
                merge_normalized_constraint(constraint_data, normalized[0], normalized[1])
        return constraint_data

    def _has_anyurl_outside_container(self) -> bool:
        def has_anyurl(data_type: DataType, *, inside_container: bool) -> bool:
            is_container = inside_container or (
                data_type.is_dict
                or data_type.is_list
                or data_type.is_set
                or data_type.is_frozen_set
                or data_type.is_mapping
                or data_type.is_sequence
                or data_type.is_tuple
            )
            if data_type.import_ == IMPORT_ANYURL:
                return not is_container
            return any(has_anyurl(child, inside_container=is_container) for child in data_type.data_types) or (
                data_type.dict_key is not None and has_anyurl(data_type.dict_key, inside_container=is_container)
            )

        return has_anyurl(self.data_type, inside_container=False)

    def _get_default_factory_for_optional_nested_model(self) -> str | None:
        """Get default_factory for optional nested Pydantic model fields.

        Returns the class name if the field type references a BaseModel,
        otherwise returns None.
        """
        return _nested_model_default_factory(self, BaseModelBase)

    def _process_data_in_str(self, data: dict[str, Any]) -> None:  # pragma: no cover
        if self.const:
            data["const"] = True

        if self.use_frozen_field and self.read_only:
            data["allow_mutation"] = False

    def _process_annotated_field_arguments(self, field_arguments: list[str]) -> list[str]:  # noqa: PLR6301
        return field_arguments

    def _get_field_data_and_default_factory(self) -> tuple[dict[str, Any], Any]:
        """Build Field() keyword data and the effective default_factory."""
        data: dict[str, Any] = {k: v for k, v in self.extras.items() if k not in self._EXCLUDE_FIELD_KEYS}
        if self.alias:
            data["alias"] = self.alias
        has_type_constraints = self.data_type.kwargs is not None and len(self.data_type.kwargs) > 0
        if (
            self.constraints is not None
            and not self.self_reference()
            and not (self.data_type.strict and has_type_constraints)
        ):
            if self._has_anyurl_outside_container():
                constraint_data: dict[str, Any] = {}
            else:
                constraint_data = self._get_normalized_constraint_data()
            data = {**data, **constraint_data}

        if self.use_field_description:
            data.pop("description", None)  # Description is part of field docstring

        self._process_data_in_str(data)

        discriminator = data.pop("discriminator", None)
        if discriminator:
            if isinstance(discriminator, str):
                data["discriminator"] = discriminator
            elif isinstance(discriminator, dict):  # pragma: no cover
                data["discriminator"] = discriminator["propertyName"]

        if (self.required and not self.has_default) or (
            self.default is not UNDEFINED and self.default is not None and "default_factory" not in data
        ):
            default_factory = None
        else:
            default_factory = data.pop("default_factory", None)

        if (
            default_factory is None
            and self.use_default_factory_for_optional_nested_models
            and not self.required
            and (self.default is None or self.default is UNDEFINED)
        ):
            default_factory = self._get_default_factory_for_optional_nested_model()

        self.__dict__["_computed_default_factory"] = default_factory

        return data, default_factory

    def __str__(self) -> str:
        """Return Field() call with all constraints and metadata."""
        data, default_factory = self._get_field_data_and_default_factory()

        field_arguments = sorted(f"{k}={represent_python_value(v)}" for k, v in data.items() if v is not None)

        if not field_arguments and not default_factory:
            if self.nullable and self.required and not self.use_default_with_required:
                return "Field(...)"  # Field() is for mypy
            return ""

        if default_factory:
            field_arguments = [f"default_factory={default_factory}", *field_arguments]

        if self.use_annotated:
            field_arguments = self._process_annotated_field_arguments(field_arguments)
        elif (
            self.required
            and not self.use_default_with_required
            and not default_factory
            and not self.extras.get("validate_default")
        ):
            field_arguments = ["...", *field_arguments]
        elif not default_factory:
            default_repr = represent_python_value(self.default)
            field_arguments = [default_repr, *field_arguments]

        if self.is_class_var:
            if self.default is UNDEFINED:  # pragma: no cover
                return ""
            return represent_python_value(self.default)

        return f"Field({', '.join(field_arguments)})"

    @property
    def is_class_var(self) -> bool:
        """Check if this field is a ClassVar."""
        return self.extras.get("x-is-classvar") is True

    @property
    def type_hint(self) -> str:
        """Get the type hint including ClassVar if applicable."""
        if self.is_class_var:
            return f"ClassVar[{super().type_hint}]"
        return super().type_hint

    @property
    def annotated(self) -> str | None:
        """Get the Annotated type hint if use_annotated is enabled."""
        if not self.use_annotated or self.is_class_var:
            return None
        if not (field := str(self)):
            return None
        return f"Annotated[{self.type_hint}, {field}]"

    @property
    def imports(self) -> tuple[Import, ...]:
        """Get all required imports including Field if needed.

        Computes _has_field_statement() once and derives needs_annotated from it:
        str(self) is non-empty exactly when _has_field_statement() is true (both
        come from the same Field() data), so this matches bool(self.annotated)
        without rebuilding the type hint and Field() string.
        """
        has_field_statement = self._has_field_statement()
        base_imports = self._collect_field_imports(
            needs_annotated=self.use_annotated and not self.is_class_var and has_field_statement
        )
        if has_field_statement:
            return chain_as_tuple(base_imports, (IMPORT_FIELD,))
        return base_imports


class BaseModelBase(DataModel, ABC):
    """Abstract base class for Pydantic BaseModel implementations."""

    REQUIRES_RUNTIME_IMPORTS_WITH_RUFF_CHECK: ClassVar[bool] = True

    def __init__(  # noqa: PLR0913
        self,
        *,
        reference: Reference,
        fields: list[DataModelFieldBase],
        decorators: list[str] | None = None,
        base_classes: list[Reference] | None = None,
        custom_base_class: str | list[str] | None = None,
        custom_template_dir: Path | None = None,
        extra_template_data: defaultdict[str, Any] | None = None,
        path: Path | None = None,
        description: str | None = None,
        default: Any = UNDEFINED,
        nullable: bool = False,
        keyword_only: bool = False,
        treat_dot_as_module: bool | None = None,
    ) -> None:
        """Initialize the BaseModel with fields and configuration."""
        methods: list[str] = [field.method for field in fields if field.method]

        super().__init__(
            fields=fields,
            reference=reference,
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

    @cached_property
    def template_file_path(self) -> Path:
        """Get the template file path with backward compatibility support."""
        # This property is for Backward compatibility
        # Current version supports '{custom_template_dir}/BaseModel.jinja'
        # But, Future version will support only '{custom_template_dir}/pydantic/BaseModel.jinja'
        if self._custom_template_dir is not None:
            custom_template_file_path = self._custom_template_dir / Path(self.TEMPLATE_FILE_PATH).name
            if cached_path_exists(custom_template_file_path):
                return custom_template_file_path
        return super().template_file_path


_rebuild_model_with_datamodel_namespace(DataModelField)
