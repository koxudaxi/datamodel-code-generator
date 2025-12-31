"""Pydantic models for --input-model tests."""

from __future__ import annotations

from collections import UserDict
from collections.abc import Callable, Mapping, Sequence
from typing import Any, FrozenSet, Generic, Optional, Set, Type, TypeVar, Union

from pydantic import BaseModel

# Custom generic type for testing generic type import
TK = TypeVar("TK")
TV = TypeVar("TV")


class CustomGenericDict(UserDict[TK, TV], Generic[TK, TV]):
    """Custom generic dict for testing generic type import."""

    pass


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


# Import DefaultPutDict for testing real-world generic type import
from datamodel_code_generator.parser import DefaultPutDict  # noqa: E402


class ModelWithDefaultPutDict(BaseModel):
    """Model with DefaultPutDict to test generic type import from parser module."""

    model_config = {"arbitrary_types_allowed": True}
    cache: DefaultPutDict[str, str]
    optional_cache: DefaultPutDict[str, int] | None
