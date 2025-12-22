"""msgspec.Struct model generator.

Generates Python models using msgspec.Struct for high-performance serialization.
"""

from __future__ import annotations

from functools import lru_cache, wraps
from typing import TYPE_CHECKING, Any, ClassVar, Optional, TypeVar

from pydantic import Field

from datamodel_code_generator import DateClassType, DatetimeClassType, PythonVersion, PythonVersionMin
from datamodel_code_generator.imports import (
    IMPORT_DATE,
    IMPORT_DATETIME,
    IMPORT_TIME,
    IMPORT_TIMEDELTA,
    IMPORT_UNION,
    Import,
)
from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.model.base import UNDEFINED, BaseClassDataType
from datamodel_code_generator.model.imports import (
    IMPORT_MSGSPEC_CONVERT,
    IMPORT_MSGSPEC_FIELD,
    IMPORT_MSGSPEC_META,
    IMPORT_MSGSPEC_STRUCT,
    IMPORT_MSGSPEC_UNSET,
    IMPORT_MSGSPEC_UNSETTYPE,
)
from datamodel_code_generator.model.pydantic.base_model import (
    Constraints as _Constraints,
)
from datamodel_code_generator.model.type_alias import TypeAliasBase
from datamodel_code_generator.model.types import DataTypeManager as _DataTypeManager
from datamodel_code_generator.model.types import standard_primitive_type_map_factory, type_map_factory
from datamodel_code_generator.types import (
    NONE,
    OPTIONAL_PREFIX,
    UNION_DELIMITER,
    UNION_OPERATOR_DELIMITER,
    UNION_PREFIX,
    DataType,
    StrictTypes,
    Types,
    _remove_none_from_union,
    chain_as_tuple,
)
from datamodel_code_generator.util import model_dump

UNSET_TYPE = "UnsetType"


class _UNSET:
    def __str__(self) -> str:
        return "UNSET"

    __repr__ = __str__


UNSET = _UNSET()


if TYPE_CHECKING:
    from collections import defaultdict
    from collections.abc import Sequence
    from pathlib import Path

    from datamodel_code_generator.reference import Reference


def _has_field_assignment(field: DataModelFieldBase) -> bool:
    return not (field.required or (field.represented_default == "None" and field.strip_default_none))


DataModelFieldBaseT = TypeVar("DataModelFieldBaseT", bound=DataModelFieldBase)


def import_extender(cls: type[DataModelFieldBaseT]) -> type[DataModelFieldBaseT]:
    """Extend imports property with msgspec-specific imports."""
    original_imports: property = cls.imports

    @wraps(original_imports.fget)  # pyright: ignore[reportArgumentType]
    def new_imports(self: DataModelFieldBaseT) -> tuple[Import, ...]:
        if self.extras.get("is_classvar"):
            return ()
        extra_imports = []
        field = self.field
        # TODO: Improve field detection
        if field and field.startswith("field("):
            extra_imports.append(IMPORT_MSGSPEC_FIELD)
        if self.field and "lambda: convert" in self.field:
            extra_imports.append(IMPORT_MSGSPEC_CONVERT)
        if isinstance(self, DataModelField) and self.needs_meta_import:
            extra_imports.append(IMPORT_MSGSPEC_META)
        if not self.required and not self.nullable:
            extra_imports.append(IMPORT_MSGSPEC_UNSETTYPE)
            if not self.data_type.use_union_operator:
                extra_imports.append(IMPORT_UNION)
            if self.default is None or self.default is UNDEFINED:
                extra_imports.append(IMPORT_MSGSPEC_UNSET)
        return chain_as_tuple(original_imports.fget(self), extra_imports)  # pyright: ignore[reportOptionalCall]

    cls.imports = property(new_imports)  # pyright: ignore[reportAttributeAccessIssue]
    return cls


