"""Reference resolution and model tracking system.

Provides Reference for tracking model references across schemas, ModelResolver
for managing class names and field names, and FieldNameResolver for converting
schema field names to valid Python identifiers.
"""

from __future__ import annotations

import re
from collections import defaultdict
from contextlib import contextmanager
from enum import Enum, auto
from functools import cached_property, lru_cache
from itertools import zip_longest
from keyword import iskeyword
from pathlib import Path, PurePath
from re import Pattern
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    NamedTuple,
    Optional,
    Protocol,
    TypeVar,
    cast,
    runtime_checkable,
)
from urllib.parse import ParseResult, urlparse

import pydantic
from packaging import version
from pydantic import BaseModel, Field
from typing_extensions import TypeIs

from datamodel_code_generator import Error, NamingStrategy
from datamodel_code_generator.util import ConfigDict, camel_to_snake, is_pydantic_v2, model_validator

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterator, Mapping, Sequence
    from collections.abc import Set as AbstractSet

    import inflect
    from pydantic.typing import DictStrAny

    from datamodel_code_generator.model.base import DataModel
    from datamodel_code_generator.types import DataType


def _is_data_type(value: object) -> TypeIs[DataType]:
    """Check if value is a DataType instance."""
    from datamodel_code_generator.types import DataType as DataType_  # noqa: PLC0415

    return isinstance(value, DataType_)


def _is_data_model(value: object) -> TypeIs[DataModel]:
    """Check if value is a DataModel instance."""
    from datamodel_code_generator.model.base import DataModel as DataModel_  # noqa: PLC0415

    return isinstance(value, DataModel_)


@runtime_checkable
class ReferenceChild(Protocol):
    """Protocol for objects that can be stored in Reference.children.

    This is a minimal protocol - actual usage checks isinstance for DataType
    or DataModel to access specific methods like replace_reference or class_name.
    Using a property makes the type covariant, allowing both DataModel (Reference)
    and DataType (Reference | None) to satisfy this protocol.
    """

    @property
    def reference(self) -> Reference | None:
        """Return the reference associated with this object."""
        ...


class _BaseModel(BaseModel):
    """Base model with field exclusion and pass-through support."""

    _exclude_fields: ClassVar[set[str]] = set()
    _pass_fields: ClassVar[set[str]] = set()

    if not TYPE_CHECKING:  # pragma: no branch

        def __init__(self, **values: Any) -> None:
            super().__init__(**values)
            for pass_field_name in self._pass_fields:
                if pass_field_name in values:
                    setattr(self, pass_field_name, values[pass_field_name])

    if not TYPE_CHECKING:  # pragma: no branch
        if is_pydantic_v2():

            def dict(  # noqa: PLR0913
                self,
                *,
                include: AbstractSet[int | str] | Mapping[int | str, Any] | None = None,
                exclude: AbstractSet[int | str] | Mapping[int | str, Any] | None = None,
                by_alias: bool = False,
                exclude_unset: bool = False,
                exclude_defaults: bool = False,
                exclude_none: bool = False,
            ) -> DictStrAny:
                return self.model_dump(
                    include=include,
                    exclude=set(exclude or ()) | self._exclude_fields,
                    by_alias=by_alias,
                    exclude_unset=exclude_unset,
                    exclude_defaults=exclude_defaults,
                    exclude_none=exclude_none,
                )

        else:

            def dict(  # noqa: PLR0913
                self,
                *,
                include: AbstractSet[int | str] | Mapping[int | str, Any] | None = None,
                exclude: AbstractSet[int | str] | Mapping[int | str, Any] | None = None,
                by_alias: bool = False,
                skip_defaults: bool | None = None,
                exclude_unset: bool = False,
                exclude_defaults: bool = False,
                exclude_none: bool = False,
            ) -> DictStrAny:
                return super().dict(
                    include=include,
                    exclude=set(exclude or ()) | self._exclude_fields,
                    by_alias=by_alias,
                    skip_defaults=skip_defaults,
                    exclude_unset=exclude_unset,
                    exclude_defaults=exclude_defaults,
                    exclude_none=exclude_none,
                )


