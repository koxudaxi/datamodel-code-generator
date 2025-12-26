"""Core type system for data model generation.

Provides DataType for representing types with references and constraints,
DataTypeManager as the abstract base for type mappings, and supporting
utilities for handling unions, optionals, and type hints.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from enum import Enum, auto
from functools import lru_cache
from itertools import chain
from re import Pattern
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Optional,
    Protocol,
    TypeVar,
    Union,
    runtime_checkable,
)

import pydantic
from packaging import version
from pydantic import StrictBool, StrictInt, StrictStr, create_model
from typing_extensions import TypeIs

from datamodel_code_generator.format import (
    DateClassType,
    DatetimeClassType,
    PythonVersion,
    PythonVersionMin,
)
from datamodel_code_generator.imports import (
    IMPORT_ABC_MAPPING,
    IMPORT_ABC_SEQUENCE,
    IMPORT_ANY,
    IMPORT_DICT,
    IMPORT_FROZEN_SET,
    IMPORT_LIST,
    IMPORT_LITERAL,
    IMPORT_MAPPING,
    IMPORT_OPTIONAL,
    IMPORT_SEQUENCE,
    IMPORT_SET,
    IMPORT_TUPLE,
    IMPORT_UNION,
    Import,
)
from datamodel_code_generator.reference import Reference, _BaseModel
from datamodel_code_generator.util import ConfigDict, is_pydantic_v2

T = TypeVar("T")
SourceT = TypeVar("SourceT")

OPTIONAL = "Optional"
OPTIONAL_PREFIX = f"{OPTIONAL}["

UNION = "Union"
UNION_PREFIX = f"{UNION}["
UNION_DELIMITER = ", "
UNION_PATTERN: Pattern[str] = re.compile(r"\s*,\s*")
UNION_OPERATOR_DELIMITER = " | "
UNION_OPERATOR_PATTERN: Pattern[str] = re.compile(r"\s*\|\s*")
NONE = "None"
ANY = "Any"
LITERAL = "Literal"
SEQUENCE = "Sequence"
FROZEN_SET = "FrozenSet"
MAPPING = "Mapping"
DICT = "Dict"
SET = "Set"
LIST = "List"
TUPLE = "Tuple"
STANDARD_DICT = "dict"
STANDARD_LIST = "list"
STANDARD_SET = "set"
STANDARD_TUPLE = "tuple"
STANDARD_FROZEN_SET = "frozenset"
STR = "str"

NOT_REQUIRED = "NotRequired"
NOT_REQUIRED_PREFIX = f"{NOT_REQUIRED}["

READ_ONLY = "ReadOnly"
READ_ONLY_PREFIX = f"{READ_ONLY}["


def __getattr__(name: str) -> Any:
    """Provide lazy access to StrictTypes for backwards compatibility."""
    if name == "StrictTypes":
        from datamodel_code_generator.enums import StrictTypes  # noqa: PLC0415

        return StrictTypes
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


if TYPE_CHECKING:
    import builtins
    from collections.abc import Callable, Iterable, Iterator, Sequence

    from pydantic_core import core_schema

    from datamodel_code_generator.enums import StrictTypes
    from datamodel_code_generator.model.base import DataModelFieldBase

if is_pydantic_v2():
    from pydantic import GetCoreSchemaHandler
    from pydantic_core import core_schema


class UnionIntFloat:
    """Pydantic-compatible type that accepts both int and float values."""

    def __init__(self, value: float) -> None:
        """Initialize with an int or float value."""
        self.value: int | float = value

    def __int__(self) -> int:
        """Convert value to int."""
        return int(self.value)

    def __float__(self) -> float:
        """Convert value to float."""
        return float(self.value)

    def __str__(self) -> str:
        """Convert value to string."""
        return str(self.value)

    @classmethod
    def __get_validators__(cls) -> Iterator[Callable[[Any], Any]]:  # noqa: PLW3201
        """Return Pydantic v1 validators."""
        yield cls.validate

    @classmethod
    def __get_pydantic_core_schema__(  # noqa: PLW3201
        cls, _source_type: Any, _handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """Return Pydantic v2 core schema."""
        from_int_schema = core_schema.chain_schema([
            core_schema.union_schema([core_schema.int_schema(), core_schema.float_schema()]),
            core_schema.no_info_plain_validator_function(cls.validate),
        ])

        return core_schema.json_or_python_schema(
            json_schema=from_int_schema,
            python_schema=core_schema.union_schema([
                # check if it's an instance first before doing any further work
                core_schema.is_instance_schema(UnionIntFloat),
                from_int_schema,
            ]),
            serialization=core_schema.plain_serializer_function_ser_schema(lambda instance: instance.value),
        )

    @classmethod
    def validate(cls, v: Any) -> UnionIntFloat:
        """Validate and convert value to UnionIntFloat."""
        if isinstance(v, UnionIntFloat):
            return v
        if not isinstance(v, (int, float)):  # pragma: no cover
            try:
                int(v)
                return cls(v)
            except (TypeError, ValueError):
                pass
            try:
                float(v)
                return cls(v)
            except (TypeError, ValueError):
                pass

            msg = f"{v} is not int or float"
            raise TypeError(msg)
        return cls(v)


def chain_as_tuple(*iterables: Iterable[T]) -> tuple[T, ...]:
    """Chain multiple iterables and return as a tuple.

    Optimized for the common case of 2 iterables to avoid chain() overhead.
    """
    if len(iterables) == 2:  # noqa: PLR2004
        return (*iterables[0], *iterables[1])
    return tuple(chain(*iterables))


def _remove_none_from_union(type_: str, *, use_union_operator: bool) -> str:  # noqa: PLR0912
    """Remove None from a Union type string, handling nested unions."""
    if use_union_operator:
        if " | " not in type_:
            return type_
        separator = "|"
        inner_text = type_
    else:
        if not type_.startswith(UNION_PREFIX):
            return type_
        separator = ","
        inner_text = type_[len(UNION_PREFIX) : -1]

    parts = []
    inner_count = 0
    current_part = ""

    # With this variable we count any non-escaped round bracket, whenever we are inside a
    # constraint string expression. Once found a part starting with `constr(`, we increment
    # this counter for each non-escaped opening round bracket and decrement it for each
    # non-escaped closing round bracket.
    in_constr = 0

    # Parse union parts carefully to handle nested structures
    for char in inner_text:
        current_part += char
        if char == "[" and in_constr == 0:
            inner_count += 1
        elif char == "]" and in_constr == 0:
            inner_count -= 1
        elif char == "(":
            if current_part.strip().startswith("constr(") and (len(current_part) < 2 or current_part[-2] != "\\"):  # noqa: PLR2004
                in_constr += 1
        elif char == ")":
            if in_constr > 0 and (len(current_part) < 2 or current_part[-2] != "\\"):  # noqa: PLR2004
                in_constr -= 1
        elif char == separator and inner_count == 0 and in_constr == 0:
            part = current_part[:-1].strip()
            if part != NONE:
                # Process nested unions recursively
                # only UNION_PREFIX might be nested but not union_operator
                if not use_union_operator and part.startswith(UNION_PREFIX):
                    part = _remove_none_from_union(part, use_union_operator=False)
                parts.append(part)
            current_part = ""

    part = current_part.strip()
    if current_part and part != NONE:
        # only UNION_PREFIX might be nested but not union_operator
        if not use_union_operator and part.startswith(UNION_PREFIX):
            part = _remove_none_from_union(part, use_union_operator=False)
        parts.append(part)

    if not parts:
        return NONE
    if len(parts) == 1:
        return parts[0]

    if use_union_operator:
        return UNION_OPERATOR_DELIMITER.join(parts)

    return f"{UNION_PREFIX}{UNION_DELIMITER.join(parts)}]"


@lru_cache
def get_optional_type(type_: str, use_union_operator: bool) -> str:  # noqa: FBT001
    """Wrap a type string in Optional or add | None suffix."""
    type_ = _remove_none_from_union(type_, use_union_operator=use_union_operator)

    if not type_ or type_ == NONE:
        return NONE
    if use_union_operator:
        return f"{type_} | {NONE}"
    return f"{OPTIONAL_PREFIX}{type_}]"


def is_data_model_field(obj: object) -> TypeIs[DataModelFieldBase]:
    """Check if an object is a DataModelFieldBase instance."""
    from datamodel_code_generator.model.base import DataModelFieldBase  # noqa: PLC0415

    return isinstance(obj, DataModelFieldBase)


@runtime_checkable
class Modular(Protocol):
    """Protocol for objects with a module name property."""

    @property
    def module_name(self) -> str:
        """Return the module name."""
        raise NotImplementedError


@runtime_checkable
class Nullable(Protocol):
    """Protocol for objects with a nullable property."""

    @property
    def nullable(self) -> bool:
        """Return whether the type is nullable."""
        raise NotImplementedError


class DataType(_BaseModel):
    """Represents a type in generated code with imports and references."""

    if is_pydantic_v2():
        # TODO[pydantic]: The following keys were removed: `copy_on_model_validation`.
        # Check https://docs.pydantic.dev/dev-v2/migration/#changes-to-config for more information.
        model_config = ConfigDict(  # pyright: ignore[reportAssignmentType]
            extra="forbid",
            revalidate_instances="never",
        )
    else:
        if not TYPE_CHECKING:  # pragma: no branch

            @classmethod
            def model_rebuild(
                cls,
                *,
                _types_namespace: dict[str, type] | None = None,
            ) -> None:
                """Update forward references for Pydantic v1."""
                localns = _types_namespace or {}
                cls.update_forward_refs(**localns)

        class Config:
            """Pydantic v1 model configuration."""

            extra = "forbid"
            copy_on_model_validation = False if version.parse(pydantic.VERSION) < version.parse("1.9.2") else "none"

    type: Optional[str] = None  # noqa: UP045
    reference: Optional[Reference] = None  # noqa: UP045
    data_types: list[DataType] = []  # noqa: RUF012
    is_func: bool = False
    kwargs: Optional[dict[str, Any]] = None  # noqa: UP045
    import_: Optional[Import] = None  # noqa: UP045
    python_version: PythonVersion = PythonVersionMin
    is_optional: bool = False
    is_dict: bool = False
    is_list: bool = False
    is_set: bool = False
    is_tuple: bool = False
    is_custom_type: bool = False
    literals: list[Union[StrictBool, StrictInt, StrictStr]] = []  # noqa: RUF012, UP007
    enum_member_literals: list[tuple[str, str]] = []  # noqa: RUF012  # [(EnumClassName, member_name), ...]
    use_standard_collections: bool = False
    use_generic_container: bool = False
    use_union_operator: bool = False
    alias: Optional[str] = None  # noqa: UP045
    parent: Union[DataModelFieldBase, DataType, None] = None  # noqa: UP007
    children: list[DataType] = []  # noqa: RUF012
    strict: bool = False
    dict_key: Optional[DataType] = None  # noqa: UP045
    treat_dot_as_module: bool = False
    use_serialize_as_any: bool = False

    _exclude_fields: ClassVar[set[str]] = {"parent", "children"}
    _pass_fields: ClassVar[set[str]] = {"parent", "children", "data_types", "reference"}

    @classmethod
    def from_import(  # noqa: PLR0913
        cls: builtins.type[DataTypeT],
        import_: Import,
        *,
        is_optional: bool = False,
        is_dict: bool = False,
        is_list: bool = False,
        is_set: bool = False,
        is_custom_type: bool = False,
        strict: bool = False,
        kwargs: dict[str, Any] | None = None,
    ) -> DataTypeT:
        """Create a DataType from an Import object."""
        return cls(
            type=import_.import_,
            import_=import_,
            is_optional=is_optional,
            is_dict=is_dict,
            is_list=is_list,
            is_set=is_set,
            is_func=bool(kwargs),
            is_custom_type=is_custom_type,
            strict=strict,
            kwargs=kwargs,
        )

    @property
    def unresolved_types(self) -> frozenset[str]:
        """Return set of unresolved type reference paths."""
        return frozenset(
            {t.reference.path for data_types in self.data_types for t in data_types.all_data_types if t.reference}
            | ({self.reference.path} if self.reference else set())
        )

    def replace_reference(self, reference: Reference | None) -> None:
        """Replace this DataType's reference with a new one."""
        if not self.reference:  # pragma: no cover
            msg = f"`{self.__class__.__name__}.replace_reference()` can't be called when `reference` field is empty."
            raise Exception(msg)  # noqa: TRY002
        self_id = id(self)
        self.reference.children = [c for c in self.reference.children if id(c) != self_id]
        self.reference = reference
        if reference:
            reference.children.append(self)

    def remove_reference(self) -> None:
        """Remove the reference from this DataType."""
        self.replace_reference(None)

    def swap_with(self, new_data_type: DataType) -> None:
        """Detach self and attach new_data_type to the same parent.

        Replaces this DataType with new_data_type in the parent container.
        Works with both field parents and nested DataType parents.
        """
        parent = self.parent
        self.parent = None
        if parent is not None:  # pragma: no cover
            new_data_type.parent = parent
            if is_data_model_field(parent):
                parent.data_type = new_data_type
            elif isinstance(parent, DataType):  # pragma: no cover
                parent.data_types = [new_data_type if d is self else d for d in parent.data_types]

    @property
    def module_name(self) -> str | None:
        """Return the module name from the reference source."""
        if self.reference and isinstance(self.reference.source, Modular):
            return self.reference.source.module_name
        return None  # pragma: no cover

    @property
    def full_name(self) -> str:
        """Return the fully qualified name including module."""
        module_name = self.module_name
        if module_name:
            return f"{module_name}.{self.reference.short_name if self.reference else ''}"
        return self.reference.short_name if self.reference else ""

    @property
    def all_data_types(self) -> Iterator[DataType]:
        """Recursively yield all nested DataTypes including self and dict_key."""
        for data_type in self.data_types:
            yield from data_type.all_data_types
        if self.dict_key:
            yield from self.dict_key.all_data_types
        yield self

    def walk(
        self,
        visitor: Callable[[DataType], None],
        visited: set[int] | None = None,
    ) -> None:
        """Recursively walk this DataType tree, calling visitor on each node."""
        if visited is None:
            visited = set()
        node_id = id(self)
        if node_id in visited:
            return
        visited.add(node_id)
        visitor(self)
        for child in self.data_types:
            child.walk(visitor, visited)
        if self.dict_key:
            self.dict_key.walk(visitor, visited)

    def find_source(self, source_type: type[SourceT]) -> SourceT | None:
        """Find the first reference source matching the given type from all nested data types."""
        for data_type in self.all_data_types:  # pragma: no branch
            if not data_type.reference:  # pragma: no cover
                continue
            source = data_type.reference.source
            if isinstance(source, source_type):  # pragma: no cover
                return source
        return None  # pragma: no cover

    @property
    def all_imports(self) -> Iterator[Import]:
        """Recursively yield all imports from nested DataTypes and self."""
        for data_type in self.data_types:
            yield from data_type.all_imports
        yield from self.imports

    @property
    def imports(self) -> Iterator[Import]:
        """Yield imports required by this DataType."""
        # Add base import if exists
        if self.import_:
            yield self.import_

        # Define required imports based on type features and conditions
        imports: tuple[tuple[bool, Import], ...] = (
            (self.is_optional and not self.use_union_operator, IMPORT_OPTIONAL),
            (len(self.data_types) > 1 and not self.use_union_operator, IMPORT_UNION),
            (bool(self.literals) or bool(self.enum_member_literals), IMPORT_LITERAL),
        )

        if self.use_generic_container:
            if self.use_standard_collections:
                # frozenset is builtin, no import needed for is_set
                imports = (
                    *imports,
                    (self.is_list, IMPORT_ABC_SEQUENCE),
                    (self.is_dict, IMPORT_ABC_MAPPING),
                )
            else:
                imports = (
                    *imports,
                    (self.is_list, IMPORT_SEQUENCE),
                    (self.is_set, IMPORT_FROZEN_SET),
                    (self.is_dict, IMPORT_MAPPING),
                    (self.is_tuple, IMPORT_TUPLE),
                )
        elif not self.use_standard_collections:
            imports = (
                *imports,
                (self.is_list, IMPORT_LIST),
                (self.is_set, IMPORT_SET),
                (self.is_dict, IMPORT_DICT),
                (self.is_tuple, IMPORT_TUPLE),
            )

        # Yield imports based on conditions
        for field, import_ in imports:
            if field and import_ != self.import_:
                yield import_

        # Propagate imports from any dict_key type
        if self.dict_key:
            yield from self.dict_key.imports

    def __init__(self, **values: Any) -> None:
        """Initialize DataType with validation and reference setup."""
        if not TYPE_CHECKING:  # pragma: no cover
            super().__init__(**values)

        # Single-pass optimization: detect ANY+optional and non-ANY types together
        # This is a rare edge case optimization - pragma: no cover
        any_optional_found = False
        has_non_any = False
        for type_ in self.data_types:
            if type_.type == ANY and type_.is_optional:
                any_optional_found = True  # pragma: no cover
            elif type_.type != ANY:
                has_non_any = True
            # Early exit if both conditions met
            if any_optional_found and has_non_any:  # pragma: no cover
                break

        if any_optional_found and has_non_any:  # pragma: no cover
            self.is_optional = True
            self.data_types = [t for t in self.data_types if not (t.type == ANY and t.is_optional)]

        for data_type in self.data_types:
            if data_type.reference or data_type.data_types:
                data_type.parent = self

        if self.reference:
            self.reference.children.append(self)

    def _get_wrapped_reference_type_hint(self, type_: str) -> str:  # noqa: PLR6301
        """Wrap reference type name if needed (override in subclasses, e.g., for SerializeAsAny).

        Args:
            type_: The reference type name (e.g., "User")

        Returns:
            The potentially wrapped type name
        """
        return type_

    @property
    def type_hint(self) -> str:  # noqa: PLR0912, PLR0915
        """Generate the Python type hint string for this DataType."""
        type_: str | None = self.alias or self.type
        if not type_:
            if self.is_tuple:
                tuple_type = STANDARD_TUPLE if self.use_standard_collections else TUPLE
                inner_types = [item.type_hint or ANY for item in self.data_types]
                type_ = f"{tuple_type}[{', '.join(inner_types)}]" if inner_types else f"{tuple_type}[()]"
            elif self.is_union:
                data_types: list[str] = []
                for data_type in self.data_types:
                    data_type_type = data_type.type_hint
                    if not data_type_type or data_type_type in data_types:
                        continue

                    if data_type_type == NONE:
                        self.is_optional = True
                        continue

                    non_optional_data_type_type = _remove_none_from_union(
                        data_type_type, use_union_operator=self.use_union_operator
                    )

                    if non_optional_data_type_type != data_type_type:
                        self.is_optional = True

                    data_types.append(non_optional_data_type_type)
                if not data_types:
                    type_ = ANY
                    self.import_ = self.import_ or IMPORT_ANY
                elif len(data_types) == 1:
                    type_ = data_types[0]
                elif self.use_union_operator:
                    type_ = UNION_OPERATOR_DELIMITER.join(data_types)
                else:
                    type_ = f"{UNION_PREFIX}{UNION_DELIMITER.join(data_types)}]"
            elif len(self.data_types) == 1:
                type_ = self.data_types[0].type_hint
            elif self.enum_member_literals:
                parts = [f"{enum_class}.{member}" for enum_class, member in self.enum_member_literals]
                type_ = f"{LITERAL}[{', '.join(parts)}]"
            elif self.literals:
                type_ = f"{LITERAL}[{', '.join(repr(literal) for literal in self.literals)}]"
            elif self.reference:
                type_ = self.reference.short_name
                type_ = self._get_wrapped_reference_type_hint(type_)
            else:
                # TODO support strict Any
                type_ = ""
        if self.reference:
            source = self.reference.source
            is_alias = getattr(source, "is_alias", False)
            if isinstance(source, Nullable) and source.nullable and not is_alias:
                self.is_optional = True
        if self.is_list:
            if self.use_generic_container:
                list_ = SEQUENCE
            elif self.use_standard_collections:
                list_ = STANDARD_LIST
            else:
                list_ = LIST
            type_ = f"{list_}[{type_}]" if type_ else list_
        elif self.is_set:
            if self.use_generic_container:
                set_ = STANDARD_FROZEN_SET if self.use_standard_collections else FROZEN_SET
            elif self.use_standard_collections:
                set_ = STANDARD_SET
            else:
                set_ = SET
            type_ = f"{set_}[{type_}]" if type_ else set_
        elif self.is_dict:
            if self.use_generic_container:
                dict_ = MAPPING
            elif self.use_standard_collections:
                dict_ = STANDARD_DICT
            else:
                dict_ = DICT
            if self.dict_key or type_:
                key = self.dict_key.type_hint if self.dict_key else STR
                type_ = f"{dict_}[{key}, {type_ or ANY}]"
            else:  # pragma: no cover
                type_ = dict_
        if self.is_optional and type_ != ANY:
            return get_optional_type(type_, self.use_union_operator)
        if self.is_func:
            if self.kwargs:
                kwargs: str = ", ".join(f"{k}={v}" for k, v in self.kwargs.items())
                return f"{type_}({kwargs})"
            return f"{type_}()"
        return type_

    @property
    def is_union(self) -> bool:
        """Return whether this DataType represents a union of multiple types."""
        return len(self.data_types) > 1

    # Mapping from constrained type functions to their base Python types.
    # Only constr is included because it's the only type with a 'pattern' parameter
    # that can trigger lookaround regex detection. Other constrained types (conint,
    # confloat, condecimal, conbytes) don't have pattern constraints, so they will
    # never need base_type_hint conversion in the regex_engine context.
    _CONSTRAINED_TYPE_TO_BASE: ClassVar[dict[str, str]] = {
        "constr": "str",
    }

    @property
    def base_type_hint(self) -> str:  # noqa: PLR0912, PLR0915
        """Return the base type hint without constrained type kwargs.

        For types like constr(pattern=..., min_length=...), this returns just 'str'.
        This works recursively for nested types like list[constr(pattern=...)] -> list[str].

        This is useful when the pattern contains lookaround assertions that require
        regex_engine="python-re", which must be set in model_config. In such cases,
        the RootModel generic cannot use the constrained type because it would be
        evaluated at class definition time before model_config is processed.
        """
        if self.is_func and self.kwargs:
            type_: str | None = self.alias or self.type
            if type_:  # pragma: no branch
                base_type = self._CONSTRAINED_TYPE_TO_BASE.get(type_)
                if base_type is None:
                    # Not a constrained type we convert (e.g., conint, confloat)
                    # Return the full type_hint with kwargs to avoid returning bare function name
                    return self.type_hint
                if self.is_optional and base_type != ANY:  # pragma: no cover
                    return get_optional_type(base_type, self.use_union_operator)
                return base_type

        type_: str | None = self.alias or self.type
        if not type_:
            if self.is_tuple:  # pragma: no cover
                tuple_type = STANDARD_TUPLE if self.use_standard_collections else TUPLE
                inner_types = [item.base_type_hint or ANY for item in self.data_types]
                type_ = f"{tuple_type}[{', '.join(inner_types)}]" if inner_types else f"{tuple_type}[()]"
            elif self.is_union:
                data_types: list[str] = []
                for data_type in self.data_types:
                    data_type_type = data_type.base_type_hint
                    if not data_type_type or data_type_type in data_types:  # pragma: no cover
                        continue

                    if data_type_type == NONE:
                        self.is_optional = True
                        continue

                    non_optional_data_type_type = _remove_none_from_union(
                        data_type_type, use_union_operator=self.use_union_operator
                    )

                    if non_optional_data_type_type != data_type_type:  # pragma: no cover
                        self.is_optional = True

                    data_types.append(non_optional_data_type_type)
                if not data_types:  # pragma: no cover
                    type_ = ANY
                    self.import_ = self.import_ or IMPORT_ANY
                elif len(data_types) == 1:
                    type_ = data_types[0]
                elif self.use_union_operator:
                    type_ = UNION_OPERATOR_DELIMITER.join(data_types)
                else:  # pragma: no cover
                    type_ = f"{UNION_PREFIX}{UNION_DELIMITER.join(data_types)}]"
            elif len(self.data_types) == 1:
                type_ = self.data_types[0].base_type_hint
            elif self.enum_member_literals:  # pragma: no cover
                parts = [f"{enum_class}.{member}" for enum_class, member in self.enum_member_literals]
                type_ = f"{LITERAL}[{', '.join(parts)}]"
            elif self.literals:  # pragma: no cover
                type_ = f"{LITERAL}[{', '.join(repr(literal) for literal in self.literals)}]"
            elif self.reference:  # pragma: no cover
                type_ = self.reference.short_name
                type_ = self._get_wrapped_reference_type_hint(type_)
            else:  # pragma: no cover
                type_ = ""
        if self.reference:  # pragma: no cover
            source = self.reference.source
            is_alias = getattr(source, "is_alias", False)
            if isinstance(source, Nullable) and source.nullable and not is_alias:
                self.is_optional = True
        if self.is_list:
            if self.use_generic_container:
                list_ = SEQUENCE
            elif self.use_standard_collections:
                list_ = STANDARD_LIST
            else:  # pragma: no cover
                list_ = LIST
            type_ = f"{list_}[{type_}]" if type_ else list_
        elif self.is_set:  # pragma: no cover
            if self.use_generic_container:
                set_ = STANDARD_FROZEN_SET if self.use_standard_collections else FROZEN_SET
            elif self.use_standard_collections:
                set_ = STANDARD_SET
            else:
                set_ = SET
            type_ = f"{set_}[{type_}]" if type_ else set_
        elif self.is_dict:
            if self.use_generic_container:
                dict_ = MAPPING
            elif self.use_standard_collections:
                dict_ = STANDARD_DICT
            else:  # pragma: no cover
                dict_ = DICT
            if self.dict_key or type_:
                key = self.dict_key.base_type_hint if self.dict_key else STR
                type_ = f"{dict_}[{key}, {type_ or ANY}]"
            else:  # pragma: no cover
                type_ = dict_

        if self.is_optional and type_ != ANY:
            return get_optional_type(type_, self.use_union_operator)
        if self.is_func:  # pragma: no cover
            return f"{type_}()"
        return type_


