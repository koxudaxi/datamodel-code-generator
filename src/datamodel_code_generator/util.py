"""Utility functions for YAML/TOML loading and lazy BaseModel access."""

from __future__ import annotations

import re
import warnings
from functools import lru_cache
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

try:
    from tomllib import load as load_tomllib  # type: ignore[ignoreMissingImports]
except ImportError:  # pragma: no cover
    from tomli import load as load_tomllib  # type: ignore[ignoreMissingImports]


def load_toml(path: Path) -> dict[str, Any]:
    """Load and parse a TOML file."""
    with path.open("rb") as f:
        return load_tomllib(f)


_YAML_1_2_BOOL_PATTERN = re.compile(r"^(?:true|false|True|False|TRUE|FALSE)$")
_YAML_DEPRECATED_BOOL_VALUES = {"True", "False", "TRUE", "FALSE"}
# Pattern for scientific notation without decimal point (e.g., 1e-5, 1E+10)
# Standard YAML only matches floats with decimal points, missing patterns like "1e-5"
_YAML_SCIENTIFIC_NOTATION_PATTERN = re.compile(r"^[-+]?[0-9][0-9_]*[eE][-+]?[0-9]+$")


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

    # Add scientific notation without decimal point (e.g., 1e-5) as float
    for key in ["-", "+", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]:
        CustomSafeLoader.yaml_implicit_resolvers.setdefault(key, []).append((
            "tag:yaml.org,2002:float",
            _YAML_SCIENTIFIC_NOTATION_PATTERN,
        ))

    return CustomSafeLoader


@lru_cache(maxsize=1)
def _get_base_model_class() -> type:
    """Get BaseModel class with strict=False config lazily."""
    from pydantic import BaseModel as _PydanticBaseModel  # noqa: PLC0415
    from pydantic import ConfigDict as _ConfigDict  # noqa: PLC0415

    class _BaseModelV2(_PydanticBaseModel):
        model_config = _ConfigDict(strict=False)

    return _BaseModelV2


_BaseModel: type | None = None


def create_module_getattr(
    module_name: str,
    lazy_imports: dict[str, tuple[str, str]],
) -> Callable[[str], Any]:
    """Create a __getattr__ function for lazy module imports.

    Args:
        module_name: The name of the module (typically __name__).
        lazy_imports: Mapping of attribute name to (module_path, attribute_name).

    Returns:
        A __getattr__ function that lazily imports the specified attributes.

    Example:
        __getattr__ = create_module_getattr(__name__, {
            "MyClass": ("mypackage.mymodule", "MyClass"),
        })
    """
    from importlib import import_module  # noqa: PLC0415

    def _getattr(name: str) -> Any:
        if name in lazy_imports:
            module_path, attr_name = lazy_imports[name]
            module = import_module(module_path)
            return getattr(module, attr_name)
        msg = f"module {module_name!r} has no attribute {name!r}"
        raise AttributeError(msg)

    return _getattr


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