class Reference(_BaseModel):
    """Represents a reference to a model in the schema.

    Tracks path, name, and relationships between models for resolution.
    """

    path: str
    original_name: str = ""
    name: str
    duplicate_name: Optional[str] = None  # noqa: UP045
    loaded: bool = True
    source: Optional[ReferenceChild] = None  # noqa: UP045
    children: list[ReferenceChild] = Field(default_factory=list)
    _exclude_fields: ClassVar[set[str]] = {"children"}

    @model_validator(mode="before")
    def validate_original_name(cls, values: Any) -> Any:  # noqa: N805
        """Assign name to original_name if original_name is empty."""
        if not isinstance(values, dict):  # pragma: no cover
            return values
        original_name = values.get("original_name")
        if original_name:
            return values

        values["original_name"] = values.get("name", original_name)
        return values

    if is_pydantic_v2():
        # TODO[pydantic]: The following keys were removed: `copy_on_model_validation`.
        # Check https://docs.pydantic.dev/dev-v2/migration/#changes-to-config for more information.
        model_config = ConfigDict(  # pyright: ignore[reportAssignmentType]
            arbitrary_types_allowed=True,
            ignored_types=(cached_property,),
            revalidate_instances="never",
        )
    else:

        class Config:
            """Pydantic v1 configuration for Reference model."""

            arbitrary_types_allowed = True
            keep_untouched = (cached_property,)
            copy_on_model_validation = False if version.parse(pydantic.VERSION) < version.parse("1.9.2") else "none"

    @property
    def short_name(self) -> str:
        """Return the last component of the dotted name."""
        return self.name.rsplit(".", 1)[-1]

    def replace_children_references(self, new_reference: Reference) -> None:
        """Replace all DataType children's reference with new_reference."""
        for child in self.children[:]:
            if _is_data_type(child):
                child.replace_reference(new_reference)

    def iter_data_model_children(self) -> Iterator[DataModel]:
        """Yield all DataModel children."""
        for child in self.children:
            if _is_data_model(child):
                yield child


SINGULAR_NAME_SUFFIX: str = "Item"

ID_PATTERN: Pattern[str] = re.compile(r"^#[^/].*")

SPECIAL_PATH_MARKER: str = "#-datamodel-code-generator-#-"

T = TypeVar("T")


@contextmanager
def context_variable(setter: Callable[[T], None], current_value: T, new_value: T) -> Generator[None, None, None]:
    """Context manager that temporarily sets a value and restores it on exit."""
    previous_value: T = current_value
    setter(new_value)
    try:
        yield
    finally:
        setter(previous_value)


class FieldNameResolver:
    """Converts schema field names to valid Python identifiers."""

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        aliases: Mapping[str, str] | None = None,
        snake_case_field: bool = False,  # noqa: FBT001, FBT002
        empty_field_name: str | None = None,
        original_delimiter: str | None = None,
        special_field_name_prefix: str | None = None,
        remove_special_field_name_prefix: bool = False,  # noqa: FBT001, FBT002
        capitalise_enum_members: bool = False,  # noqa: FBT001, FBT002
        no_alias: bool = False,  # noqa: FBT001, FBT002
    ) -> None:
        """Initialize field name resolver with transformation options."""
        self.aliases: Mapping[str, str] = {} if aliases is None else {**aliases}
        self.empty_field_name: str = empty_field_name or "_"
        self.snake_case_field = snake_case_field
        self.original_delimiter: str | None = original_delimiter
        self.special_field_name_prefix: str | None = (
            "field" if special_field_name_prefix is None else special_field_name_prefix
        )
        self.remove_special_field_name_prefix: bool = remove_special_field_name_prefix
        self.capitalise_enum_members: bool = capitalise_enum_members
        self.no_alias = no_alias

    @classmethod
    def _validate_field_name(cls, field_name: str) -> bool:  # noqa: ARG003
        """Check if a field name is valid. Subclasses may override."""
        return True

    def get_valid_name(  # noqa: PLR0912
        self,
        name: str,
        excludes: set[str] | None = None,
        ignore_snake_case_field: bool = False,  # noqa: FBT001, FBT002
        upper_camel: bool = False,  # noqa: FBT001, FBT002
    ) -> str:
        """Convert a name to a valid Python identifier."""
        if not name:
            name = self.empty_field_name
        if name[0] == "#":
            name = name[1:] or self.empty_field_name

        if self.snake_case_field and not ignore_snake_case_field and self.original_delimiter is not None:
            name = snake_to_upper_camel(name, delimiter=self.original_delimiter)

        name = re.sub(r"[¹²³⁴⁵⁶⁷⁸⁹]|\W", "_", name)
        if name[0].isnumeric():
            name = f"{self.special_field_name_prefix}_{name}"

        # We should avoid having a field begin with an underscore, as it
        # causes pydantic to consider it as private
        while name.startswith("_"):
            if self.remove_special_field_name_prefix:
                name = name[1:]
            else:
                name = f"{self.special_field_name_prefix}{name}"
                break
        if self.capitalise_enum_members or (self.snake_case_field and not ignore_snake_case_field):
            name = camel_to_snake(name)
        count = 1
        if iskeyword(name) or not self._validate_field_name(name):
            name += "_"
        if upper_camel:
            new_name = snake_to_upper_camel(name)
        elif self.capitalise_enum_members:
            new_name = name.upper()
        else:
            new_name = name
        while (
            not new_name.isidentifier()
            or iskeyword(new_name)
            or (excludes and new_name in excludes)
            or not self._validate_field_name(new_name)
        ):
            new_name = f"{name}{count}" if upper_camel else f"{name}_{count}"
            count += 1
        return new_name

    def get_valid_field_name_and_alias(
        self,
        field_name: str,
        excludes: set[str] | None = None,
        path: list[str] | None = None,
        class_name: str | None = None,
    ) -> tuple[str, str | None]:
        """Get valid field name and original alias if different.

        Supports hierarchical alias resolution with the following priority:
        1. Scoped aliases (ClassName.field_name) - class-level specificity
        2. Flat aliases (field_name) - applies to all occurrences

        Args:
            field_name: The original field name from the schema.
            excludes: Set of names to avoid when generating valid names.
            path: Unused, kept for backward compatibility.
            class_name: Optional class name for scoped alias resolution.
        """
        del path
        if class_name:
            scoped_key = f"{class_name}.{field_name}"
            if scoped_key in self.aliases:
                return self.aliases[scoped_key], field_name

        if field_name in self.aliases:
            return self.aliases[field_name], field_name

        valid_name = self.get_valid_name(field_name, excludes=excludes)
        return (
            valid_name,
            None if self.no_alias or field_name == valid_name else field_name,
        )


