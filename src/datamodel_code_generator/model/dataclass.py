"""Python dataclass model generator.

Generates Python dataclasses using the @dataclass decorator.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Optional, cast

from datamodel_code_generator._format_types import (
    DateClassType,
    DatetimeClassType,
    PythonVersion,
    PythonVersionMin,
)
from datamodel_code_generator.model import DataModel, DataModelFieldBase, _rebuild_model_with_datamodel_namespace
from datamodel_code_generator.model._constraints import Constraints  # noqa: TC001 # needed for pydantic
from datamodel_code_generator.model.base import (
    UNDEFINED,
    TemplateBase,
    _has_field_assignment,
    _nested_model_default_factory,
    get_effective_fields,
)
from datamodel_code_generator.model.imports import IMPORT_DATACLASS, IMPORT_FIELD
from datamodel_code_generator.model.types import DataTypeManager as _DataTypeManager
from datamodel_code_generator.python_literal import represent_python_value
from datamodel_code_generator.reference import Reference
from datamodel_code_generator.types import DataType, StrictTypes, chain_as_tuple

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence

    from datamodel_code_generator.enums import DataclassArguments
    from datamodel_code_generator.imports import Import


def has_field_assignment(field: DataModelFieldBase) -> bool:
    """Check if a dataclass field renders with an assignment or default value."""
    return _has_field_assignment(field)


def get_field_default_info(field: DataModelFieldBase) -> tuple[bool, bool]:
    """Return Python dataclass constructor-default semantics."""
    return field._get_constructor_default_info()  # noqa: SLF001  # output-owned field policy hook


def field_participates_in_constructor(field: DataModelFieldBase) -> bool:
    """Return whether a Python dataclass field participates in __init__."""
    return field.extras.get("init") is not False


def _has_constructor_default(field: DataModelFieldBase) -> bool:
    """Classify a constructor default without recursively rendering structured values."""
    if field.required and not field.use_default_with_required:
        return False
    if field.default is not UNDEFINED and field.default is not None:
        return True
    return get_field_default_info(field)[0]


def _nested_dataclass_sources(data_type: DataType) -> tuple[DataClass, ...]:
    """Return dataclass models referenced by one non-mapping annotation branch."""
    sources: list[DataClass] = []
    for nested_data_type in data_type.data_types or (data_type,):
        if (
            nested_data_type.reference
            and isinstance(source := nested_data_type.reference.source, DataClass)
            and all(source is not existing_source for existing_source in sources)
        ):
            sources.append(source)
    return tuple(sources)


def _has_recursive_nested_mapping_default(
    model: DataClass,
    active_paths: frozenset[str] = frozenset(),
) -> bool:
    """Return whether materializing model defaults would recurse through mapping factories."""
    if model.path in active_paths:
        return True
    active_paths |= {model.path}
    effective_fields = model.fields if not model.base_classes else get_effective_fields(model)
    for field in effective_fields:
        if not field_participates_in_constructor(field) or not isinstance(field.default, dict):
            continue
        data_types = field.data_type.data_types or (field.data_type,)
        if (
            field.data_type.is_dict
            or field.data_type.is_mapping
            or any(data_type.is_dict or data_type.is_mapping for data_type in data_types)
        ):
            continue
        if any(
            _has_recursive_nested_mapping_default(source, active_paths)
            for source in _nested_dataclass_sources(field.data_type)
        ):
            return True
    return False


def _build_nested_dataclass_default_factory(data_type: DataType, default: dict[Any, Any]) -> str | None:
    """Build one valid dataclass constructor factory candidate."""
    if not (data_type.reference and isinstance(source := data_type.reference.source, DataClass)):
        return None
    effective_fields = source.fields if not source.base_classes else get_effective_fields(source)
    field_names: dict[str, str] = {}
    original_names: dict[str, str] | None = None
    required_names: set[str] = set()
    has_nested_mapping_default = False
    for model_field in effective_fields:
        if model_field.name is None or not field_participates_in_constructor(model_field):
            continue
        field_names[model_field.name] = model_field.name
        if model_field.original_name is not None:
            if original_names is None:
                original_names = {}
            original_names[model_field.original_name] = model_field.name
        if not _has_constructor_default(model_field):
            required_names.add(model_field.name)
        has_nested_mapping_default = has_nested_mapping_default or (
            isinstance(model_field.default, dict) and bool(_nested_dataclass_sources(model_field.data_type))
        )
    arguments: list[str] = []
    used_field_names: set[str] | None = set() if len(default) > 1 else None
    for name, value in default.items():
        field_name = original_names.get(name) if original_names is not None else None
        if field_name is None and (field_name := field_names.get(name)) is None:
            return None
        if used_field_names is not None:
            if field_name in used_field_names:
                return None
            used_field_names.add(field_name)
        required_names.discard(field_name)
        arguments.append(f"{field_name}={represent_python_value(value)}")
    if required_names:
        return None
    if has_nested_mapping_default and _has_recursive_nested_mapping_default(source):
        return None
    return f"lambda: {data_type.alias or source.class_name}({', '.join(arguments)})"


_REQUIRED_INHERITED_INIT_KEY = "_required_inherited_init"
_BUILTIN_TEMPLATE_FILE_PATH = "dataclass.jinja2"
_BUILTIN_TEMPLATE_PATH = Path(_BUILTIN_TEMPLATE_FILE_PATH)
# Keep these snapshots synchronized with public render hooks used by the built-in template.
_BUILTIN_RENDER = TemplateBase._render  # noqa: SLF001
_BUILTIN_TEMPLATE = DataModel.template
_BUILTIN_TEMPLATE_FILE_PATH_DESCRIPTOR = DataModel.template_file_path
_BUILTIN_RENDERED_FIELDS = DataModel.rendered_fields
_BUILTIN_DATA_MODEL_RENDER = DataModel.render
_BUILTIN_RENDER_CALL_KEYS: frozenset[str] = frozenset({
    "base_class",
    "class_name",
    "dataclass_arguments",
    "decorators",
    "description",
    "fields",
    "methods",
    "path",
})


def _uses_builtin_dataclass_classes() -> bool:
    """Return whether public class-level rendering hooks remain unchanged."""
    return bool(
        DataClass.TEMPLATE_FILE_PATH == _BUILTIN_TEMPLATE_FILE_PATH
        and DataClass.FORMAT_DESCRIPTION_AS_DOCSTRING is True
        and DataClass._render is _BUILTIN_RENDER  # noqa: SLF001
        and DataClass.template is _BUILTIN_TEMPLATE
        and DataClass.template_file_path is _BUILTIN_TEMPLATE_FILE_PATH_DESCRIPTOR
        and DataClass.rendered_fields is _BUILTIN_RENDERED_FIELDS
        and DataModel.render is _BUILTIN_DATA_MODEL_RENDER
        and DataModelField.field is _BUILTIN_FIELD_RENDERER
        and DataModelField.type_hint is _BUILTIN_FIELD_TYPE_HINT
        and DataModelField.represented_default is _BUILTIN_FIELD_REPRESENTED_DEFAULT
        and DataModelField.docstring is _BUILTIN_FIELD_DOCSTRING
        and DataModelField.inline_field_docstring is _BUILTIN_FIELD_INLINE_DOCSTRING
    )


def _uses_builtin_dataclass_arguments(arguments: object) -> bool:
    """Return whether arguments match the public parser's strict bool mapping."""
    return bool(
        type(arguments) is dict
        and all(type(key) is str and (type(value) is bool or value is None) for key, value in arguments.items())
    )