class Struct(DataModel):
    """DataModel implementation for msgspec.Struct."""

    TEMPLATE_FILE_PATH: ClassVar[str] = "msgspec.jinja2"
    BASE_CLASS: ClassVar[str] = "msgspec.Struct"
    BASE_CLASS_NAME: ClassVar[str] = "Struct"
    BASE_CLASS_ALIAS: ClassVar[str] = "_Struct"
    DEFAULT_IMPORTS: ClassVar[tuple[Import, ...]] = ()
    SUPPORTS_DISCRIMINATOR: ClassVar[bool] = True
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
        custom_base_class: str | None = None,
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
            fields=sorted(fields, key=_has_field_assignment),
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

    # To override existing pattern alias
    regex: Optional[str] = Field(None, alias="regex")  # noqa: UP045
    pattern: Optional[str] = Field(None, alias="pattern")  # noqa: UP045


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
    if type_.startswith(UNION_PREFIX):
        return f"{type_[:-1]}{UNION_DELIMITER}{UNSET_TYPE}]"
    if type_.startswith(OPTIONAL_PREFIX):  # pragma: no cover
        inner_type = type_[len(OPTIONAL_PREFIX) : -1]
        return f"{UNION_PREFIX}{inner_type}{UNION_DELIMITER}{NONE}{UNION_DELIMITER}{UNSET_TYPE}]"
    return f"{UNION_PREFIX}{type_}{UNION_DELIMITER}{UNSET_TYPE}]"


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
        # 'min_items', # not supported by msgspec
        # 'max_items', # not supported by msgspec
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
        if self.data_type.type == "str" and isinstance(const, str):  # pragma: no cover # Literal supports only str
            self.replace_data_type(self.data_type.__class__(literals=[const]), clear_old_parent=False)

    def _get_strict_field_constraint_value(self, constraint: str, value: Any) -> Any:
        """Get constraint value with appropriate numeric type."""
        if value is None or constraint not in self._COMPARE_EXPRESSIONS:
            return value

        if any(data_type.type == "float" for data_type in self.data_type.all_data_types):
            return float(value)
        return int(value)

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
        elif self.default and "default_factory" not in data:
            default_factory = self._get_default_as_struct_model()
            if default_factory is not None:
                data.pop("default")
                data["default_factory"] = default_factory

        if "default" in data and isinstance(data["default"], (list, dict, set)) and "default_factory" not in data:
            default_value = data.pop("default")
            if default_value:
                from datamodel_code_generator.model.base import repr_set_sorted  # noqa: PLC0415

                default_repr = repr_set_sorted(default_value) if isinstance(default_value, set) else repr(default_value)
                data["default_factory"] = f"lambda: {default_repr}"
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
            return repr(data["default"])

        kwargs = [f"{k}={v if k == 'default_factory' else repr(v)}" for k, v in data.items()]
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
            data = {
                **data,
                **{
                    k: self._get_strict_field_constraint_value(k, v)
                    for k, v in model_dump(self.constraints).items()
                    if k in self._META_FIELD_KEYS
                },
            }

        meta_arguments = sorted(f"{k}={v!r}" for k, v in data.items() if v is not None)
        return f"Meta({', '.join(meta_arguments)})" if meta_arguments else None

    @property
    def annotated(self) -> str | None:  # noqa: PLR0911
        """Get Annotated type hint with Meta constraints.

        For ClassVar fields (discriminator tag_field), ClassVar is required
        regardless of use_annotated setting.
        """
        if self.extras.get("is_classvar"):
            meta = self._get_meta_string()
            if self.use_annotated and meta:
                return f"ClassVar[Annotated[{self.type_hint}, {meta}]]"
            return f"ClassVar[{self.type_hint}]"

        if not self.use_annotated:  # pragma: no cover
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
        if self.extras.get("is_classvar"):
            return self.use_annotated and self._get_meta_string() is not None
        return True

    @property
    def needs_meta_import(self) -> bool:
        """Check if this field requires the Meta import."""
        return self._get_meta_string() is not None

    def _get_default_as_struct_model(self) -> str | None:
        """Convert default value to Struct model using msgspec convert."""
        for data_type in self.data_type.data_types or (self.data_type,):
            # TODO: Check nested data_types
            if data_type.is_dict:
                # TODO: Parse dict model for default
                continue  # pragma: no cover
            if data_type.is_list and len(data_type.data_types) == 1:
                data_type_child = data_type.data_types[0]
                if (  # pragma: no cover
                    data_type_child.reference
                    and (isinstance(data_type_child.reference.source, (Struct, TypeAliasBase)))
                    and isinstance(self.default, list)
                ):
                    return (
                        f"lambda: {self._PARSE_METHOD}({self.default!r},  "
                        f"type=list[{data_type_child.alias or data_type_child.reference.source.class_name}])"
                    )
            elif data_type.reference and isinstance(data_type.reference.source, Struct):
                if self.data_type.is_union:
                    if not isinstance(self.default, (dict, list)):
                        continue
                    if isinstance(self.default, dict) and any(dt.is_dict for dt in self.data_type.data_types):
                        continue
                return (
                    f"lambda: {self._PARSE_METHOD}({self.default!r},  "
                    f"type={data_type.alias or data_type.reference.source.class_name})"
                )
        return None

    def _get_default_factory_for_optional_nested_model(self) -> str | None:
        """Get default_factory for optional nested Struct model fields.

        Returns the class name if the field type references a Struct,
        otherwise returns None.
        """
        for data_type in self.data_type.data_types or (self.data_type,):
            if data_type.is_dict:
                continue
            if data_type.reference and isinstance(data_type.reference.source, Struct):
                return data_type.alias or data_type.reference.source.class_name
        return None


class DataTypeManager(_DataTypeManager):
    """Type manager for msgspec Struct models."""

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
        target_datetime_class: DatetimeClassType | None = None,
        target_date_class: DateClassType | None = None,  # noqa: ARG002
        treat_dot_as_module: bool | None = None,  # noqa: FBT001
        use_serialize_as_any: bool = False,  # noqa: FBT001, FBT002
    ) -> None:
        """Initialize type manager with optional datetime type mapping."""
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