DataTypeT = TypeVar("DataTypeT", bound=DataType)


class EmptyDataType(DataType):
    """A DataType placeholder for empty or unresolved types."""


class Types(Enum):
    """Standard type identifiers for schema type mapping."""

    integer = auto()
    int32 = auto()
    int64 = auto()
    number = auto()
    float = auto()
    double = auto()
    decimal = auto()
    time = auto()
    string = auto()
    byte = auto()
    binary = auto()
    date = auto()
    date_time = auto()
    date_time_local = auto()
    time_local = auto()
    timedelta = auto()
    password = auto()
    path = auto()
    email = auto()
    uuid = auto()
    uuid1 = auto()
    uuid2 = auto()
    uuid3 = auto()
    uuid4 = auto()
    uuid5 = auto()
    ulid = auto()
    uri = auto()
    hostname = auto()
    ipv4 = auto()
    ipv4_network = auto()
    ipv6 = auto()
    ipv6_network = auto()
    boolean = auto()
    object = auto()
    null = auto()
    array = auto()
    any = auto()


class DataTypeManager(ABC):
    """Abstract base class for managing type mappings in code generation.

    Subclasses implement get_data_type() to map schema types to DataType objects.
    """

    HOSTNAME_REGEX: ClassVar[str] = (
        r"^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])\.)*"
        r"([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]{0,61}[A-Za-z0-9])$"
    )

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
        use_standard_primitive_types: bool = False,  # noqa: FBT001, FBT002, ARG002
        target_datetime_class: DatetimeClassType | None = None,
        target_date_class: DateClassType | None = None,
        treat_dot_as_module: bool | None = None,  # noqa: FBT001
        use_serialize_as_any: bool = False,  # noqa: FBT001, FBT002
    ) -> None:
        """Initialize DataTypeManager with code generation options."""
        self.python_version = python_version
        self.use_standard_collections: bool = use_standard_collections
        self.use_generic_container_types: bool = use_generic_container_types
        self.strict_types: Sequence[StrictTypes] = strict_types or ()
        self.use_non_positive_negative_number_constrained_types: bool = (
            use_non_positive_negative_number_constrained_types
        )
        self.use_decimal_for_multiple_of: bool = use_decimal_for_multiple_of
        self.use_union_operator: bool = use_union_operator
        self.use_pendulum: bool = use_pendulum
        self.target_datetime_class: DatetimeClassType | None = target_datetime_class
        self.target_date_class: DateClassType | None = target_date_class
        self.treat_dot_as_module: bool = treat_dot_as_module or False
        self.use_serialize_as_any: bool = use_serialize_as_any

        self.data_type: type[DataType] = create_model(
            "ContextDataType",
            python_version=(PythonVersion, python_version),
            use_standard_collections=(bool, use_standard_collections),
            use_generic_container=(bool, use_generic_container_types),
            use_union_operator=(bool, use_union_operator),
            treat_dot_as_module=(bool, treat_dot_as_module),
            use_serialize_as_any=(bool, use_serialize_as_any),
            __base__=DataType,
        )

    @abstractmethod
    def get_data_type(self, types: Types, **kwargs: Any) -> DataType:
        """Map a Types enum value to a DataType. Must be implemented by subclasses."""
        raise NotImplementedError

    def get_data_type_from_full_path(self, full_path: str, is_custom_type: bool) -> DataType:  # noqa: FBT001
        """Create a DataType from a fully qualified Python path."""
        return self.data_type.from_import(Import.from_full_path(full_path), is_custom_type=is_custom_type)

    def get_data_type_from_value(self, value: Any) -> DataType:  # noqa: PLR0911
        """Infer a DataType from a Python value."""
        match value:
            case str():
                return self.get_data_type(Types.string)
            case bool():  # bool must come before int (bool is subclass of int)
                return self.get_data_type(Types.boolean)
            case int():
                return self.get_data_type(Types.integer)
            case float():
                return self.get_data_type(Types.float)
            case dict():
                return self.data_type.from_import(IMPORT_DICT)
            case list():
                return self.data_type.from_import(IMPORT_LIST)
        return self.get_data_type(Types.any)