def _uses_builtin_dataclass_instance(model: DataClass) -> bool:
    """Return whether instance-level custom rendering hooks are inactive."""
    instance_data = model.__dict__
    if type(model.fields) is not list or type(model.decorators) is not list:
        return False
    if type(model.extra_template_data) not in {dict, defaultdict}:
        return False
    template_data_keys = model.extra_template_data.keys()
    return bool(
        model._custom_template_dir is None  # noqa: SLF001
        and instance_data.keys().isdisjoint({"template", "_render"})
        and instance_data.get("template_file_path", _BUILTIN_TEMPLATE_PATH) == _BUILTIN_TEMPLATE_PATH
        and all(type(key) is str for key in template_data_keys)
        and template_data_keys.isdisjoint(_BUILTIN_RENDER_CALL_KEYS)
        and all(type(field) is DataModelField for field in model.fields)
        and _uses_builtin_dataclass_arguments(model.dataclass_arguments)
        and all(type(decorator) is str for decorator in model.decorators)
    )


def _render_builtin_field(field: DataModelField) -> str:
    """Render one standard dataclass field without invoking Jinja."""
    if assignment := field.field:
        return f"    {field.name}: {field.type_hint} = {assignment}"
    rendered = f"    {field.name}: {field.type_hint}"
    represented_default = field.represented_default
    match (
        field.required and not field.use_default_with_required,
        represented_default,
        field.strip_default_none,
    ):
        case (True, _, _) | (False, "None", True):
            return rendered
        case _:
            pass
    return f"{rendered} = {represented_default}"


