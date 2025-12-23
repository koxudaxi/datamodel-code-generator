"""Utility functions and Pydantic version compatibility helpers.

Provides Pydantic version detection (PYDANTIC_V2), YAML/TOML loading,
and version-compatible decorators (model_validator, field_validator).
"""

from __future__ import annotations

import copy
import re
import warnings
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Literal, TypeVar, overload

import pydantic
from packaging import version
from pydantic import BaseModel as _BaseModel

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

PYDANTIC_VERSION = version.parse(pydantic.VERSION if isinstance(pydantic.VERSION, str) else str(pydantic.VERSION))

PYDANTIC_V2: bool = version.parse("2.0b3") <= PYDANTIC_VERSION
PYDANTIC_V2_11: bool = version.parse("2.11") <= PYDANTIC_VERSION

try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:  # pragma: no cover
    from yaml import SafeLoader

try:
    from tomllib import load as load_tomllib  # type: ignore[ignoreMissingImports]
except ImportError:
    from tomli import load as load_tomllib  # type: ignore[ignoreMissingImports]


def load_toml(path: Path) -> dict[str, Any]:
    """Load and parse a TOML file."""
    with path.open("rb") as f:
        return load_tomllib(f)


SafeLoaderTemp = copy.deepcopy(SafeLoader)
SafeLoaderTemp.yaml_constructors = copy.deepcopy(SafeLoader.yaml_constructors)
SafeLoaderTemp.yaml_implicit_resolvers = copy.deepcopy(SafeLoader.yaml_implicit_resolvers)
SafeLoaderTemp.add_constructor(
    "tag:yaml.org,2002:timestamp",
    SafeLoaderTemp.yaml_constructors["tag:yaml.org,2002:str"],
)

_YAML_1_2_BOOL_PATTERN = re.compile(r"^(?:true|false|True|False|TRUE|FALSE)$")
_YAML_DEPRECATED_BOOL_VALUES = {"True", "False", "TRUE", "FALSE"}


def _construct_yaml_bool_with_warning(loader: Any, node: Any) -> bool:
    value = loader.construct_scalar(node)
    if value in _YAML_DEPRECATED_BOOL_VALUES:
        warnings.warn(
            f"YAML bool '{value}' is deprecated. Use lowercase 'true' or 'false' instead. "
            f"In a future version, only lowercase booleans will be recognized.",
            DeprecationWarning,
            stacklevel=6,
        )
    return value in {"true", "True", "TRUE"}


for key in list(SafeLoaderTemp.yaml_implicit_resolvers.keys()):
    SafeLoaderTemp.yaml_implicit_resolvers[key] = [
        (tag, pattern)
        for tag, pattern in SafeLoaderTemp.yaml_implicit_resolvers[key]
        if tag != "tag:yaml.org,2002:bool"
    ]
    if not SafeLoaderTemp.yaml_implicit_resolvers[key]:
        del SafeLoaderTemp.yaml_implicit_resolvers[key]
for key in ["t", "f", "T", "F"]:
    SafeLoaderTemp.yaml_implicit_resolvers.setdefault(key, []).append((
        "tag:yaml.org,2002:bool",
        _YAML_1_2_BOOL_PATTERN,
    ))
SafeLoaderTemp.add_constructor("tag:yaml.org,2002:bool", _construct_yaml_bool_with_warning)

SafeLoader = SafeLoaderTemp

Model = TypeVar("Model", bound=_BaseModel)
T = TypeVar("T")


@overload
def model_validator(
    mode: Literal["before"],
) -> (
    Callable[[Callable[[type[Model], T], T]], Callable[[type[Model], T], T]]
    | Callable[[Callable[[Model, T], T]], Callable[[Model, T], T]]
): ...


@overload
def model_validator(
    mode: Literal["after"],
) -> (
    Callable[[Callable[[type[Model], T], T]], Callable[[type[Model], T], T]]
    | Callable[[Callable[[Model, T], T]], Callable[[Model, T], T]]
    | Callable[[Callable[[Model], Model]], Callable[[Model], Model]]
): ...


@overload
def model_validator() -> (
    Callable[[Callable[[type[Model], T], T]], Callable[[type[Model], T], T]]
    | Callable[[Callable[[Model, T], T]], Callable[[Model, T], T]]
    | Callable[[Callable[[Model], Model]], Callable[[Model], Model]]
): ...


