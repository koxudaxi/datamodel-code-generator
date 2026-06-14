"""Dynamic model generation module for datamodel-code-generator.

This module provides runtime generation of Pydantic v2 models from JSON Schema
or OpenAPI schemas.
"""

from __future__ import annotations

import ast
import builtins
import hashlib
import itertools
import json
import sys
import threading
import types
from enum import Enum
from pathlib import PurePath
from typing import TYPE_CHECKING, Any

import pydantic
from pydantic import BaseModel

from datamodel_code_generator import Error, generate, is_asyncapi, is_openapi
from datamodel_code_generator.config import GenerateConfig, _rebuild_generate_config
from datamodel_code_generator.enums import DataModelType, InputFileType
from datamodel_code_generator.parser._graph import stable_toposort

if TYPE_CHECKING:
    from collections.abc import Mapping

_dynamic_models_cache: dict[str, dict[str, type]] = {}
_dynamic_models_lock = threading.Lock()
_dynamic_module_counter = itertools.count(1)


def _is_init_file(path_tuple: tuple[str, ...]) -> bool:
    """Check if path tuple represents an __init__.py file."""
    return PurePath(path_tuple[-1]).stem == "__init__"


def _path_to_module_name(package_name: str, path_tuple: tuple[str, ...]) -> str:
    """Convert path tuple to module name."""
    parts = [package_name, *path_tuple[:-1]]
    stem = PurePath(path_tuple[-1]).stem
    if stem != "__init__":
        parts.append(stem)
    return ".".join(parts)


def _execute_single_module(code: str, *, include_private_models: bool = False) -> dict[str, type]:
    """Execute single module code and extract models."""
    namespace: dict[str, Any] = {"__builtins__": builtins.__dict__}
    exec(code, namespace)  # noqa: S102

    models = _extract_models(namespace, include_private=include_private_models)

    for obj in models.values():
        if issubclass(obj, BaseModel) and hasattr(obj, "__pydantic_generic_metadata__"):
            obj.model_rebuild(_types_namespace=namespace)

    return models


def _get_relative_imports(code: str) -> set[str]:
    """Extract relative import module names from code using AST."""
    imports: set[str] = set()
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 1:
            if node.module:
                imports.add(node.module.split(".")[0])
            else:
                imports.update(alias.name for alias in node.names)
    return imports


def _build_module_edges(modules: dict[tuple[str, ...], str]) -> dict[tuple[str, ...], set[tuple[str, ...]]]:
    """Build dependency edges for topological sort.

    Returns edges where edges[u] contains v means u must come before v.
    """
    name_to_path: dict[str, tuple[str, ...]] = {}
    for path in modules:
        if (filepath := PurePath(path[-1])).suffix == ".py" and (name := filepath.stem) != "__init__":
            name_to_path[name] = path

    edges: dict[tuple[str, ...], set[tuple[str, ...]]] = {path: set() for path in modules}
    for path, code in modules.items():
        for imported in _get_relative_imports(code):
            if dep_path := name_to_path.get(imported):
                edges[dep_path].add(path)
    return edges


