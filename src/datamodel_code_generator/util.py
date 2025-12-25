"""Utility functions and Pydantic version compatibility helpers.

Provides Pydantic version detection (PYDANTIC_V2), YAML/TOML loading,
and version-compatible decorators (model_validator, field_validator).
"""

from __future__ import annotations

import re
import warnings
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Literal, TypeVar, overload

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from pydantic import BaseModel as _BaseModel

try:
    from tomllib import load as load_tomllib  # type: ignore[ignoreMissingImports]
except ImportError:
    from tomli import load as load_tomllib  # type: ignore[ignoreMissingImports]


def load_toml(path: Path) -> dict[str, Any]:
    """Load and parse a TOML file."""
    with path.open("rb") as f:
        return load_tomllib(f)


@lru_cache(maxsize=1)
def get_pydantic_version() -> tuple[Any, bool, bool]:
    """Get pydantic version info lazily. Returns (version, is_v2, is_v2_11)."""
    # Apply pydantic patch before importing pydantic
    from datamodel_code_generator.pydantic_patch import apply_patch  # noqa: PLC0415

    apply_patch()

    import pydantic  # noqa: PLC0415
    from packaging import version  # noqa: PLC0415

    pydantic_version = version.parse(pydantic.VERSION if isinstance(pydantic.VERSION, str) else str(pydantic.VERSION))
    is_v2 = version.parse("2.0b3") <= pydantic_version
    is_v2_11 = version.parse("2.11") <= pydantic_version
    return pydantic_version, is_v2, is_v2_11


_is_v2: bool | None = None


def is_pydantic_v2() -> bool:
    """Check if pydantic v2 is installed."""
    global _is_v2  # noqa: PLW0603
    if _is_v2 is None:  # pragma: no branch
        _is_v2 = get_pydantic_version()[1]
    return _is_v2


_YAML_1_2_BOOL_PATTERN = re.compile(r"^(?:true|false|True|False|TRUE|FALSE)$")
_YAML_DEPRECATED_BOOL_VALUES = {"True", "False", "TRUE", "FALSE"}


def _construct_yaml_bool_with_warning(loader: Any, node: Any) -> bool:
    value = loader.construct_scalar(node)
    if value in _YAML_DEPRECATED_BOOL_VALUES:  # pragma: no cover
        warnings.warn(
            f"YAML bool '{value}' is deprecated. Use lowercase 'true' or 'false' instead. "
            f"In a future version, only lowercase booleans will be recognized.",
            DeprecationWarning,
            stacklevel=6,
        )
    return value in {"true", "True", "TRUE"}


@lru_cache(maxsize=1)
def get_safe_loader() -> type:
    """Get customized SafeLoader lazily."""
    try:
        from yaml import CSafeLoader as _SafeLoader  # noqa: PLC0415
    except ImportError:  # pragma: no cover
        from yaml import SafeLoader as _SafeLoader  # noqa: PLC0415

    class CustomSafeLoader(_SafeLoader):  # type: ignore[valid-type,misc]
        """SafeLoader with YAML 1.2 bool handling and timestamp-as-string."""

        yaml_constructors = _SafeLoader.yaml_constructors.copy()
        yaml_implicit_resolvers = {  # noqa: RUF012
            k: v
            for k, v in (
                (k, [(tag, pat) for tag, pat in v if tag != "tag:yaml.org,2002:bool"])
                for k, v in _SafeLoader.yaml_implicit_resolvers.items()
            )
            if v
        }

    CustomSafeLoader.yaml_constructors["tag:yaml.org,2002:timestamp"] = CustomSafeLoader.yaml_constructors[
        "tag:yaml.org,2002:str"
    ]
    for key in ["t", "f", "T", "F"]:
        CustomSafeLoader.yaml_implicit_resolvers.setdefault(key, []).append((
            "tag:yaml.org,2002:bool",
            _YAML_1_2_BOOL_PATTERN,
        ))
    CustomSafeLoader.yaml_constructors["tag:yaml.org,2002:bool"] = _construct_yaml_bool_with_warning

    return CustomSafeLoader


