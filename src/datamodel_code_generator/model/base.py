"""Base classes for data model generation.

Provides ConstraintsBase for field constraints, DataModelFieldBase for field
representation, and DataModel as the abstract base for all model types.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections import defaultdict
from copy import deepcopy
from functools import cached_property, lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Optional, TypeVar, Union
from warnings import warn

from pydantic import Field
from typing_extensions import Self

from datamodel_code_generator import cached_path_exists
from datamodel_code_generator.imports import (
    IMPORT_ANNOTATED,
    IMPORT_OPTIONAL,
    IMPORT_UNION,
    Import,
)
from datamodel_code_generator.model._types import WrappedDefault
from datamodel_code_generator.reference import Reference, _BaseModel
from datamodel_code_generator.types import (
    ANY,
    NONE,
    OPTIONAL_PREFIX,
    UNION_PREFIX,
    DataType,
    Nullable,
    chain_as_tuple,
    get_optional_type,
)
from datamodel_code_generator.util import ConfigDict, is_pydantic_v2, model_copy, model_dump, model_validate

__all__ = ["WrappedDefault"]

if TYPE_CHECKING:
    from collections.abc import Iterator

    from jinja2 import Environment, Template

    from datamodel_code_generator import DataclassArguments

TEMPLATE_DIR: Path = Path(__file__).parents[0] / "template"


def escape_docstring(value: str | None) -> str | None:
    r"""Escape special characters in a docstring to prevent syntax errors.

    Handles:
    - Backslashes: `\\` -> `\\\\` (must be escaped first)
    - Triple quotes: `\"\"\"` -> `\\\"\\\"\\\"` (would terminate docstring)

    Args:
        value: The string to escape, or None.

    Returns:
        The escaped string, or None if input was None.
    """
    if value is None:
        return None
    # Escape backslashes first, then triple quotes
    return value.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')


ALL_MODEL: str = "#all#"
GENERIC_BASE_CLASS_PATH: str = "#/__datamodel_code_generator__/generic_base_class__"
GENERIC_BASE_CLASS_NAME: str = "__generic_base_class__"


def _copy_all_model_data(source: dict[str, Any], target: dict[str, Any]) -> None:
    """Copy ALL_MODEL data to target dict, deep copying mutable containers only."""
    for key, value in source.items():
        target[key] = deepcopy(value) if isinstance(value, (dict, list, set)) else value


def repr_set_sorted(value: set[Any]) -> str:
    """Return a repr of a set with elements sorted for consistent output.

    Uses (type_name, repr(x)) as sort key to safely handle any type including
    Enum, custom classes, or types without __lt__ defined.
    """
    if not value:
        return "set()"
    # Sort by type name first, then by repr for consistent output
    sorted_elements = sorted(value, key=lambda x: (type(x).__name__, repr(x)))
    return "{" + ", ".join(repr(e) for e in sorted_elements) + "}"


ConstraintsBaseT = TypeVar("ConstraintsBaseT", bound="ConstraintsBase")
DataModelFieldBaseT = TypeVar("DataModelFieldBaseT", bound="DataModelFieldBase")


class ConstraintsBase(_BaseModel):
    """Base class for field constraints (min/max, patterns, etc.)."""

    unique_items: Optional[bool] = Field(None, alias="uniqueItems")  # noqa: UP045
    _exclude_fields: ClassVar[set[str]] = {"has_constraints"}
    if is_pydantic_v2():
        model_config = ConfigDict(  # pyright: ignore[reportAssignmentType]
            arbitrary_types_allowed=True, ignored_types=(cached_property,)
        )
    else:

        class Config:
            """Pydantic v1 configuration for ConstraintsBase."""

            arbitrary_types_allowed = True
            keep_untouched = (cached_property,)

    @cached_property
    def has_constraints(self) -> bool:
        """Check if any constraint values are set."""
        return any(v is not None for v in model_dump(self).values())

    @staticmethod
    def merge_constraints(a: ConstraintsBaseT | None, b: ConstraintsBaseT | None) -> ConstraintsBaseT | None:
        """Merge two constraint objects, with b taking precedence over a."""
        constraints_class = None
        if isinstance(a, ConstraintsBase):  # pragma: no cover
            root_type_field_constraints = {k: v for k, v in model_dump(a, by_alias=True).items() if v is not None}
            constraints_class = a.__class__
        else:
            root_type_field_constraints = {}  # pragma: no cover

        if isinstance(b, ConstraintsBase):  # pragma: no cover
            model_field_constraints = {k: v for k, v in model_dump(b, by_alias=True).items() if v is not None}
            constraints_class = constraints_class or b.__class__
        else:
            model_field_constraints = {}

        if constraints_class is None or not issubclass(constraints_class, ConstraintsBase):  # pragma: no cover
            return None

        return model_validate(
            constraints_class,
            {
                **root_type_field_constraints,
                **model_field_constraints,
            },
        )


class DataModelFieldBase(_BaseModel):
    """Base class for model field representation and rendering."""

    if is_pydantic_v2():
        model_config = ConfigDict(  # pyright: ignore[reportAssignmentType]
            arbitrary_types_allowed=True,
            defer_build=True,
        )
    else:

        class Config:
            """Pydantic v1 configuration for DataModelFieldBase."""

            arbitrary_types_allowed = True

    name: Optional[str] = None  # noqa: UP045
    default: Optional[Any] = None  # noqa: UP045
    required: bool = False
    alias: Optional[str] = None  # noqa: UP045
    data_type: DataType
    constraints: Any = None
    strip_default_none: bool = False
    nullable: Optional[bool] = None  # noqa: UP045
    parent: Optional[DataModel] = None  # noqa: UP045
    extras: dict[str, Any] = Field(default_factory=dict)
    use_annotated: bool = False
    use_serialize_as_any: bool = False
    has_default: bool = False
    use_field_description: bool = False
    use_field_description_example: bool = False
    use_inline_field_description: bool = False
    const: bool = False
    original_name: Optional[str] = None  # noqa: UP045
    use_default_kwarg: bool = False
    use_one_literal_as_default: bool = False
    _exclude_fields: ClassVar[set[str]] = {"parent"}
    _pass_fields: ClassVar[set[str]] = {"parent", "data_type"}
    can_have_extra_keys: ClassVar[bool] = True
    type_has_null: Optional[bool] = None  # noqa: UP045
    read_only: bool = False
    write_only: bool = False
    use_frozen_field: bool = False
    use_default_factory_for_optional_nested_models: bool = False

    if not TYPE_CHECKING:  # pragma: no branch
        if not is_pydantic_v2():

            @classmethod
            def model_rebuild(
                cls,
                *,
                _types_namespace: dict[str, type] | None = None,
            ) -> None:
                """Update forward references for Pydantic v1."""
                localns = _types_namespace or {}
                cls.update_forward_refs(**localns)

        def __init__(self, **data: Any) -> None:
            """Initialize the field and set up parent relationships."""
            super().__init__(**data)
            if self.data_type.reference or self.data_type.data_types:
                self.data_type.parent = self
            self.process_const()

    def process_const(self) -> None:
        """Process const values by setting them as defaults."""
        if "const" not in self.extras:
            return
        self.default = self.extras["const"]
        self.const = True
        self.required = False
        self.nullable = False

    def _process_const_as_literal(self) -> None:
        """Process const values by converting to literal type. Used by subclasses."""
        if "const" not in self.extras:
            return
        const = self.extras["const"]
        self.const = True
        self.nullable = False
        self.replace_data_type(self.data_type.__class__(literals=[const]), clear_old_parent=False)
        if not self.default:
            self.default = const

    def self_reference(self) -> bool:
        """Check if field references its parent model.

        Result is cached after first call since parent is stable at render time.
        Uses __dict__ for caching to avoid Pydantic v1 field assignment restrictions.
        """
        if "_self_reference_cache" in self.__dict__:
            return self.__dict__["_self_reference_cache"]
        if self.parent is None or not self.parent.reference:  # pragma: no cover
            self.__dict__["_self_reference_cache"] = False
            return False
        result = self.parent.reference.path in {d.reference.path for d in self.data_type.all_data_types if d.reference}
        self.__dict__["_self_reference_cache"] = result
        return result

    @property
    def _use_union_operator(self) -> bool:
        """Get effective use_union_operator considering parent model's forward reference."""
        if self.parent and self.parent.has_forward_reference:
            return False
        return self.data_type.use_union_operator

    def _build_union_type_hint(self) -> str | None:
        """Build Union[] type hint from data_type.data_types if forward reference requires it."""
        if not (self._use_union_operator != self.data_type.use_union_operator and self.data_type.is_union):
            return None
        parts = [dt.type_hint for dt in self.data_type.data_types if dt.type_hint]
        if len(parts) > 1:
            return f"Union[{', '.join(parts)}]"
        return None  # pragma: no cover

    def _build_base_union_type_hint(self) -> str | None:  # pragma: no cover
        """Build Union[] base type hint from data_type.data_types if forward reference requires it."""
        if not (self._use_union_operator != self.data_type.use_union_operator and self.data_type.is_union):
            return None
        parts = [dt.base_type_hint for dt in self.data_type.data_types if dt.base_type_hint]
        if len(parts) > 1:
            return f"Union[{', '.join(parts)}]"
        return None

    @property
    def type_hint(self) -> str:  # noqa: PLR0911
        """Get the type hint string for this field, including nullability."""
        type_hint = self._build_union_type_hint() or self.data_type.type_hint

        if not type_hint:
            return NONE
        if self.has_default_factory or (self.data_type.is_optional and self.data_type.type != ANY):
            return type_hint
        if self.nullable is not None:
            if self.nullable:
                return get_optional_type(type_hint, self._use_union_operator)
            return type_hint
        if self.required:
            if self.type_has_null:
                return get_optional_type(type_hint, self._use_union_operator)
            return type_hint
        if self.fall_back_to_nullable:
            return get_optional_type(type_hint, self._use_union_operator)
        return type_hint

    @property
    def base_type_hint(self) -> str:
        """Get the base type hint without constrained type kwargs.

        This returns the type without kwargs (e.g., 'str' instead of 'constr(pattern=...)').
        Used in RootModel generics when regex_engine config is needed for lookaround patterns.
        """
        base_hint = self._build_base_union_type_hint() or self.data_type.base_type_hint

        if not base_hint:  # pragma: no cover
            return NONE

        needs_optional = (
            (self.nullable is True)
            or (self.required and self.type_has_null)
            or (self.nullable is None and not self.required and self.fall_back_to_nullable)
        )
        skip_optional = (
            self.has_default_factory
            or (self.data_type.is_optional and self.data_type.type != ANY)
            or (self.nullable is False)
        )

        if needs_optional and not skip_optional:  # pragma: no cover
            return get_optional_type(base_hint, self._use_union_operator)
        return base_hint

    @property
    def imports(self) -> tuple[Import, ...]:
        """Get all imports required for this field's type hint."""
        type_hint = self.type_hint
        has_union = not self._use_union_operator and UNION_PREFIX in type_hint
        has_optional = OPTIONAL_PREFIX in type_hint
        needs_annotated = self.use_annotated and self.needs_annotated_import

        # Fast path: no special typing imports needed
        if not has_union and not has_optional and not needs_annotated:
            return tuple(self.data_type.all_imports)

        imports: list[tuple[Import] | Iterator[Import]] = [
            iter(
                i
                for i in self.data_type.all_imports
                if not ((not has_union and i == IMPORT_UNION) or (not has_optional and i == IMPORT_OPTIONAL))
            )
        ]

        if has_union:
            imports.append((IMPORT_UNION,))
        if has_optional:
            imports.append((IMPORT_OPTIONAL,))
        if needs_annotated:
            imports.append((IMPORT_ANNOTATED,))
        return chain_as_tuple(*imports)

    @property
    def docstring(self) -> str | None:
        """Get the docstring for this field from its description and/or example."""
        parts = []

        if self.use_field_description:
            description = self.extras.get("description")
            if description is not None:
                parts.append(description)
        elif self.use_inline_field_description and self.use_field_description_example:
            description = self.extras.get("description")
            if description is not None and "\n" in description:
                parts.append(description)

        if self.use_field_description_example:
            example = self.extras.get("example")
            examples = self.extras.get("examples")

            if examples and isinstance(examples, list) and len(examples) > 1:
                examples_str = "\n".join(f"- {e!r}" for e in examples)
                parts.append(f"Examples:\n{examples_str}")
            elif example is not None:
                parts.append(f"Example: {example!r}")
            elif examples and isinstance(examples, list) and len(examples) == 1:
                parts.append(f"Example: {examples[0]!r}")

        if parts:
            return "\n\n".join(parts)

        if self.use_inline_field_description:
            description = self.extras.get("description")
            if description is not None and "\n" in description:
                return description

        return None

    @property
    def inline_field_docstring(self) -> str | None:
        """Get the inline docstring for this field if single-line."""
        if self.use_inline_field_description:
            description = self.extras.get("description", None)
            if description is not None and "\n" not in description:
                escaped = escape_docstring(description)
                return f'"""{escaped}"""'
        return None

    @property
    def unresolved_types(self) -> frozenset[str]:
        """Get the set of unresolved type references."""
        return self.data_type.unresolved_types

    @property
    def field(self) -> str | None:
        """For backwards compatibility."""
        return None

    @property
    def method(self) -> str | None:
        """Get the method string for this field, if any."""
        return None

    @property
    def represented_default(self) -> str:
        """Get the repr() string of the default value."""
        if isinstance(self.default, set):
            return repr_set_sorted(self.default)
        return repr(self.default)

    @property
    def annotated(self) -> str | None:
        """Get the Annotated type hint content, if any."""
        return None

    @property
    def needs_annotated_import(self) -> bool:
        """Check if this field requires the Annotated import."""
        return bool(self.annotated)

    @property
    def needs_meta_import(self) -> bool:  # pragma: no cover
        """Check if this field requires the Meta import (msgspec only)."""
        return False

    @property
    def has_default_factory(self) -> bool:
        """Check if this field has a default_factory."""
        return "default_factory" in self.extras

    @property
    def fall_back_to_nullable(self) -> bool:
        """Check if optional fields should be nullable by default."""
        return True

    def copy_deep(self) -> Self:
        """Create a deep copy of this field to avoid mutating the original."""
        copied = model_copy(self)
        copied.parent = None
        copied.extras = deepcopy(self.extras)
        copied.data_type = model_copy(self.data_type)
        if self.data_type.data_types:
            copied.data_type.data_types = [model_copy(dt) for dt in self.data_type.data_types]
        if self.data_type.dict_key:
            copied.data_type.dict_key = model_copy(self.data_type.dict_key)
        return copied

    def replace_data_type(self, new_data_type: DataType, *, clear_old_parent: bool = True) -> None:
        """Replace data_type and update parent relationships.

        Args:
            new_data_type: The new DataType to set.
            clear_old_parent: If True, clear the old data_type's parent reference.
                Set to False when the old data_type may be referenced elsewhere.
        """
        if self.data_type.parent is self and clear_old_parent:
            self.data_type.swap_with(new_data_type)
        else:
            self.data_type = new_data_type
            new_data_type.parent = self


