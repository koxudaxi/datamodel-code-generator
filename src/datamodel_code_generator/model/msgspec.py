"""msgspec.Struct model generator.

Generates Python models using msgspec.Struct for high-performance serialization.
"""

from __future__ import annotations

from functools import lru_cache, wraps
from math import isfinite
from typing import TYPE_CHECKING, Any, ClassVar, Optional, TypeVar

from datamodel_code_generator.imports import IMPORT_UNION, Import
from datamodel_code_generator.model import DataModel, DataModelFieldBase, _rebuild_model_with_datamodel_namespace
from datamodel_code_generator.model.base import UNDEFINED, BaseClassDataType, _nested_model_default_factory
from datamodel_code_generator.model.imports import (
    IMPORT_MSGSPEC_CONVERT,
    IMPORT_MSGSPEC_FIELD,
    IMPORT_MSGSPEC_META,
    IMPORT_MSGSPEC_STRUCT,
    IMPORT_MSGSPEC_UNSET,
    IMPORT_MSGSPEC_UNSETTYPE,
)
from datamodel_code_generator.model.pydantic_base import (
    PatternConstraints as _Constraints,
)
from datamodel_code_generator.model.type_alias import TypeAliasBase
from datamodel_code_generator.model.types import DataTypeManager as _DataTypeManager
from datamodel_code_generator.python_literal import represent_python_value
from datamodel_code_generator.types import (
    NONE,
    OPTIONAL_PREFIX,
    UNION_DELIMITER,
    UNION_OPERATOR_DELIMITER,
    UNION_PREFIX,
    _remove_none_from_union,
    chain_as_tuple,
    merge_normalized_constraint,
    normalize_integer_constraint,
)

UNSET_TYPE = "UnsetType"


class _UNSET:
    def __str__(self) -> str:
        return "UNSET"

    __repr__ = __str__


UNSET = _UNSET()


if TYPE_CHECKING:
    from collections import defaultdict
    from pathlib import Path

    from datamodel_code_generator.reference import Reference


def has_field_assignment(field: DataModelFieldBase) -> bool:
    """Return whether a msgspec field renders with a default assignment."""
    return field.use_default_with_required or not (
        field.required or (field.represented_default == "None" and field.strip_default_none)
    )


DataModelFieldBaseT = TypeVar("DataModelFieldBaseT", bound=DataModelFieldBase)


def import_extender(cls: type[DataModelFieldBaseT]) -> type[DataModelFieldBaseT]:
    """Extend imports property with msgspec-specific imports."""
    original_imports: property = cls.imports

    @wraps(original_imports.fget)  # ty: ignore
    def new_imports(self: DataModelFieldBaseT) -> tuple[Import, ...]:
        if self.extras.get("is_classvar"):
            return ()
        extra_imports = []
        field = self.field
        # TODO: Improve field detection
        if field and field.startswith("field("):
            extra_imports.append(IMPORT_MSGSPEC_FIELD)
        if field and "lambda: convert" in field:
            extra_imports.append(IMPORT_MSGSPEC_CONVERT)
        if isinstance(self, DataModelField) and self.needs_meta_import:
            extra_imports.append(IMPORT_MSGSPEC_META)
        if not self.required and not self.nullable:
            extra_imports.append(IMPORT_MSGSPEC_UNSETTYPE)
            if not self.data_type.use_union_operator:
                extra_imports.append(IMPORT_UNION)
            if self.default is None or self.default is UNDEFINED:
                extra_imports.append(IMPORT_MSGSPEC_UNSET)
        return chain_as_tuple(original_imports.fget(self), extra_imports)  # ty: ignore

    cls.imports = property(new_imports)  # ty: ignore
    return cls