def model_validator(  # pyright: ignore[reportInconsistentOverload]
    mode: Literal["before", "after"] = "after",
) -> (
    Callable[[Callable[[type[Model], T], T]], Callable[[type[Model], T], T]]
    | Callable[[Callable[[Model, T], T]], Callable[[Model, T], T]]
    | Callable[[Callable[[Model], Model]], Callable[[Model], Model]]
):
    """Decorate model validators for both Pydantic v1 and v2."""

    @overload
    def inner(method: Callable[[type[Model], T], T]) -> Callable[[type[Model], T], T]: ...

    @overload
    def inner(method: Callable[[Model, T], T]) -> Callable[[Model, T], T]: ...

    @overload
    def inner(method: Callable[[Model], Model]) -> Callable[[Model], Model]: ...

    def inner(
        method: Callable[[type[Model], T], T] | Callable[[Model, T], T] | Callable[[Model], Model],
    ) -> Callable[[type[Model], T], T] | Callable[[Model, T], T] | Callable[[Model], Model]:
        if PYDANTIC_V2:
            from pydantic import model_validator as model_validator_v2  # noqa: PLC0415

            if mode == "before":
                return model_validator_v2(mode=mode)(classmethod(method))  # type: ignore[reportReturnType]
            return model_validator_v2(mode=mode)(method)  # type: ignore[reportReturnType]
        from pydantic import root_validator  # noqa: PLC0415

        return root_validator(method, pre=mode == "before")  # pyright: ignore[reportCallIssue]

    return inner


def field_validator(
    field_name: str,
    *fields: str,
    mode: Literal["before", "after"] = "after",
) -> Callable[[Any], Callable[[BaseModel, Any], Any]]:
    """Decorate field validators for both Pydantic v1 and v2."""

    def inner(method: Callable[[Model, Any], Any]) -> Callable[[Model, Any], Any]:
        if PYDANTIC_V2:
            from pydantic import field_validator as field_validator_v2  # noqa: PLC0415

            return field_validator_v2(field_name, *fields, mode=mode)(method)
        from pydantic import validator  # noqa: PLC0415

        return validator(field_name, *fields, pre=mode == "before")(method)  # pyright: ignore[reportReturnType]

    return inner


if PYDANTIC_V2:
    from pydantic import ConfigDict
else:
    ConfigDict = dict


class BaseModel(_BaseModel):
    """Base Pydantic model with version-compatible configuration."""

    if PYDANTIC_V2:
        model_config = ConfigDict(strict=False)  # pyright: ignore[reportAssignmentType]


_UNDER_SCORE_1: re.Pattern[str] = re.compile(r"([^_])([A-Z][a-z]+)")
_UNDER_SCORE_2: re.Pattern[str] = re.compile(r"([a-z0-9])([A-Z])")


@lru_cache
def camel_to_snake(string: str) -> str:
    """Convert camelCase or PascalCase to snake_case."""
    subbed = _UNDER_SCORE_1.sub(r"\1_\2", string)
    return _UNDER_SCORE_2.sub(r"\1_\2", subbed).lower()


def model_dump(obj: _BaseModel, **kwargs: Any) -> dict[str, Any]:
    """Version-compatible model serialization (dict/model_dump)."""
    if PYDANTIC_V2:
        return obj.model_dump(**kwargs)
    return obj.dict(**kwargs)  # type: ignore[reportDeprecated]


def model_validate(cls: type[Model], obj: Any) -> Model:
    """Version-compatible model validation (parse_obj/model_validate)."""
    if PYDANTIC_V2:
        return cls.model_validate(obj)
    return cls.parse_obj(obj)  # type: ignore[reportDeprecated]


def get_fields_set(obj: _BaseModel) -> set[str]:
    """Version-compatible access to fields set (__fields_set__/model_fields_set)."""
    if PYDANTIC_V2:
        return obj.model_fields_set
    return obj.__fields_set__  # type: ignore[reportDeprecated]


def model_copy(obj: Model, **kwargs: Any) -> Model:
    """Version-compatible model copy (copy/model_copy)."""
    if PYDANTIC_V2:
        return obj.model_copy(**kwargs)
    return obj.copy(**kwargs)  # type: ignore[reportDeprecated]
