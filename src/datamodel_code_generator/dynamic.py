"""Dynamic model generation module for datamodel-code-generator.

This module provides runtime generation of Pydantic v2 models from JSON Schema
or OpenAPI schemas.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping

    from datamodel_code_generator.config import GenerateConfig


_dynamic_models_cache: dict[str, dict[str, type]] = {}
_dynamic_models_lock: Any = None
_dynamic_models_lock_init: Any = None


def _get_dynamic_models_lock() -> Any:
    """Get or create the lock for dynamic models cache (thread-safe lazy initialization)."""
    import threading  # noqa: PLC0415

    global _dynamic_models_lock, _dynamic_models_lock_init  # noqa: PLW0603
    if _dynamic_models_lock_init is None:
        _dynamic_models_lock_init = threading.Lock()
    if _dynamic_models_lock is None:
        with _dynamic_models_lock_init:
            if _dynamic_models_lock is None:
                _dynamic_models_lock = threading.Lock()
    return _dynamic_models_lock


def _make_cache_key(schema: Mapping[str, Any], config: GenerateConfig) -> str | None:
    """Create cache key from schema and config.

    Returns None if the schema is not JSON-serializable.
    """
    import hashlib  # noqa: PLC0415
    import json  # noqa: PLC0415

    try:
        config_dict = config.model_dump(mode="json", exclude_defaults=True)
        key_data = {
            "schema": dict(schema),
            "config": config_dict,
        }
        return hashlib.sha256(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
    except (TypeError, ValueError):
        return None


def generate_dynamic_models(
    input_: Mapping[str, Any],
    *,
    config: GenerateConfig | None = None,
    cache_size: int = 128,
) -> dict[str, type]:
    """Generate actual Python model classes from schema at runtime.

    This function creates real Python classes from JSON Schema or OpenAPI schemas
    using Pydantic's model creation. The generated models can be used immediately
    for validation and data processing.

    Args:
        input_: JSON Schema or OpenAPI schema as dict.
        config: A GenerateConfig object with generation options. If None, uses defaults.
        cache_size: Maximum number of schemas to cache. Set to 0 to disable caching.

    Returns:
        Dictionary mapping class names to model classes.

    Note:
        - Thread-safe (uses internal lock and cache)
        - Pydantic v2 only (v1 is not supported)
        - Not pickle-able (use model_dump() to serialize instances)
        - Cached by schema + config hash with FIFO eviction when cache_size is exceeded

    Example:
        >>> schema = {
        ...     "type": "object",
        ...     "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        ...     "required": ["name"],
        ... }
        >>> models = generate_dynamic_models(schema)
        >>> User = models["Model"]
        >>> user = User(name="John", age=30)
        >>> user.model_dump()
        {'name': 'John', 'age': 30}
    """
    import builtins  # noqa: PLC0415
    from enum import Enum  # noqa: PLC0415

    import pydantic  # noqa: PLC0415
    from pydantic import BaseModel  # noqa: PLC0415

    from datamodel_code_generator import Error, generate, is_openapi  # noqa: PLC0415
    from datamodel_code_generator.config import GenerateConfig as GenerateConfigClass  # noqa: PLC0415
    from datamodel_code_generator.enums import DataModelType, InputFileType  # noqa: PLC0415
    from datamodel_code_generator.model.pydantic_v2 import UnionMode  # noqa: PLC0415
    from datamodel_code_generator.types import StrictTypes  # noqa: PLC0415

    if pydantic.VERSION < "2.0.0":  # pragma: no cover
        msg = f"generate_dynamic_models requires Pydantic v2, found v{pydantic.VERSION}"
        raise Error(msg)

    GenerateConfigClass.model_rebuild(_types_namespace={"StrictTypes": StrictTypes, "UnionMode": UnionMode})

    if config is None:
        if is_openapi(input_):
            config = GenerateConfigClass(
                input_file_type=InputFileType.OpenAPI,
                output_model_type=DataModelType.PydanticV2BaseModel,
            )
        else:
            config = GenerateConfigClass(
                input_file_type=InputFileType.JsonSchema,
                output_model_type=DataModelType.PydanticV2BaseModel,
            )
    elif config.input_file_type == InputFileType.Auto:
        detected_type = InputFileType.OpenAPI if is_openapi(input_) else InputFileType.JsonSchema
        config = config.model_copy(update={"input_file_type": detected_type})

    cache_key = _make_cache_key(input_, config)
    use_cache = cache_size > 0 and cache_key is not None

    if use_cache and cache_key in _dynamic_models_cache:
        return _dynamic_models_cache[cache_key]

    lock = _get_dynamic_models_lock()
    with lock:
        if use_cache and cache_key in _dynamic_models_cache:
            return _dynamic_models_cache[cache_key]

        result = generate(input_=input_, config=config)
        if not isinstance(result, str):  # pragma: no cover
            msg = "generate_dynamic_models only supports single-module output"
            raise Error(msg)
        code: str = result

        namespace: dict[str, Any] = {"__builtins__": builtins.__dict__}
        exec(code, namespace)  # noqa: S102

        models = {
            k: v
            for k, v in namespace.items()
            if isinstance(v, type)
            and not k.startswith("_")
            and ((issubclass(v, BaseModel) and v is not BaseModel) or (issubclass(v, Enum) and v is not Enum))
        }

        for obj in models.values():
            if issubclass(obj, BaseModel) and hasattr(obj, "__pydantic_generic_metadata__"):
                obj.model_rebuild(_types_namespace=namespace)

        if use_cache:
            while len(_dynamic_models_cache) >= cache_size:
                oldest_key = next(iter(_dynamic_models_cache))
                del _dynamic_models_cache[oldest_key]
            _dynamic_models_cache[cache_key] = models  # type: ignore[index]

        return models


def clear_dynamic_models_cache() -> int:
    """Clear the dynamic models cache.

    Returns:
        Number of cached entries that were cleared.
    """
    lock = _get_dynamic_models_lock()
    with lock:
        count = len(_dynamic_models_cache)
        _dynamic_models_cache.clear()
        return count
