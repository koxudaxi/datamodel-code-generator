"""msgspec.Struct model generator.

Generates Python models using msgspec.Struct for high-performance serialization.
"""

from __future__ import annotations

from functools import wraps
from math import isfinite
from typing import TYPE_CHECKING, Any, ClassVar, Optional, TypeVar

from datamodel_code_generator.imports import IMPORT_OPTIONAL, Import
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
    chain_as_tuple,
    merge_normalized_constraint,
    normalize_integer_constraint,
)


class _UNSET:
    def __str__(self) -> str:
        return "UNSET"

    __repr__ = __str__


UNSET = _UNSET()


if TYPE_CHECKING:
    from collections import defaultdict
    from pathlib import Path

    from datamodel_code_generator.reference import Reference
    from datamodel_code_generator.types import DataType


def has_field_assignment(field: DataModelFieldBase) -> bool:
    """Return whether a msgspec field renders with a default assignment."""
    return field.use_default_with_required or not (field.required or field.should_strip_default_none())


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
        if not self.required and not self.nullable and (self.default is None or self.default is UNDEFINED):
            extra_imports.append(IMPORT_MSGSPEC_UNSET)
        imports = original_imports.fget(self)  # ty: ignore
        if (
            isinstance(self, DataModelField)
            and self._not_required
            and not self.nullable
            and self.data_type.is_optional
            and not self._uses_optional_inside_annotated_unset
        ):
            imports = tuple(import_ for import_ in imports if import_ != IMPORT_OPTIONAL)
        return chain_as_tuple(imports, extra_imports)

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

    def _unset_type_data_type(self) -> DataType:
        return self.data_type.__class__.from_import(IMPORT_MSGSPEC_UNSETTYPE)

    def _ordered_union_data_type(self, data_types: list[DataType]) -> DataType:
        if len(data_types) == 1:
            return data_types[0]
        return self.data_type.__class__(
            data_types=data_types,
            use_union_operator=self.data_type.use_union_operator,
            preserve_union_member_order=True,
        )

    def _data_type_has_top_level_none(self, data_type: DataType) -> bool:
        if data_type.is_optional or self._data_type_renders_none(data_type):
            return True
        if not data_type.is_union:
            return False
        return any(self._data_type_renders_none(child) for child in data_type.data_types)

    @staticmethod
    def _data_type_has_container(data_type: DataType) -> bool:
        return any((
            data_type.is_dict,
            data_type.is_list,
            data_type.is_set,
            data_type.is_frozen_set,
            data_type.is_mapping,
            data_type.is_sequence,
            data_type.is_tuple,
        ))

    def _data_type_is_plain_union(self, data_type: DataType) -> bool:
        return data_type.is_union and not self._data_type_has_container(data_type)

    def _copy_data_type(self, data_type: DataType) -> DataType:
        copied = data_type.model_copy()
        copied.parent = None
        copied.children = []
        copied.data_types = [self._copy_data_type(child) for child in data_type.data_types]
        copied.literals = list(data_type.literals)
        copied.enum_member_literals = list(data_type.enum_member_literals)
        if data_type.dict_key:
            copied.dict_key = self._copy_data_type(data_type.dict_key)
        if data_type.kwargs:
            copied.kwargs = dict(data_type.kwargs)
        return copied

    def _copy_data_type_without_top_level_none(self, data_type: DataType) -> DataType:
        data_type = self._copy_data_type(data_type)
        data_type.is_optional = False
        if data_type.is_union:
            data_type.data_types = [child for child in data_type.data_types if not self._data_type_renders_none(child)]
        return data_type

    def _unset_union_data_type(self) -> DataType:
        unset_type = self._unset_type_data_type()
        if self._data_type_renders_none(self.data_type):
            return unset_type

        data_types = []
        has_none = self._data_type_has_top_level_none(self.data_type)
        if not has_none and self._data_type_is_plain_union(self.data_type):
            data_types.extend(self._copy_data_type(child) for child in self.data_type.data_types)
        elif has_none:
            base_data_type = self._copy_data_type_without_top_level_none(self.data_type)
            if self._data_type_has_renderable_structure(base_data_type) and not self._data_type_renders_none(
                base_data_type
            ):
                data_types.append(base_data_type)
        else:
            base_data_type = self._copy_data_type(self.data_type)
            if self._data_type_has_renderable_structure(base_data_type) and not self._data_type_renders_none(
                base_data_type
            ):
                data_types.append(base_data_type)
        if has_none:
            data_types.append(self.data_type.__class__(type=NONE))
        data_types.append(unset_type)
        return self._ordered_union_data_type(data_types)

    def _annotated_type_hint(self, meta: str) -> str:
        return f"Annotated[{self.data_type.type_hint}, {meta}]"

    def _annotated_data_type(self, annotated_type: str) -> DataType:
        return self.data_type.__class__(
            type=annotated_type,
            data_types=[self._copy_data_type(self.data_type)],
            use_union_operator=self.data_type.use_union_operator,
        )

    def _annotated_unset_union_data_type(self, annotated_type: str) -> DataType:
        return self._ordered_union_data_type([self._annotated_data_type(annotated_type), self._unset_type_data_type()])

    def _type_hint_data_type(self) -> DataType:
        if self._not_required and not self.nullable:
            return self._unset_union_data_type()
        return self.data_type

    def _imports_data_type(self) -> DataType:
        if not (self._not_required and not self.nullable and self.use_annotated):
            return self._type_hint_data_type()
        if (meta := self._get_meta_string()) is None:
            return self._type_hint_data_type()
        return self._annotated_unset_union_data_type(self._annotated_type_hint(meta))

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
        if self._not_required and not self.nullable:
            return self._unset_union_data_type().type_hint
        return super().type_hint

    @property
    def imports(self) -> tuple[Import, ...]:
        """Get imports from the structurally rendered msgspec annotation."""
        return self._collect_field_imports(
            needs_annotated=self.use_annotated and self.needs_annotated_import,
            data_type=self._imports_data_type(),
        )

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

        annotated_type = self._annotated_type_hint(meta)
        if self.nullable:  # pragma: no cover
            return annotated_type
        return self._annotated_unset_union_data_type(annotated_type).type_hint

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

    @property
    def _uses_optional_inside_annotated_unset(self) -> bool:
        return self.needs_meta_import and not self.data_type.use_union_operator

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