class PydanticFieldNameResolver(FieldNameResolver):
    """Field name resolver that avoids Pydantic reserved names."""

    @classmethod
    def _validate_field_name(cls, field_name: str) -> bool:
        """Check field name doesn't conflict with BaseModel attributes."""
        # TODO: Support Pydantic V2
        return not hasattr(BaseModel, field_name)


class EnumFieldNameResolver(FieldNameResolver):
    """Field name resolver for enum members with special handling for reserved names.

    When using --use-subclass-enum, enums inherit from types like str or int.
    Member names that conflict with methods of these types cause type checker errors.
    This class detects and handles such conflicts by adding underscore suffixes.

    The _BUILTIN_TYPE_ATTRIBUTES set is intentionally static (not using hasattr)
    to avoid runtime Python version differences affecting code generation.
    Based on Python 3.8-3.14 method names (union of all versions for safety).
    Note: 'mro' is handled explicitly in get_valid_name for backward compatibility.
    """

    _BUILTIN_TYPE_ATTRIBUTES: ClassVar[frozenset[str]] = frozenset({
        "as_integer_ratio",
        "bit_count",
        "bit_length",
        "capitalize",
        "casefold",
        "center",
        "conjugate",
        "count",
        "decode",
        "denominator",
        "encode",
        "endswith",
        "expandtabs",
        "find",
        "format",
        "format_map",
        "from_bytes",
        "from_number",
        "fromhex",
        "hex",
        "imag",
        "index",
        "isalnum",
        "isalpha",
        "isascii",
        "isdecimal",
        "isdigit",
        "isidentifier",
        "islower",
        "isnumeric",
        "isprintable",
        "isspace",
        "istitle",
        "isupper",
        "is_integer",
        "join",
        "ljust",
        "lower",
        "lstrip",
        "maketrans",
        "numerator",
        "partition",
        "real",
        "removeprefix",
        "removesuffix",
        "replace",
        "rfind",
        "rindex",
        "rjust",
        "rpartition",
        "rsplit",
        "rstrip",
        "split",
        "splitlines",
        "startswith",
        "strip",
        "swapcase",
        "title",
        "to_bytes",
        "translate",
        "upper",
        "zfill",
    })

    @classmethod
    def _validate_field_name(cls, field_name: str) -> bool:
        """Check field name doesn't conflict with subclass enum base type attributes.

        When using --use-subclass-enum, enums inherit from types like str or int.
        Member names that conflict with methods of these types (e.g., 'count' for str)
        cause type checker errors. This method detects such conflicts.
        """
        return field_name not in cls._BUILTIN_TYPE_ATTRIBUTES

    def get_valid_name(
        self,
        name: str,
        excludes: set[str] | None = None,
        ignore_snake_case_field: bool = False,  # noqa: FBT001, FBT002
        upper_camel: bool = False,  # noqa: FBT001, FBT002
    ) -> str:
        """Convert name to valid enum member, handling reserved names."""
        return super().get_valid_name(
            name="mro_" if name == "mro" else name,
            excludes={"mro"} | (excludes or set()),
            ignore_snake_case_field=ignore_snake_case_field,
            upper_camel=upper_camel,
        )


class ModelType(Enum):
    """Type of model for field name resolution strategy."""

    PYDANTIC = auto()
    ENUM = auto()
    CLASS = auto()


DEFAULT_FIELD_NAME_RESOLVERS: dict[ModelType, type[FieldNameResolver]] = {
    ModelType.ENUM: EnumFieldNameResolver,
    ModelType.PYDANTIC: PydanticFieldNameResolver,
    ModelType.CLASS: FieldNameResolver,
}


class ClassName(NamedTuple):
    """A class name with optional duplicate name for disambiguation."""

    name: str
    duplicate_name: str | None


