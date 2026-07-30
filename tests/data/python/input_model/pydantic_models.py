"""Pydantic models for --input-model tests."""

from __future__ import annotations

import typing
from collections import UserDict
from collections.abc import Callable, Mapping, Sequence
from enum import Enum, Flag, IntFlag
from typing import Any, Concatenate, FrozenSet, Generic, Literal, Optional, ParamSpec, Set, Type, TypeVar, Union

from pydantic import BaseModel

from tests.data.python.input_model.literal_enum_first import Status as FirstStatus
from tests.data.python.input_model.literal_enum_second import Status as SecondStatus

# Custom generic type for testing generic type import
TK = TypeVar("TK")
TV = TypeVar("TV")
P = ParamSpec("P")


class CustomGenericDict(UserDict[TK, TV], Generic[TK, TV]):
    """Custom generic dict for testing generic type import."""

    pass


class NotCallableGeneric(Generic[TV]):
    """Custom generic whose name must not determine Callable semantics."""


class LiteralValueEnum(Enum):
    """Enum member used as a legal Literal value."""

    VALUE = "typing.enum"
    ALIAS = "typing.enum"  # noqa: PIE796


class LiteralFlagValue(Flag):
    """Flag members used as legal and rejected Literal values."""

    READ = 1
    WRITE = 2
    EXECUTE = 4
    READ_WRITE = READ | WRITE


class LiteralIntFlagValue(IntFlag):
    """IntFlag members used as legal and rejected Literal values."""

    READ = 1
    WRITE = 2
    EXECUTE = 4
    READ_WRITE = READ | WRITE


class LiteralEnumContainer:
    """Container used to verify nested enum qualification."""

    class NestedValue(Enum):
        """Nested enum member used as a legal Literal value."""

        VALUE = "typing.nested-enum"


class User(BaseModel):
    """User model with basic fields."""

    name: str
    age: int


class Tag(BaseModel):
    """Nested model for testing x-python-type with nested models."""

    values: FrozenSet[str]


class ModelWithPythonTypes(BaseModel):
    """Model with types that need x-python-type preservation."""

    tags: Set[str]
    frozen_tags: FrozenSet[int]
    metadata: Mapping[str, int]
    items: Sequence[str]
    nested_mapping: Mapping[str, Set[int]]
    tag_obj: Tag
    nested_in_list: list[Set[int]]
    optional_set: Optional[Set[str]]
    nullable_frozenset: Union[None, FrozenSet[str]]
    optional_mapping: Mapping[str, str] | None


class RecursiveNode(BaseModel):
    """Recursive model for testing cycle detection."""

    value: Set[str]
    children: Optional[list[RecursiveNode]] = None


class ModelWithCallableTypes(BaseModel):
    """Model with Callable and other unserializable types."""

    callback: Callable[[str], str]
    multi_param_callback: Callable[[int, int], bool]
    variadic_callback: Callable[..., Any]
    no_param_callback: Callable[[], None]
    optional_callback: Callable[[str], str] | None
    type_field: Type[BaseModel]
    nested_callable: list[Callable[[str], int]]


class NestedCallableModel(BaseModel):
    """Model with nested Callable types for $defs coverage."""

    handler: Callable[[str], int]


class ModelWithNestedCallable(BaseModel):
    """Model referencing another model with Callable to test $defs processing."""

    nested: NestedCallableModel
    own_callback: Callable[[int], str]


class CustomClass:
    """Custom class for testing handle_invalid_for_json_schema."""

    pass


class ModelWithCustomClass(BaseModel):
    """Model with a custom class that triggers handle_invalid_for_json_schema."""

    model_config = {"arbitrary_types_allowed": True}
    custom_obj: CustomClass


class ModelWithUnionCallable(BaseModel):
    """Model with Union of Callable and other types to test Union serialization."""

    union_callback: Union[Callable[[str], str], int]
    raw_callable: Callable  # Callable without type args


class ModelWithCustomGeneric(BaseModel):
    """Model with custom generic type that requires module import."""

    model_config = {"arbitrary_types_allowed": True}
    custom_dict: CustomGenericDict[str, int]
    optional_custom_dict: CustomGenericDict[str, str] | None


class ModelWithStructuredGenericArguments(BaseModel):
    """Model with structured generic, callable, and literal arguments."""

    model_config = {"arbitrary_types_allowed": True}
    callable_like_name: NotCallableGeneric[int]
    literal_arguments: NotCallableGeneric[
        Literal["typing.foo", "Callable", 0, True, None, b"bytes"]  # noqa: PYI061
    ]
    enum_literal: NotCallableGeneric[Literal[LiteralValueEnum.VALUE]]
    flag_literal: NotCallableGeneric[Literal[LiteralFlagValue.READ]]
    named_composite_flag_literal: NotCallableGeneric[Literal[LiteralFlagValue.READ_WRITE]]
    int_flag_literal: NotCallableGeneric[Literal[LiteralIntFlagValue.READ]]
    named_composite_int_flag_literal: NotCallableGeneric[Literal[LiteralIntFlagValue.READ_WRITE]]
    nested_enum_literal: NotCallableGeneric[Literal[LiteralEnumContainer.NestedValue.VALUE]]
    mixed_enum_literal: NotCallableGeneric[Literal[LiteralValueEnum.VALUE, LiteralEnumContainer.NestedValue.VALUE]]
    same_named_enum_literal: NotCallableGeneric[Literal[FirstStatus.ACTIVE, SecondStatus.INACTIVE]]
    fixed_callable: NotCallableGeneric[Callable[[int, str], bool]]
    typing_callable: NotCallableGeneric[typing.Callable[[bytes], float]]
    variadic_callable: NotCallableGeneric[Callable[..., str]]
    empty_callable: NotCallableGeneric[Callable[[], None]]
    raw_callable: NotCallableGeneric[Callable]
    parameter_specification: NotCallableGeneric[Callable[P, int]]
    concatenated: NotCallableGeneric[Callable[Concatenate[str, P], int]]


# Import DefaultPutDict for testing real-world generic type import
from datamodel_code_generator.parser import DefaultPutDict  # noqa: E402


class ModelWithDefaultPutDict(BaseModel):
    """Model with DefaultPutDict to test generic type import from parser module."""

    model_config = {"arbitrary_types_allowed": True}
    cache: DefaultPutDict[str, str]
    optional_cache: DefaultPutDict[str, int] | None