Model = TypeVar("Model", bound="_BaseModel")  # pyright: ignore[reportInvalidTypeForm]
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
        if is_pydantic_v2():
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
) -> Callable[[Any], Callable[[Any, Any], Any]]:
    """Decorate field validators for both Pydantic v1 and v2."""

    def inner(method: Callable[[Model, Any], Any]) -> Callable[[Model, Any], Any]:
        if is_pydantic_v2():
            from pydantic import field_validator as field_validator_v2  # noqa: PLC0415

            return field_validator_v2(field_name, *fields, mode=mode)(method)
        from pydantic import validator  # noqa: PLC0415

        return validator(field_name, *fields, pre=mode == "before")(method)  # pyright: ignore[reportReturnType]

    return inner


@lru_cache(maxsize=1)
def _get_config_dict() -> type:
    """Get ConfigDict type lazily. Only used with pydantic v2."""
    from pydantic import ConfigDict  # noqa: PLC0415

    return ConfigDict


class _ConfigDictProxy:
    """Proxy for lazy ConfigDict access."""

    def __call__(self, **kwargs: Any) -> Any:
        return _get_config_dict()(**kwargs)


ConfigDict: type = _ConfigDictProxy()  # type: ignore[assignment]


@lru_cache(maxsize=1)
def _get_base_model_class() -> type:
    """Get version-compatible BaseModel class lazily."""
    from pydantic import BaseModel as _PydanticBaseModel  # noqa: PLC0415

    if is_pydantic_v2():
        from pydantic import ConfigDict as _ConfigDict  # noqa: PLC0415

        class _BaseModelV2(_PydanticBaseModel):
            model_config = _ConfigDict(strict=False)

        return _BaseModelV2
    return _PydanticBaseModel


_BaseModel: type | None = None


def __getattr__(name: str) -> Any:
    """Provide lazy access to BaseModel and SafeLoader."""
    global _BaseModel  # noqa: PLW0603
    if name == "BaseModel":
        if _BaseModel is None:
            _BaseModel = _get_base_model_class()
        return _BaseModel
    if name == "SafeLoader":
        return get_safe_loader()
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


_UNDER_SCORE_1: re.Pattern[str] = re.compile(r"([^_])([A-Z][a-z]+)")
_UNDER_SCORE_2: re.Pattern[str] = re.compile(r"([a-z0-9])([A-Z])")


@lru_cache
def camel_to_snake(string: str) -> str:
    """Convert camelCase or PascalCase to snake_case."""
    subbed = _UNDER_SCORE_1.sub(r"\1_\2", string)
    return _UNDER_SCORE_2.sub(r"\1_\2", subbed).lower()


def model_dump(obj: _BaseModel, **kwargs: Any) -> dict[str, Any]:  # pyright: ignore[reportInvalidTypeForm]
    """Version-compatible model serialization (dict/model_dump)."""
    if is_pydantic_v2():
        return obj.model_dump(**kwargs)
    return obj.dict(**kwargs)  # type: ignore[reportDeprecated]


def model_validate(cls: type[Model], obj: Any) -> Model:
    """Version-compatible model validation (parse_obj/model_validate)."""
    if is_pydantic_v2():
        return cls.model_validate(obj)
    return cls.parse_obj(obj)  # type: ignore[reportDeprecated]


def get_fields_set(obj: _BaseModel) -> set[str]:  # pyright: ignore[reportInvalidTypeForm]
    """Version-compatible access to fields set (__fields_set__/model_fields_set)."""
    if is_pydantic_v2():
        return obj.model_fields_set
    return obj.__fields_set__  # type: ignore[reportDeprecated]


def model_copy(obj: Model, **kwargs: Any) -> Model:
    """Version-compatible model copy (copy/model_copy)."""
    if is_pydantic_v2():
        return obj.model_copy(**kwargs)
    return obj.copy(**kwargs)  # type: ignore[reportDeprecated]