class Struct(DataModel):
    """DataModel implementation for msgspec.Struct."""

    TEMPLATE_FILE_PATH: ClassVar[str] = "msgspec.jinja2"
    BASE_CLASS: ClassVar[str] = "msgspec.Struct"
    BASE_CLASS_NAME: ClassVar[str] = "Struct"
    BASE_CLASS_ALIAS: ClassVar[str] = "_Struct"
    DEFAULT_IMPORTS: ClassVar[tuple[Import, ...]] = ()
    SUPPORTS_DISCRIMINATOR: ClassVar[bool] = True
    SUPPORTS_KW_ONLY: ClassVar[bool] = True
    CONFIG_MAPPING: ClassVar[dict[tuple[str, Any], tuple[str, Any] | None]] = {
        ("allow_mutation", False): ("frozen", True),
        ("extra_fields", "forbid"): ("forbid_unknown_fields", True),
        ("extra_fields", "allow"): None,
        ("extra_fields", "ignore"): None,
        ("allow_extra_fields", True): None,
        ("allow_population_by_field_name", True): None,
        ("use_attribute_docstrings", True): None,
    }

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
        """Initialize msgspec Struct with fields sorted by field assignment requirement."""
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
            treat_dot_as_module=treat_dot_as_module,
        )
        self.extra_template_data.setdefault("base_class_kwargs", {})
        if self.keyword_only:
            self.add_base_class_kwarg("kw_only", "True")

    def add_base_class_kwarg(self, name: str, value: str) -> None:
        """Add keyword argument to base class constructor."""
        self.extra_template_data["base_class_kwargs"][name] = value

    @classmethod
    def create_base_class_model(
        cls,
        config: dict[str, Any],
        reference: Reference,
        custom_template_dir: Path | None = None,
        keyword_only: bool = False,  # noqa: FBT001, FBT002
        treat_dot_as_module: bool | None = None,  # noqa: FBT001
    ) -> Struct | None:
        """Create a shared base class model for DRY configuration.

        Creates a Struct that inherits from msgspec.Struct (aliased as _Struct)
        with the specified configuration. Updates the reference path and name in place.
        """
        reference.path = f"#/{cls.BASE_CLASS_NAME}"
        reference.name = cls.BASE_CLASS_NAME

        base_model = cls(
            reference=reference,
            fields=[],
            custom_template_dir=custom_template_dir,
            keyword_only=keyword_only,
            treat_dot_as_module=treat_dot_as_module,
        )

        base_model.base_classes = [BaseClassDataType(type=cls.BASE_CLASS_ALIAS)]

        for key, value in config.items():
            mapping_result = cls.CONFIG_MAPPING.get((key, value))
            if mapping_result is None:
                continue
            mapped_key, mapped_value = mapping_result
            base_model.add_base_class_kwarg(mapped_key, str(mapped_value))

        base_model._additional_imports.append(
            Import(from_=IMPORT_MSGSPEC_STRUCT.from_, import_=IMPORT_MSGSPEC_STRUCT.import_, alias=cls.BASE_CLASS_ALIAS)
        )

        return base_model


class Constraints(_Constraints):
    """Constraint model for msgspec fields."""


@lru_cache
def get_neither_required_nor_nullable_type(type_: str, use_union_operator: bool) -> str:  # noqa: FBT001
    """Get type hint for fields that are neither required nor nullable, using UnsetType."""
    type_ = _remove_none_from_union(type_, use_union_operator=use_union_operator)
    if type_.startswith(OPTIONAL_PREFIX):  # pragma: no cover
        type_ = type_[len(OPTIONAL_PREFIX) : -1]

    if not type_ or type_ == NONE:
        return UNSET_TYPE
    if use_union_operator:
        return UNION_OPERATOR_DELIMITER.join((type_, UNSET_TYPE))
    if type_.startswith(UNION_PREFIX):
        return f"{type_[:-1]}{UNION_DELIMITER}{UNSET_TYPE}]"
    return f"{UNION_PREFIX}{type_}{UNION_DELIMITER}{UNSET_TYPE}]"


@lru_cache
def _add_unset_type(type_: str, use_union_operator: bool) -> str:  # noqa: FBT001
    """Add UnsetType to a type hint without removing None."""
    if use_union_operator:
        return f"{type_}{UNION_OPERATOR_DELIMITER}{UNSET_TYPE}"
    if type_.startswith(UNION_PREFIX):  # pragma: no cover
        return f"{type_[:-1]}{UNION_DELIMITER}{UNSET_TYPE}]"
    if type_.startswith(OPTIONAL_PREFIX):  # pragma: no cover
        inner_type = type_[len(OPTIONAL_PREFIX) : -1]
        return f"{UNION_PREFIX}{inner_type}{UNION_DELIMITER}{NONE}{UNION_DELIMITER}{UNSET_TYPE}]"
    return f"{UNION_PREFIX}{type_}{UNION_DELIMITER}{UNSET_TYPE}]"  # pragma: no cover