@lru_cache(maxsize=16)
def _get_environment(template_subdir: Path, custom_template_dir: Path | None) -> Environment:
    """Get or create a cached Jinja2 Environment for the given directories."""
    from jinja2 import ChoiceLoader, Environment, FileSystemLoader, select_autoescape  # noqa: PLC0415

    loaders: list[FileSystemLoader] = []

    if custom_template_dir is not None:
        custom_dir = custom_template_dir / template_subdir
        if cached_path_exists(custom_dir):
            loaders.append(FileSystemLoader(str(custom_dir)))

    loaders.append(FileSystemLoader(str(TEMPLATE_DIR / template_subdir)))

    loader: ChoiceLoader | FileSystemLoader = ChoiceLoader(loaders) if len(loaders) > 1 else loaders[0]
    env = Environment(
        loader=loader,
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["escape_docstring"] = escape_docstring
    return env


@lru_cache
def _get_template_with_custom_dir(template_file_path: Path, custom_template_dir: Path | None) -> Template:
    """Load and cache a Jinja2 template with optional custom directory support.

    When custom_template_dir is provided, templates are searched in this order:
    1. custom_template_dir/<template_subdir>/
    2. TEMPLATE_DIR/<template_subdir>/ (fallback)

    This allows users to override individual templates (including included ones)
    while keeping other templates from the default directory.
    """
    template_subdir = template_file_path.parent
    environment = _get_environment(template_subdir, custom_template_dir)
    return environment.get_template(template_file_path.name)


@lru_cache(maxsize=16)
def _get_environment_with_absolute_path(absolute_template_dir: Path, builtin_subdir: Path) -> Environment:
    """Get or create a cached Jinja2 Environment for absolute path templates."""
    from jinja2 import ChoiceLoader, Environment, FileSystemLoader, select_autoescape  # noqa: PLC0415

    loaders: list[FileSystemLoader] = [
        FileSystemLoader(str(absolute_template_dir)),
        FileSystemLoader(str(TEMPLATE_DIR / builtin_subdir)),
    ]
    env = Environment(
        loader=ChoiceLoader(loaders),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["escape_docstring"] = escape_docstring
    return env


@lru_cache
def _get_template_with_absolute_path(absolute_template_path: Path, builtin_subdir: Path) -> Template:
    """Load a Jinja2 template from an absolute path with fallback to built-in directory.

    This handles backward compatibility for custom templates found at absolute paths.
    Includes are searched in this order:
    1. The directory containing the absolute template path
    2. TEMPLATE_DIR/<builtin_subdir>/ (fallback for includes not in custom dir)
    """
    environment = _get_environment_with_absolute_path(absolute_template_path.parent, builtin_subdir)
    return environment.get_template(absolute_template_path.name)


@lru_cache
def get_template(template_file_path: Path) -> Template:
    """Load and cache a Jinja2 template from the template directory."""
    return _get_template_with_custom_dir(template_file_path, None)


def sanitize_module_name(name: str, *, treat_dot_as_module: bool | None) -> str:
    """Sanitize a module name by replacing invalid characters.

    If treat_dot_as_module is True, dots are preserved in the name.
    If treat_dot_as_module is False or None (default), dots are replaced with underscores.
    """
    pattern = r"[^0-9a-zA-Z_.]" if treat_dot_as_module else r"[^0-9a-zA-Z_]"
    sanitized = re.sub(pattern, "_", name)
    if sanitized and sanitized[0].isdigit():
        sanitized = f"_{sanitized}"
    return sanitized


def get_module_path(name: str, file_path: Path | None, *, treat_dot_as_module: bool | None) -> list[str]:
    """Get the module path components from a name and file path.

    The treat_dot_as_module flag controls behavior:
    - None (default): Split names on dots (backward compat), but sanitize file names (replace dots)
    - True: Split names on dots AND keep dots in file names (for modular output)
    - False: Don't split names on dots AND sanitize file names (new feature for flat output)
    """
    should_split_names = treat_dot_as_module is not False
    should_keep_dots_in_files = treat_dot_as_module is True
    if file_path:
        sanitized_stem = sanitize_module_name(file_path.stem, treat_dot_as_module=should_keep_dots_in_files)
        module_parts = name.split(".")[:-1] if should_split_names else []
        return [
            *file_path.parts[:-1],
            sanitized_stem,
            *module_parts,
        ]
    return name.split(".")[:-1] if should_split_names else []


def get_module_name(name: str, file_path: Path | None, *, treat_dot_as_module: bool | None) -> str:
    """Get the full module name from a name and file path."""
    return ".".join(get_module_path(name, file_path, treat_dot_as_module=treat_dot_as_module))


class TemplateBase(ABC):
    """Abstract base class for template-based code generation."""

    @cached_property
    @abstractmethod
    def template_file_path(self) -> Path:
        """Get the path to the template file."""
        raise NotImplementedError

    @cached_property
    def template(self) -> Template:
        """Get the cached Jinja2 template instance."""
        return get_template(self.template_file_path)

    @abstractmethod
    def render(self) -> str:
        """Render the template to a string."""
        raise NotImplementedError

    def _render(self, *args: Any, **kwargs: Any) -> str:
        """Render the template with the given arguments."""
        return self.template.render(*args, **kwargs)

    def __str__(self) -> str:
        """Return the rendered template as a string."""
        return self.render()


class BaseClassDataType(DataType):
    """DataType subclass for base class references."""


UNDEFINED: Any = object()


class DataModel(TemplateBase, Nullable, ABC):  # noqa: PLR0904
    """Abstract base class for all data model types.

    Handles template rendering, import collection, and model relationships.
    """

    TEMPLATE_FILE_PATH: ClassVar[str] = ""
    BASE_CLASS: ClassVar[str] = ""
    DEFAULT_IMPORTS: ClassVar[tuple[Import, ...]] = ()
    IS_ALIAS: ClassVar[bool] = False
    SUPPORTS_GENERIC_BASE_CLASS: ClassVar[bool] = True
    SUPPORTS_DISCRIMINATOR: ClassVar[bool] = False
    SUPPORTS_FIELD_RENAMING: ClassVar[bool] = False
    SUPPORTS_WRAPPED_DEFAULT: ClassVar[bool] = False
    SUPPORTS_KW_ONLY: ClassVar[bool] = False
    has_forward_reference: bool = False

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
        """Initialize a data model with fields, base classes, and configuration."""
        self.keyword_only = keyword_only
        self.frozen = frozen
        self.dataclass_arguments: DataclassArguments = dataclass_arguments if dataclass_arguments is not None else {}
        if not self.TEMPLATE_FILE_PATH:
            msg = "TEMPLATE_FILE_PATH is undefined"
            raise Exception(msg)  # noqa: TRY002

        self._custom_template_dir: Path | None = custom_template_dir
        self.decorators: list[str] = decorators or []
        self._additional_imports: list[Import] = []
        self.custom_base_class = custom_base_class
        if base_classes:
            self.base_classes: list[BaseClassDataType] = [BaseClassDataType(reference=b) for b in base_classes]
        else:
            self.set_base_class()

        self.file_path: Path | None = path
        self.reference: Reference = reference

        self.reference.source = self

        if extra_template_data is not None:
            # The supplied defaultdict will either create a new entry,
            # or already contain a predefined entry for this type
            self.extra_template_data = extra_template_data[self.reference.path]

            # We use the full object reference path as dictionary key, but
            # we still support `name` as key because it was used for
            # `--extra-template-data` input file and we don't want to break the
            # existing behavior.
            self.extra_template_data.update(extra_template_data[self.name])
        else:
            self.extra_template_data = defaultdict(dict)

        self.fields = self._validate_fields(fields) if fields else []

        for base_class in self.base_classes:
            if base_class.reference:
                base_class.reference.children.append(self)

        if extra_template_data is not None:
            all_model_extra_template_data = extra_template_data.get(ALL_MODEL)
            if all_model_extra_template_data:
                _copy_all_model_data(all_model_extra_template_data, self.extra_template_data)

        self.methods: list[str] = methods or []

        self.description = description
        for field in self.fields:
            field.parent = self

        self._additional_imports.extend(self.DEFAULT_IMPORTS)
        self.default: Any = default
        self._nullable: bool = nullable
        self._treat_dot_as_module: bool | None = treat_dot_as_module
        self._dedup_key_cache: dict[tuple[str | None, bool], tuple[Any, ...]] = {}

    def _validate_fields(self, fields: list[DataModelFieldBase]) -> list[DataModelFieldBase]:
        names: set[str] = set()
        unique_fields: list[DataModelFieldBase] = []
        for field in fields:
            if field.name:
                if field.name in names:
                    warn(f"Field name `{field.name}` is duplicated on {self.name}", stacklevel=2)
                    continue
                names.add(field.name)
            unique_fields.append(field)
        return unique_fields

    def iter_all_fields(self, visited: set[str] | None = None) -> Iterator[DataModelFieldBase]:
        """Yield all fields including those from base classes (parent fields first)."""
        if visited is None:
            visited = set()
        if self.reference.path in visited:  # pragma: no cover
            return
        visited.add(self.reference.path)
        for base_class in self.base_classes:
            if base_class.reference and isinstance(base_class.reference.source, DataModel):
                yield from base_class.reference.source.iter_all_fields(visited)
        yield from self.fields

    def get_dedup_key(self, class_name: str | None = None, *, use_default: bool = True) -> tuple[Any, ...]:
        """Generate hashable key for model deduplication.

        Results are cached per (class_name, use_default) combination since
        the key computation involves expensive render() and imports calls.
        """
        cache_key = (class_name, use_default)
        cached = self._dedup_key_cache.get(cache_key)
        if cached is not None:
            return cached

        from datamodel_code_generator.parser.base import to_hashable  # noqa: PLC0415

        render_class_name = class_name if class_name is not None or not use_default else "M"
        result = tuple(to_hashable(v) for v in (self.render(class_name=render_class_name), self.imports))
        self._dedup_key_cache[cache_key] = result
        return result

    def create_reuse_model(self, base_ref: Reference) -> Self:
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
            treat_dot_as_module=self._treat_dot_as_module,
        )

    def replace_children_in_models(self, models: list[DataModel], new_ref: Reference) -> None:
        """Replace reference children if their parent model is in models list."""
        from datamodel_code_generator.parser.base import get_most_of_parent  # noqa: PLC0415

        for child in self.reference.children[:]:
            if isinstance(child, DataType) and get_most_of_parent(child) in models:
                child.replace_reference(new_ref)

    def set_base_class(self) -> None:
        """Set up the base class for this model."""
        base_class = self.custom_base_class or self.BASE_CLASS
        if not base_class:
            self.base_classes = []
            return
        base_class_import = Import.from_full_path(base_class)
        self._additional_imports.append(base_class_import)
        self.base_classes = [BaseClassDataType.from_import(base_class_import)]

    @cached_property
    def template_file_path(self) -> Path:
        """Get the path to the template file, checking custom directory first."""
        template_file_path = Path(self.TEMPLATE_FILE_PATH)
        if self._custom_template_dir is not None:
            custom_template_file_path = self._custom_template_dir / template_file_path
            if cached_path_exists(custom_template_file_path):
                return custom_template_file_path
        return template_file_path

    @cached_property
    def template(self) -> Template:
        """Get the Jinja2 template with custom directory support for includes."""
        resolved_path = self.template_file_path
        if resolved_path.is_absolute():
            return _get_template_with_absolute_path(resolved_path, Path(self.TEMPLATE_FILE_PATH).parent)
        return _get_template_with_custom_dir(Path(self.TEMPLATE_FILE_PATH), self._custom_template_dir)

    @property
    def imports(self) -> tuple[Import, ...]:
        """Get all imports required by this model and its fields."""
        return chain_as_tuple(
            (i for f in self.fields for i in f.imports),
            self._additional_imports,
        )

    @property
    def reference_classes(self) -> frozenset[str]:
        """Get all referenced class paths used by this model."""
        return frozenset(
            {r.reference.path for r in self.base_classes if r.reference}
            | {t for f in self.fields for t in f.unresolved_types}
        )

    @property
    def name(self) -> str:
        """Get the full name of this model."""
        return self.reference.name

    @property
    def duplicate_name(self) -> str:
        """Get the duplicate name for this model if it exists."""
        return self.reference.duplicate_name or ""

    @property
    def base_class(self) -> str:
        """Get the comma-separated string of base class names."""
        return ", ".join(b.type_hint for b in self.base_classes)

    @staticmethod
    def _get_class_name(name: str) -> str:
        if "." in name:
            return name.rsplit(".", 1)[-1]
        return name

    @property
    def class_name(self) -> str:
        """Get the class name without module path."""
        return self._get_class_name(self.name)

    @class_name.setter
    def class_name(self, class_name: str) -> None:
        if "." in self.reference.name:
            self.reference.name = f"{self.reference.name.rsplit('.', 1)[0]}.{class_name}"
        else:
            self.reference.name = class_name

    @property
    def duplicate_class_name(self) -> str:
        """Get the duplicate class name without module path."""
        return self._get_class_name(self.duplicate_name)

    @property
    def module_path(self) -> list[str]:
        """Get the module path components for this model."""
        return get_module_path(self.name, self.file_path, treat_dot_as_module=self._treat_dot_as_module)

    @property
    def module_name(self) -> str:
        """Get the full module name for this model."""
        return get_module_name(self.name, self.file_path, treat_dot_as_module=self._treat_dot_as_module)

    @property
    def all_data_types(self) -> Iterator[DataType]:
        """Iterate over all data types used in this model."""
        for field in self.fields:
            yield from field.data_type.all_data_types
        yield from self.base_classes

    @property
    def is_alias(self) -> bool:
        """Whether is a type alias (i.e. not an instance of BaseModel/RootModel)."""
        return self.IS_ALIAS

    @classmethod
    def create_base_class_model(
        cls,
        config: dict[str, Any],  # noqa: ARG003
        reference: Reference,  # noqa: ARG003
        custom_template_dir: Path | None = None,  # noqa: ARG003
        keyword_only: bool = False,  # noqa: ARG003, FBT001, FBT002
        treat_dot_as_module: bool | None = None,  # noqa: ARG003, FBT001
    ) -> DataModel | None:
        """Create a shared base class model for DRY configuration.

        Returns the base model or None if not supported. Updates reference in place.
        Each model type should override this to provide appropriate implementation.
        """
        return None

    @property
    def nullable(self) -> bool:
        """Check if this model is nullable."""
        return self._nullable

    @cached_property
    def path(self) -> str:
        """Get the full reference path for this model."""
        return self.reference.path

    def set_reference_path(self, new_path: str) -> None:
        """Set reference path and clear cached path property."""
        self.reference.path = new_path
        if "path" in self.__dict__:
            del self.__dict__["path"]

    def render(self, *, class_name: str | None = None) -> str:
        """Render the model to a string using the template."""
        return self._render(
            class_name=class_name or self.class_name,
            fields=self.fields,
            decorators=self.decorators,
            base_class=self.base_class,
            methods=self.methods,
            description=self.description,
            dataclass_arguments=self.dataclass_arguments,
            path=self.path,
            **self.extra_template_data,
        )


if is_pydantic_v2():
    _rebuild_namespace = {"Union": Union, "DataModelFieldBase": DataModelFieldBase, "DataType": DataType}
    DataType.model_rebuild(_types_namespace=_rebuild_namespace)
    BaseClassDataType.model_rebuild(_types_namespace=_rebuild_namespace)
    DataModelFieldBase.model_rebuild(_types_namespace={"DataModel": DataModel})
else:
    _rebuild_namespace = {"Union": Union, "DataModelFieldBase": DataModelFieldBase, "DataType": DataType}
    DataType.model_rebuild(_types_namespace=_rebuild_namespace)
    BaseClassDataType.model_rebuild(_types_namespace=_rebuild_namespace)
    DataModelFieldBase.model_rebuild(_types_namespace={"DataModel": DataModel})