def get_relative_path(base_path: PurePath, target_path: PurePath) -> PurePath:
    """Calculate relative path from base to target."""
    if base_path == target_path:
        return Path()
    if not target_path.is_absolute():
        return target_path
    parent_count: int = 0
    children: list[str] = []
    for base_part, target_part in zip_longest(base_path.parts, target_path.parts):
        if base_part == target_part and not parent_count:
            continue
        if base_part or not target_part:
            parent_count += 1
        if target_part:
            children.append(target_part)
    return Path(*[".." for _ in range(parent_count)], *children)


class ModelResolver:  # noqa: PLR0904
    """Manages model references, class names, and field name resolution.

    Central registry for all model references during parsing, handling
    name uniqueness, path resolution, and field name transformations.
    """

    # Default suffixes for duplicate name resolution by model type
    DEFAULT_DUPLICATE_NAME_SUFFIX: ClassVar[dict[str, str]] = {
        "model": "Model",
        "enum": "Enum",
    }

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        exclude_names: set[str] | None = None,
        duplicate_name_suffix: str | None = None,
        base_url: str | None = None,
        singular_name_suffix: str | None = None,
        aliases: Mapping[str, str] | None = None,
        snake_case_field: bool = False,  # noqa: FBT001, FBT002
        empty_field_name: str | None = None,
        custom_class_name_generator: Callable[[str], str] | None = None,
        base_path: Path | None = None,
        field_name_resolver_classes: dict[ModelType, type[FieldNameResolver]] | None = None,
        original_field_name_delimiter: str | None = None,
        special_field_name_prefix: str | None = None,
        remove_special_field_name_prefix: bool = False,  # noqa: FBT001, FBT002
        capitalise_enum_members: bool = False,  # noqa: FBT001, FBT002
        no_alias: bool = False,  # noqa: FBT001, FBT002
        remove_suffix_number: bool = False,  # noqa: FBT001, FBT002
        parent_scoped_naming: bool = False,  # noqa: FBT001, FBT002
        treat_dot_as_module: bool | None = None,  # noqa: FBT001
        naming_strategy: NamingStrategy | None = None,
        duplicate_name_suffix_map: dict[str, str] | None = None,
    ) -> None:
        """Initialize model resolver with naming and resolution options."""
        self.references: dict[str, Reference] = {}
        self._current_root: Sequence[str] = []
        self._root_id: str | None = None
        self._root_id_base_path: str | None = None
        self.ids: defaultdict[str, dict[str, str]] = defaultdict(dict)
        self.after_load_files: set[str] = set()
        self.exclude_names: set[str] = exclude_names or set()
        self.duplicate_name_suffix: str | None = duplicate_name_suffix
        self._base_url: str | None = base_url
        self.singular_name_suffix: str = (
            singular_name_suffix if isinstance(singular_name_suffix, str) else SINGULAR_NAME_SUFFIX
        )
        merged_field_name_resolver_classes = DEFAULT_FIELD_NAME_RESOLVERS.copy()
        if field_name_resolver_classes:  # pragma: no cover
            merged_field_name_resolver_classes.update(field_name_resolver_classes)
        self.field_name_resolvers: dict[ModelType, FieldNameResolver] = {
            k: v(
                aliases=aliases,
                snake_case_field=snake_case_field,
                empty_field_name=empty_field_name,
                original_delimiter=original_field_name_delimiter,
                special_field_name_prefix=special_field_name_prefix,
                remove_special_field_name_prefix=remove_special_field_name_prefix,
                capitalise_enum_members=capitalise_enum_members if k == ModelType.ENUM else False,
                no_alias=no_alias,
            )
            for k, v in merged_field_name_resolver_classes.items()
        }
        self.class_name_generator = custom_class_name_generator or self.default_class_name_generator
        self._base_path: Path = base_path or Path.cwd()
        self._current_base_path: Path | None = self._base_path
        self.remove_suffix_number: bool = remove_suffix_number

        # Handle naming strategy with backward compatibility for parent_scoped_naming
        if naming_strategy is None and parent_scoped_naming:
            naming_strategy = NamingStrategy.ParentPrefixed
        self.naming_strategy: NamingStrategy = naming_strategy or NamingStrategy.Numbered
        self.parent_scoped_naming = parent_scoped_naming or (self.naming_strategy == NamingStrategy.ParentPrefixed)
        self.treat_dot_as_module = treat_dot_as_module

        # Duplicate name suffix map for type-specific suffixes
        # Only use suffixes when explicitly provided via --duplicate-name-suffix
        self.duplicate_name_suffix_map: dict[str, str] = duplicate_name_suffix_map or {}

        # Incrementally maintained set of reference names for O(1) uniqueness checking
        self._reference_names_cache: set[str] = set()

    def _get_reference_names(self) -> set[str]:
        """Get the set of all reference names for uniqueness checking."""
        return self._reference_names_cache

    def _update_reference_name(self, old_name: str | None, new_name: str) -> None:
        """Update the reference names cache when a reference name changes."""
        if old_name and old_name != new_name:
            self._reference_names_cache.discard(old_name)
        self._reference_names_cache.add(new_name)

    def _remove_reference_name(self, name: str) -> None:
        """Remove a name from the reference names cache."""
        self._reference_names_cache.discard(name)

    @property
    def current_base_path(self) -> Path | None:
        """Return the current base path for file resolution."""
        return self._current_base_path

    def set_current_base_path(self, base_path: Path | None) -> None:
        """Set the current base path for file resolution."""
        self._current_base_path = base_path

    @property
    def base_url(self) -> str | None:
        """Return the base URL for reference resolution."""
        return self._base_url

    def set_base_url(self, base_url: str | None) -> None:
        """Set the base URL for reference resolution."""
        self._base_url = base_url

    @contextmanager
    def current_base_path_context(self, base_path: Path | None) -> Generator[None, None, None]:
        """Temporarily set the current base path within a context."""
        if base_path:
            base_path = (self._base_path / base_path).resolve()
        with context_variable(self.set_current_base_path, self.current_base_path, base_path):
            yield

    @contextmanager
    def base_url_context(self, base_url: str | None) -> Generator[None, None, None]:
        """Temporarily set the base URL within a context.

        Only sets the base_url if:
        - The new value is actually a URL (http://, https://, or file://)
        - OR _base_url was already set (switching between URLs)
        This preserves backward compatibility for local file parsing where
        this method was previously a no-op.
        """
        if self._base_url or (base_url and is_url(base_url)):
            with context_variable(self.set_base_url, self.base_url, base_url):
                yield
        else:
            yield

    @property
    def current_root(self) -> Sequence[str]:
        """Return the current root path components."""
        return self._current_root

    def set_current_root(self, current_root: Sequence[str]) -> None:
        """Set the current root path components."""
        self._current_root = current_root

    @contextmanager
    def current_root_context(self, current_root: Sequence[str]) -> Generator[None, None, None]:
        """Temporarily set the current root path within a context."""
        with context_variable(self.set_current_root, self.current_root, current_root):
            yield

    @property
    def root_id(self) -> str | None:
        """Return the root identifier for the current schema."""
        return self._root_id

    @property
    def root_id_base_path(self) -> str | None:
        """Return the base path component of the root identifier."""
        return self._root_id_base_path

    def set_root_id(self, root_id: str | None) -> None:
        """Set the root identifier and extract its base path."""
        if root_id and "/" in root_id:
            self._root_id_base_path = root_id.rsplit("/", 1)[0]
        else:
            self._root_id_base_path = None

        self._root_id = root_id

    def add_id(self, id_: str, path: Sequence[str]) -> None:
        """Register an identifier mapping to a resolved reference path."""
        self.ids["/".join(self.current_root)][id_] = self.resolve_ref(path)

    def resolve_ref(self, path: Sequence[str] | str) -> str:  # noqa: PLR0911, PLR0912, PLR0914
        """Resolve a reference path to its canonical form."""
        joined_path = path if isinstance(path, str) else self.join_path(tuple(path))
        if joined_path == "#":
            return f"{'/'.join(self.current_root)}#"
        if self.current_base_path and not self.base_url and joined_path[0] != "#" and not is_url(joined_path):
            # resolve local file path
            file_path, fragment = joined_path.split("#", 1) if "#" in joined_path else (joined_path, "")
            resolved_file_path = Path(self.current_base_path, file_path).resolve()
            joined_path = get_relative_path(self._base_path, resolved_file_path).as_posix()
            if fragment:
                joined_path += f"#{fragment}"
        if ID_PATTERN.match(joined_path) and SPECIAL_PATH_MARKER not in joined_path:
            id_scope = "/".join(self.current_root)
            scoped_ids = self.ids[id_scope]
            ref: str | None = scoped_ids.get(joined_path)
            if ref is None:
                msg = (
                    f"Unresolved $id reference '{joined_path}' in scope '{id_scope or '<root>'}'. "
                    f"Known $id values: {', '.join(sorted(scoped_ids)) or '<none>'}"
                )
                raise Error(msg)
        else:
            if "#" not in joined_path:
                joined_path += "#"
            elif joined_path[0] == "#" and self.current_root:
                joined_path = f"{'/'.join(self.current_root)}{joined_path}"

            file_path, fragment = joined_path.split("#", 1)
            ref = f"{file_path}#{fragment}"
            if (
                self.root_id_base_path
                and not self.base_url
                and not (is_url(joined_path) or Path(self._base_path, file_path).is_file())
            ):
                ref = f"{self.root_id_base_path}/{ref}"

        if is_url(ref):
            file_part, path_part = ref.split("#", 1)
            id_scope = "/".join(self.current_root)
            scoped_ids = self.ids[id_scope]
            if file_part in scoped_ids:
                mapped_ref = scoped_ids[file_part]
                if path_part:
                    mapped_base, mapped_fragment = mapped_ref.split("#", 1) if "#" in mapped_ref else (mapped_ref, "")
                    combined_fragment = f"{mapped_fragment.rstrip('/')}/{path_part.lstrip('/')}"
                    return f"{mapped_base}#{combined_fragment}"
                return mapped_ref

        if self.base_url:
            from .http import join_url  # noqa: PLC0415

            effective_base = self.root_id or self.base_url
            joined_url = join_url(effective_base, ref)
            if "#" in joined_url:
                return joined_url
            return f"{joined_url}#"

        if is_url(ref):
            file_part, path_part = ref.split("#", 1)
            if file_part == self.root_id:
                return f"{'/'.join(self.current_root)}#{path_part}"
            target_url: ParseResult = urlparse(file_part)
            if not (self.root_id and self.current_base_path):
                return ref
            root_id_url: ParseResult = urlparse(self.root_id)
            if (target_url.scheme, target_url.netloc) == (
                root_id_url.scheme,
                root_id_url.netloc,
            ):  # pragma: no cover
                target_url_path = Path(target_url.path)
                target_path = (
                    self.current_base_path
                    / get_relative_path(Path(root_id_url.path).parent, target_url_path.parent)
                    / target_url_path.name
                )
                if target_path.exists():
                    return f"{target_path.resolve().relative_to(self._base_path)}#{path_part}"

        return ref

    def is_after_load(self, ref: str) -> bool:
        """Check if a reference points to a file loaded after the current one."""
        if is_url(ref) or not self.current_base_path:
            return False
        file_part, *_ = ref.split("#", 1)
        absolute_path = Path(self._base_path, file_part).resolve().as_posix()
        if self.is_external_root_ref(ref) or self.is_external_ref(ref):
            return absolute_path in self.after_load_files
        return False  # pragma: no cover

    @staticmethod
    def is_external_ref(ref: str) -> bool:
        """Check if a reference points to an external file."""
        return "#" in ref and ref[0] != "#"

    @staticmethod
    def is_external_root_ref(ref: str) -> bool:
        """Check if a reference points to an external file root."""
        return bool(ref) and ref[-1] == "#"

    @staticmethod
    @lru_cache(maxsize=4096)
    def join_path(path: tuple[str, ...]) -> str:
        """Join path components with slashes and normalize anchors."""
        joined_path = "/".join(p for p in path if p).replace("/#", "#")
        if "#" not in joined_path:
            joined_path += "#"
        return joined_path

    def _is_external_path(self, resolved_path: str) -> bool:
        """Check if a resolved path belongs to an external file."""
        current_root_path = self.join_path(tuple(self._current_root))
        current_file = current_root_path.split("#")[0]
        resolved_file = resolved_path.split("#", maxsplit=1)[0]
        return current_file != resolved_file

    def add_ref(self, ref: str, resolved: bool = False) -> Reference:  # noqa: FBT001, FBT002
        """Add a reference and return the Reference object."""
        path = self.resolve_ref(ref) if not resolved else ref
        if reference := self.references.get(path):
            return reference
        split_ref = ref.rsplit("/", 1)
        if len(split_ref) == 1:
            original_name = Path(split_ref[0].rstrip("#") if self.is_external_root_ref(path) else split_ref[0]).stem
        else:
            original_name = Path(split_ref[1].rstrip("#")).stem if self.is_external_root_ref(path) else split_ref[1]
        # For PrimaryFirst strategy, use unique=True for external references
        # so that definitions in the main input file get priority for clean names
        use_unique = self.naming_strategy == NamingStrategy.PrimaryFirst and self._is_external_path(path)
        name = self.get_class_name(original_name, unique=use_unique).name
        reference = Reference(
            path=path,
            original_name=original_name,
            name=name,
            loaded=False,
        )

        self.references[path] = reference
        self._update_reference_name(None, reference.name)
        return reference

    def _find_parent_reference(self, path: Sequence[str]) -> Reference | None:
        """Find the closest parent reference for a given path.

        Traverses up the path hierarchy to find the first existing parent reference.
        Returns None if no parent reference is found.
        """
        parent_path = list(path[:-1])
        while parent_path:
            if parent_reference := self.references.get(self.join_path(tuple(parent_path))):
                return parent_reference
            parent_path = parent_path[:-1]
        return None

    def _check_parent_scope_option(self, name: str, path: Sequence[str]) -> str:
        # Check for parent-prefixed naming via either the legacy flag or the new naming strategy
        use_parent_prefix = self.parent_scoped_naming or self.naming_strategy == NamingStrategy.ParentPrefixed
        if use_parent_prefix and (parent_ref := self._find_parent_reference(path)):
            return f"{parent_ref.name}_{name}"
        return name

    def _apply_full_path_naming(self, name: str, path: Sequence[str]) -> str:
        """Build name from full schema path for FullPath strategy.

        Uses the immediate parent reference to build a unique name.
        For example: Order > properties > item becomes OrderItem
        """
        if self.naming_strategy != NamingStrategy.FullPath:
            return name

        # Find the immediate parent reference to prefix the name
        if parent_ref := self._find_parent_reference(path):
            # Use immediate parent's name (CamelCase join without underscore)
            return f"{parent_ref.name}{snake_to_upper_camel(name)}"

        return name

    @staticmethod
    def _is_primary_definition(path: Sequence[str]) -> bool:
        """Check if path represents a primary schema definition."""
        # Primary definitions are directly under /definitions/ or /components/schemas/
        path_str = "/".join(path)
        primary_patterns = [
            "#/definitions/",
            "#/components/schemas/",
            "#/$defs/",
        ]
        for pattern in primary_patterns:
            if pattern in path_str:
                # Check if it's a direct child (not nested)
                after_pattern = path_str.split(pattern, 1)[-1]
                # If there's no more "/" after the pattern part, it's a primary definition
                if "/" not in after_pattern:
                    return True
        return False

    def _rename_external_ref_with_same_name(self, name: str, current_path: str) -> None:
        """Rename an external reference that has the same name as a primary definition.

        For PrimaryFirst strategy, when a primary definition in the main file
        has the same name as an external reference, rename the external reference
        so the primary definition can use the clean name.
        """
        for ref_path, ref in self.references.items():
            if ref.name == name and ref_path != current_path:
                # Check if this is an external reference (different file)
                ref_file = ref_path.split("#")[0]
                current_file = current_path.split("#", maxsplit=1)[0]
                if ref_file != current_file:
                    # Rename this external reference
                    new_name = self._get_unique_name(name, camel=True)
                    old_name = ref.name
                    ref.duplicate_name = ref.name
                    ref.name = new_name
                    self._update_reference_name(old_name, new_name)
                    break

    def add(  # noqa: PLR0913
        self,
        path: Sequence[str],
        original_name: str,
        *,
        class_name: bool = False,
        singular_name: bool = False,
        unique: bool = True,
        singular_name_suffix: str | None = None,
        loaded: bool = False,
    ) -> Reference:
        """Add or update a model reference with the given path and name."""
        joined_path = self.join_path(tuple(path))
        reference: Reference | None = self.references.get(joined_path)
        old_ref_name: str | None = reference.name if reference else None
        if reference:
            if loaded and not reference.loaded:
                reference.loaded = True
            if not original_name or original_name in {reference.original_name, reference.name}:
                return reference
        name = original_name
        duplicate_name: str | None = None
        if class_name:
            # Apply naming strategy before further processing
            name = self._check_parent_scope_option(name, path)
            name = self._apply_full_path_naming(name, path)

            # For PrimaryFirst strategy, check if this is a primary definition
            # Primary definitions get priority (don't need suffix), others get suffix when there's conflict
            is_primary = self._is_primary_definition(path)
            if self.naming_strategy == NamingStrategy.PrimaryFirst and is_primary:
                # For primary definitions, try to use the clean name first
                # If an external reference has the same name, rename it
                self._rename_external_ref_with_same_name(name, joined_path)
                name, duplicate_name = self.get_class_name(
                    name=name,
                    unique=unique,
                    reserved_name=reference.name if reference else None,
                    singular_name=singular_name,
                    singular_name_suffix=singular_name_suffix,
                )
            else:
                name, duplicate_name = self.get_class_name(
                    name=name,
                    unique=unique,
                    reserved_name=reference.name if reference else None,
                    singular_name=singular_name,
                    singular_name_suffix=singular_name_suffix,
                )
        else:
            # TODO: create a validate for module name
            name = self.get_valid_field_name(name, model_type=ModelType.CLASS)
            if singular_name:  # pragma: no cover
                name = get_singular_name(name, singular_name_suffix or self.singular_name_suffix)
            elif unique:  # pragma: no cover
                unique_name = self._get_unique_name(name)
                if unique_name != name:
                    duplicate_name = name
                name = unique_name
        if reference:
            reference.original_name = original_name
            reference.name = name
            reference.loaded = loaded
            reference.duplicate_name = duplicate_name
            self._update_reference_name(old_ref_name, name)
        else:
            reference = Reference(
                path=joined_path,
                original_name=original_name,
                name=name,
                loaded=loaded,
                duplicate_name=duplicate_name,
            )
            self.references[joined_path] = reference
            self._update_reference_name(None, name)
        return reference

    def get(self, path: Sequence[str] | str) -> Reference | None:
        """Get a reference by path, returning None if not found."""
        return self.references.get(self.resolve_ref(path))

    def delete(self, path: Sequence[str] | str) -> None:
        """Delete a reference by path if it exists."""
        resolved = self.resolve_ref(path)
        if resolved in self.references:
            old_name = self.references[resolved].name
            del self.references[resolved]
            self._remove_reference_name(old_name)

    def default_class_name_generator(self, name: str) -> str:
        """Generate a valid class name from a string."""
        # TODO: create a validate for class name
        return self.field_name_resolvers[ModelType.CLASS].get_valid_name(
            name, ignore_snake_case_field=True, upper_camel=True
        )

    def get_class_name(
        self,
        name: str,
        unique: bool = True,  # noqa: FBT001, FBT002
        reserved_name: str | None = None,
        singular_name: bool = False,  # noqa: FBT001, FBT002
        singular_name_suffix: str | None = None,
    ) -> ClassName:
        """Generate a unique class name with optional singularization."""
        if "." in name and self.treat_dot_as_module is not False:
            split_name = name.split(".")
            prefix = ".".join(
                # TODO: create a validate for class name
                self.field_name_resolvers[ModelType.CLASS].get_valid_name(n, ignore_snake_case_field=True)
                for n in split_name[:-1]
            )
            prefix += "."
            class_name = split_name[-1]
        else:
            prefix = ""
            class_name = name.replace(".", "_") if "." in name else name

        class_name = self.class_name_generator(class_name)

        if singular_name:
            class_name = get_singular_name(class_name, singular_name_suffix or self.singular_name_suffix)
        duplicate_name: str | None = None
        if unique:
            if reserved_name == class_name:
                return ClassName(name=class_name, duplicate_name=duplicate_name)

            unique_name = self._get_unique_name(class_name, camel=True)
            if unique_name != class_name:
                duplicate_name = class_name
            class_name = unique_name
        return ClassName(name=f"{prefix}{class_name}", duplicate_name=duplicate_name)

    def _get_unique_name(self, name: str, camel: bool = False, model_type: str = "model") -> str:  # noqa: FBT001, FBT002
        unique_name: str = name
        count: int = 0 if self.remove_suffix_number else 1
        # Use cached reference names for O(1) lookup instead of O(n) set creation
        reference_names = self._get_reference_names() | self.exclude_names

        # Determine the suffix to use
        suffix = self._get_suffix_for_model_type(model_type)
        if not suffix and self.duplicate_name_suffix:
            suffix = self.duplicate_name_suffix

        while unique_name in reference_names:
            if suffix:
                name_parts: list[str | int] = [name, suffix, count - 1]
            else:
                name_parts = [name, count]
            delimiter = "" if camel else "_"
            unique_name = delimiter.join(str(p) for p in name_parts if p) if count else name
            count += 1
        return unique_name

    def _get_suffix_for_model_type(self, model_type: str) -> str:
        """Get the suffix for a given model type from the suffix map."""
        return self.duplicate_name_suffix_map.get(model_type, self.duplicate_name_suffix_map.get("default", ""))

    @classmethod
    def validate_name(cls, name: str) -> bool:
        """Check if a name is a valid Python identifier."""
        return name.isidentifier() and not iskeyword(name)

    def get_valid_field_name(
        self,
        name: str,
        excludes: set[str] | None = None,
        model_type: ModelType = ModelType.PYDANTIC,
    ) -> str:
        """Get a valid field name for the specified model type."""
        return self.field_name_resolvers[model_type].get_valid_name(name, excludes)

    def get_valid_field_name_and_alias(
        self,
        field_name: str,
        excludes: set[str] | None = None,
        model_type: ModelType = ModelType.PYDANTIC,
        path: list[str] | None = None,
        class_name: str | None = None,
    ) -> tuple[str, str | None]:
        """Get a valid field name and alias for the specified model type.

        Args:
            field_name: The original field name from the schema.
            excludes: Set of names to avoid when generating valid names.
            model_type: The type of model (PYDANTIC, ENUM, or CLASS).
            path: Unused, kept for backward compatibility.
            class_name: Optional class name for scoped alias resolution.

        Returns:
            A tuple of (valid_field_name, alias_or_none).
        """
        del path
        return self.field_name_resolvers[model_type].get_valid_field_name_and_alias(
            field_name, excludes, class_name=class_name
        )


def _get_inflect_engine() -> inflect.engine:
    """Get or create the inflect engine lazily."""
    global _inflect_engine  # noqa: PLW0603
    if _inflect_engine is None:
        import inflect  # noqa: PLC0415

        _inflect_engine = inflect.engine()
    return _inflect_engine


_inflect_engine: inflect.engine | None = None


@lru_cache
def get_singular_name(name: str, suffix: str = SINGULAR_NAME_SUFFIX) -> str:
    """Convert a plural name to singular form."""
    singular_name = _get_inflect_engine().singular_noun(cast("inflect.Word", name))
    if singular_name is False:
        singular_name = f"{name}{suffix}"
    return singular_name  # pyright: ignore[reportReturnType]


@lru_cache
def snake_to_upper_camel(word: str, delimiter: str = "_") -> str:
    """Convert snake_case or delimited string to UpperCamelCase."""
    prefix = ""
    if word.startswith(delimiter):
        prefix = "_"
        word = word[1:]

    return prefix + "".join(x[0].upper() + x[1:] for x in word.split(delimiter) if x)


def is_url(ref: str) -> bool:
    """Check if a reference string is a URL (HTTP, HTTPS, or file scheme)."""
    return ref.startswith(("https://", "http://", "file://"))