@import_extender
class DataModelField(DataModelFieldBase):
    """Field implementation for msgspec Struct models."""

    _FIELD_KEYS: ClassVar[set[str]] = {
        "default",
        "default_factory",
    }
    _META_FIELD_KEYS: ClassVar[set[str]] = {
        "title",
        "description",
        "gt",
        "ge",
        "lt",
        "le",
        "multiple_of",
        "min_items",
        "max_items",
        "min_length",
        "max_length",
        "pattern",
        "examples",
        # 'unique_items', # not supported by msgspec
    }
    _PARSE_METHOD = "convert"
    _COMPARE_EXPRESSIONS: ClassVar[set[str]] = {"gt", "ge", "lt", "le", "multiple_of"}
    constraints: Optional[Constraints] = None  # noqa: UP045

    def process_const(self) -> None:
        """Process const field constraint."""
        if "const" not in self.extras:
            return
        self.const = True
        self.nullable = False
        const = self.extras["const"]
        if self.data_type.type == "str" and isinstance(const, str):  # pragma: no cover
            self.replace_data_type(self.data_type.__class__(literals=[const]), clear_old_parent=False)

    def _has_numeric_data_type(self, type_name: str) -> bool:
        """Return whether any field data type is the given numeric type."""
        return any(data_type.type == type_name for data_type in self.data_type.all_data_types)

    def _get_strict_field_constraint(
        self, constraint: str, value: Any, *, is_float_type: bool, is_int_type: bool
    ) -> tuple[str, Any] | None:
        """Return a constraint normalized for the field's numeric type.

        Non-finite bounds are dropped because msgspec Meta only accepts finite values.
        """
        if value is None or constraint not in self._COMPARE_EXPRESSIONS:
            return constraint, value
        if isinstance(value, float) and not isfinite(value):
            return None
        if is_float_type:
            return constraint, float(value)
        if is_int_type:
            return normalize_integer_constraint(constraint, value)
        if isinstance(value, float) and value.is_integer():
            return constraint, int(value)
        return constraint, value

    @property
    def field(self) -> str | None:
        """For backwards compatibility."""
        result = str(self)
        if not result:
            return None
        return result

    def __str__(self) -> str:  # noqa: PLR0912
        """Generate field() call or default value representation."""
        data: dict[str, Any] = {k: v for k, v in self.extras.items() if k in self._FIELD_KEYS}
        if self.alias:
            data["name"] = self.alias

        if self.default is not UNDEFINED and self.default is not None:
            data["default"] = self.default
        elif self._not_required and "default_factory" not in data:
            data["default"] = None if self.nullable else UNSET

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
        elif self.default and "default_factory" not in data:
            default_factory = self._get_default_as_struct_model()
            if default_factory is not None:
                data.pop("default")
                data["default_factory"] = default_factory

        if "default" in data and isinstance(data["default"], (list, dict, set)) and "default_factory" not in data:
            default_value = data.pop("default")
            if default_value:
                data["default_factory"] = f"lambda: {represent_python_value(default_value)}"
            else:
                data["default_factory"] = type(default_value).__name__

        if (
            self.use_default_factory_for_optional_nested_models
            and not self.required
            and (self.default is None or self.default is UNDEFINED)
            and "default_factory" not in data
        ):
            nested_model_name = self._get_default_factory_for_optional_nested_model()
            if nested_model_name:
                data["default_factory"] = nested_model_name
                data.pop("default", None)

        if not data:
            return ""

        if len(data) == 1 and "default" in data:
            return represent_python_value(data["default"])

        kwargs = [f"{k}={v if k == 'default_factory' else represent_python_value(v)}" for k, v in data.items()]
        return f"field({', '.join(kwargs)})"

    @property
    def type_hint(self) -> str:
        """Return the type hint, using UnsetType for non-required non-nullable fields."""
        type_hint = super().type_hint
        if self._not_required and not self.nullable:
            if self.data_type.is_optional:
                return _add_unset_type(type_hint, self.data_type.use_union_operator)
            return get_neither_required_nor_nullable_type(type_hint, self.data_type.use_union_operator)
        return type_hint

    @property
    def _not_required(self) -> bool:
        return not self.required and isinstance(self.parent, Struct)

    @property
    def fall_back_to_nullable(self) -> bool:
        """Return whether to fall back to nullable type instead of UnsetType."""
        return not self._not_required

    def _get_meta_string(self) -> str | None:
        """Compute Meta(...) string if there are any meta constraints."""
        data: dict[str, Any] = {k: v for k, v in self.extras.items() if k in self._META_FIELD_KEYS}
        has_type_constraints = self.data_type.kwargs is not None and len(self.data_type.kwargs) > 0
        if (
            self.constraints is not None
            and not self.self_reference()
            and not (self.data_type.strict and has_type_constraints)
        ):
            dumped = self.constraints.model_dump()
            has_integer_constraints = any(dumped.get(key) is not None for key in self._COMPARE_EXPRESSIONS)
            is_float_type = has_integer_constraints and self._has_numeric_data_type("float")
            is_int_type = has_integer_constraints and not is_float_type and self._has_numeric_data_type("int")
            constraint_data: dict[str, Any] = {}
            for k, v in dumped.items():
                if k not in self._META_FIELD_KEYS or v is None:
                    continue
                if (
                    normalized := self._get_strict_field_constraint(
                        k, v, is_float_type=is_float_type, is_int_type=is_int_type
                    )
                ) is not None:
                    merge_normalized_constraint(constraint_data, normalized[0], normalized[1])
            data = {**data, **constraint_data}

        if (min_items := data.pop("min_items", None)) is not None:
            data["min_length"] = min_items
        if (max_items := data.pop("max_items", None)) is not None:
            data["max_length"] = max_items

        meta_arguments = sorted(f"{k}={represent_python_value(v)}" for k, v in data.items() if v is not None)
        return f"Meta({', '.join(meta_arguments)})" if meta_arguments else None

    @property
    def annotated(self) -> str | None:  # noqa: PLR0911
        """Get Annotated type hint with Meta constraints.

        For ClassVar fields (discriminator tag_field), ClassVar is required
        regardless of use_annotated setting.
        """
        if self.extras.get("is_classvar"):  # pragma: no cover
            meta = self._get_meta_string()
            if self.use_annotated and meta:
                return f"ClassVar[Annotated[{self.type_hint}, {meta}]]"
            return f"ClassVar[{self.type_hint}]"

        if not self.use_annotated:
            return None

        meta = self._get_meta_string()
        if not meta:
            return None

        if self.required:
            return f"Annotated[{self.type_hint}, {meta}]"

        type_hint = self.data_type.type_hint
        annotated_type = f"Annotated[{type_hint}, {meta}]"
        if self.nullable:  # pragma: no cover
            return annotated_type
        if self.data_type.is_optional:  # pragma: no cover
            return _add_unset_type(annotated_type, self.data_type.use_union_operator)
        return get_neither_required_nor_nullable_type(annotated_type, self.data_type.use_union_operator)

    @property
    def needs_annotated_import(self) -> bool:
        """Check if this field requires the Annotated import.

        ClassVar fields with Meta need Annotated only when use_annotated is True.
        ClassVar fields without Meta don't need Annotated.
        """
        if not self.annotated:
            return False
        if self.extras.get("is_classvar"):  # pragma: no cover
            return self.use_annotated and self._get_meta_string() is not None
        return True

    @property
    def needs_meta_import(self) -> bool:
        """Check if this field requires the Meta import."""
        return self.use_annotated and self._get_meta_string() is not None

    def _get_default_as_struct_model(self) -> str | None:
        """Convert default value to Struct model using msgspec convert."""
        for data_type in self.data_type.data_types or (self.data_type,):
            # TODO: Check nested data_types
            if data_type.is_dict:
                # TODO: Parse dict model for default
                continue
            if data_type.is_list and len(data_type.data_types) == 1:
                data_type_child = data_type.data_types[0]
                if (
                    data_type_child.reference
                    and (isinstance(data_type_child.reference.source, (Struct, TypeAliasBase)))
                    and isinstance(self.default, list)
                ):
                    return (
                        f"lambda: {self._PARSE_METHOD}({represent_python_value(self.default)},  "
                        f"type=list[{data_type_child.alias or data_type_child.reference.source.class_name}])"
                    )
            elif data_type.reference and isinstance(data_type.reference.source, Struct):
                if self.data_type.is_union:
                    if not isinstance(self.default, (dict, list)):
                        continue
                    if isinstance(self.default, dict) and any(dt.is_dict for dt in self.data_type.data_types):
                        continue
                return (
                    f"lambda: {self._PARSE_METHOD}({represent_python_value(self.default)},  "
                    f"type={data_type.alias or data_type.reference.source.class_name})"
                )
        return None

    def _get_default_factory_for_optional_nested_model(self) -> str | None:
        """Get default_factory for optional nested Struct model fields.

        Returns the class name if the field type references a Struct,
        otherwise returns None.
        """
        return _nested_model_default_factory(self, Struct)


class DataTypeManager(_DataTypeManager):
    """Type manager for msgspec Struct models."""


_rebuild_model_with_datamodel_namespace(DataModelField)