def _append_builtin_field_docstring(
    lines: list[str],
    model: DataClass,
    field: DataModelField,
    *,
    is_last: bool,
) -> None:
    """Append the built-in template's field docstring layout."""
    if field_docstring := model._format_docstring(field.docstring, model.FIELD_DOCSTRING_INDENT):  # noqa: SLF001
        lines.append(f"    {field_docstring}")
        if field.use_inline_field_description and not is_last:
            lines.extend(("", ""))
        return
    if not (inline_docstring := field.inline_field_docstring):
        return
    lines.append(f"    {inline_docstring}")
    if not is_last:
        lines.extend(("", ""))


class _DataclassReuseMixin:
    def has_keyword_only_definition(self) -> bool:
        """Return whether a dataclass declaration enables keyword-only fields."""
        return bool(cast("DataModel", self).dataclass_arguments.get("kw_only"))

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
    FIELD_DEFAULT_CLASSIFIER = staticmethod(get_field_default_info)
    FIELD_PARTICIPATES_IN_CONSTRUCTOR = staticmethod(field_participates_in_constructor)
    SUPPORTS_TREE_SCOPE_REUSE_MODEL_INHERITANCE: ClassVar[bool] = True
    USES_DATACLASS_ARGUMENTS: ClassVar[bool] = True
    SUPPORTS_REQUIRED_INHERITED_FIELD_ASSIGNMENT: ClassVar[bool] = True
    SUPPORTS_DISCRIMINATOR: ClassVar[bool] = True
    SUPPORTS_INHERITED_DISCRIMINATOR_ENUM: ClassVar[bool] = True
    SUPPORTS_KW_ONLY: ClassVar[bool] = True

    def render(self, *, class_name: str | None = None) -> str:
        """Render standard built-in dataclasses without Jinja dispatch."""
        if (rendered := self._render_builtin(class_name)) is not None:
            return rendered
        return super().render(class_name=class_name)

    def _render_builtin(self, class_name: str | None) -> str | None:
        """Return native built-in output, or None when template semantics are required."""
        if (
            type(self) is not DataClass
            or self.CUSTOM_TEMPLATE_ADAPTER is not None
            or not _uses_builtin_dataclass_classes()
            or not _uses_builtin_dataclass_instance(self)
        ):
            return None

        arguments = [
            f"{key}={value!r}"
            for key, value in self.dataclass_arguments.items()
            if value is not None and value is not False
        ]
        lines = [*self.decorators]
        if lines:
            lines.append("")
        lines.append(f"@dataclass({', '.join(arguments)})" if arguments else "@dataclass")
        resolved_class_name = class_name or self.class_name
        lines.append(
            f"class {resolved_class_name}({base_class}):"
            if (base_class := self.base_class)
            else f"class {resolved_class_name}:"
        )

        if rendered_description := self.rendered_description:
            lines.append(f"    {rendered_description}")
        elif not self.fields:
            lines.append("    pass")

        last_field_index = len(self.fields) - 1
        for index, field in enumerate(self.fields):
            lines.append(_render_builtin_field(field))
            _append_builtin_field_docstring(lines, self, field, is_last=index == last_field_index)

        return ("" if self.decorators else "\n") + "\n".join(lines)

    @classmethod
    def prepare_required_inherited_field(
        cls,
        field: DataModelFieldBase,
        inherited_field: DataModelFieldBase,
        *,
        explicit_extras: Collection[str] = (),
    ) -> None:
        """Preserve inherited init=False until requiredness is final."""
        super().prepare_required_inherited_field(
            field,
            inherited_field,
            explicit_extras=explicit_extras,
        )
        if inherited_field.extras.get("init") is False and "init" not in explicit_extras:
            field.__dict__[_REQUIRED_INHERITED_INIT_KEY] = True

    @classmethod
    def restore_required_inherited_field_state(cls, field: DataModelFieldBase) -> bool:
        """Restore a required field excluded from the inherited constructor."""
        if not (field.required and field.__dict__.pop(_REQUIRED_INHERITED_INIT_KEY, False)):
            return False
        return field.extras.pop("init", None) is False

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

    def _get_default_factory_for_nested_value(self, default: dict[Any, Any]) -> str | None:
        """Render a mapping default as a nested dataclass constructor."""
        if self.data_type.is_dict or self.data_type.is_mapping:
            return None

        data_types = self.data_type.data_types or (self.data_type,)
        if any(data_type.is_dict or data_type.is_mapping for data_type in data_types):
            return None

        default_factory: str | None = None
        for data_type in data_types:
            if (factory := _build_nested_dataclass_default_factory(data_type, default)) is None:
                continue
            if default_factory is not None:
                return None
            default_factory = factory
        return default_factory

    def _get_field_data(self) -> dict[str, Any]:
        """Return structured field() arguments before rendering."""
        data: dict[str, Any] = {k: v for k, v in self.extras.items() if k in self._FIELD_KEYS}

        needs_nested_factory = (
            self.use_default_factory_for_optional_nested_models
            and not self.required
            and (self.default is None or self.default is UNDEFINED)
            and "default_factory" not in data
        )
        if needs_nested_factory and (nested_model_name := self._get_default_factory_for_nested_model()):
            data["default_factory"] = nested_model_name

        if self.default is None:
            if data and "default_factory" not in data and (not self.strip_default_none or data.get("init") is False):
                data["default"] = None
        elif self.default != UNDEFINED and "default_factory" not in data:
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

        match data.get("default", UNDEFINED):
            case dict() as default if nested_factory := self._get_default_factory_for_nested_value(default):
                data.pop("default")
                data["default_factory"] = nested_factory
            case list() | dict() | set() as default:
                data.pop("default")
                data["default_factory"] = (
                    f"lambda: {represent_python_value(default)}" if default else type(default).__name__
                )

        return data

    def _get_constructor_default_info(self) -> tuple[bool, bool]:
        """Return constructor-default semantics from structured field data."""
        if self.required and not self.use_default_with_required:
            return False, False
        data = self._get_field_data()
        has_rendered_assignment = bool(data) or self._has_forced_field_assignment
        if (not data and self._has_forced_field_assignment) or not (
            (has_rendered_assignment and not self.use_annotated) or not self.should_strip_default_none()
        ):
            return False, False
        if "default_factory" in data:
            return True, False
        if data and "default" not in data:
            return False, False
        return True, True

    def __str__(self) -> str:
        """Generate field() call or default value representation."""
        data = self._get_field_data()
        if not data:
            return "field()" if self._has_forced_field_assignment else ""

        if len(data) == 1 and "default" in data:
            return represent_python_value(data["default"])
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


_BUILTIN_FIELD_RENDERER = DataModelField.field
_BUILTIN_FIELD_TYPE_HINT = DataModelField.type_hint
_BUILTIN_FIELD_REPRESENTED_DEFAULT = DataModelField.represented_default
_BUILTIN_FIELD_DOCSTRING = DataModelField.docstring
_BUILTIN_FIELD_INLINE_DOCSTRING = DataModelField.inline_field_docstring

_rebuild_model_with_datamodel_namespace(DataModelField)