def _execute_multi_module(
    modules: dict[tuple[str, ...], str],
    *,
    include_private_models: bool = False,
) -> dict[str, type]:
    """Execute multiple modules and extract models."""
    package_name = f"_dcg_dynamic_{next(_dynamic_module_counter)}"

    created_modules: list[str] = []
    all_namespaces: dict[str, dict[str, Any]] = {}

    try:
        nodes = list(modules.keys())
        nodes.sort(key=lambda p: (_is_init_file(p), p))
        node_index = {node: i for i, node in enumerate(nodes)}
        edges = _build_module_edges(modules)
        sorted_paths = stable_toposort(nodes, edges, key=node_index.__getitem__)

        for path_tuple in sorted_paths:
            module_name = _path_to_module_name(package_name, path_tuple)
            module = types.ModuleType(module_name)
            module.__dict__["__builtins__"] = builtins.__dict__
            module.__package__ = package_name if _is_init_file(path_tuple) else ".".join(module_name.split(".")[:-1])
            sys.modules[module_name] = module
            created_modules.append(module_name)
            all_namespaces[module_name] = module.__dict__

        if package_name not in sys.modules:
            pkg = types.ModuleType(package_name)
            pkg.__path__ = []
            pkg.__package__ = package_name
            sys.modules[package_name] = pkg
            created_modules.insert(0, package_name)

        for path_tuple in sorted_paths:
            module_name = _path_to_module_name(package_name, path_tuple)
            exec(modules[path_tuple], all_namespaces[module_name])  # noqa: S102

        models: dict[str, type] = {}
        combined_namespace: dict[str, Any] = {}
        for ns in all_namespaces.values():
            combined_namespace.update(ns)
            models.update(_extract_models(ns, include_private=include_private_models))

        for obj in models.values():
            if issubclass(obj, BaseModel) and hasattr(obj, "__pydantic_generic_metadata__"):
                obj.model_rebuild(_types_namespace=combined_namespace)

        return models
    finally:
        for module_name in reversed(created_modules):
            sys.modules.pop(module_name, None)


def _should_extract_model_name(name: str, *, include_private: bool = False) -> bool:
    if include_private:
        return True
    return not name.startswith("_")


def _extract_models(namespace: dict[str, Any], *, include_private: bool = False) -> dict[str, type]:
    """Extract model and enum classes from namespace."""
    return {
        k: v
        for k, v in namespace.items()
        if isinstance(v, type)
        and _should_extract_model_name(k, include_private=include_private)
        and ((issubclass(v, BaseModel) and v is not BaseModel) or (issubclass(v, Enum) and v is not Enum))
    }


def _make_cache_key(schema: Mapping[str, Any], config: GenerateConfig) -> str | None:
    """Create cache key from schema and config.

    Returns None if the schema is not JSON-serializable.
    """
    try:
        schema_json = json.dumps(dict(schema), sort_keys=True, separators=(",", ":"))
        config_json = config.model_dump_json(exclude_defaults=True)
    except (TypeError, ValueError):
        return None
    schema_digest = hashlib.sha256(schema_json.encode()).hexdigest()
    config_digest = hashlib.sha256(config_json.encode()).hexdigest()
    return f"{schema_digest}:{len(schema_json)}:{config_digest}:{len(config_json)}"


def _detect_schema_input_file_type(input_: Mapping[str, Any]) -> InputFileType:
    """Detect schema input type for dynamic model generation."""
    if is_asyncapi(input_):
        return InputFileType.AsyncAPI
    if is_openapi(input_):
        return InputFileType.OpenAPI
    return InputFileType.JsonSchema


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
        - Supports both single-module and multi-module output

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
    if pydantic.VERSION < "2.0.0":  # pragma: no cover
        msg = f"generate_dynamic_models requires Pydantic v2, found v{pydantic.VERSION}"
        raise Error(msg)

    _rebuild_generate_config()

    if config is None:
        config = GenerateConfig(
            input_file_type=_detect_schema_input_file_type(input_),
            output_model_type=DataModelType.PydanticV2BaseModel,
        )
    elif config.input_file_type == InputFileType.Auto:
        config = config.model_copy(update={"input_file_type": _detect_schema_input_file_type(input_)})

    cache_key = _make_cache_key(input_, config)
    use_cache = cache_size > 0 and cache_key is not None

    with _dynamic_models_lock:
        if use_cache:
            assert cache_key is not None
            if (cached_models := _dynamic_models_cache.get(cache_key)) is not None:
                return cached_models

        result = generate(input_=input_, config=config)
        if result is None:  # pragma: no cover
            msg = "generate() returned None"
            raise Error(msg)
        include_private_models = config.allow_leading_underscore_class_name
        models = (
            _execute_single_module(result, include_private_models=include_private_models)
            if isinstance(result, str)
            else _execute_multi_module(result, include_private_models=include_private_models)
        )

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
    with _dynamic_models_lock:
        count = len(_dynamic_models_cache)
        _dynamic_models_cache.clear()
        return count
