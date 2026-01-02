"""Tests for generate_dynamic_models function."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

import pydantic
import pytest
from inline_snapshot import snapshot

from datamodel_code_generator import (
    DataModelType,
    InputFileType,
    clear_dynamic_models_cache,
    generate_dynamic_models,
)
from datamodel_code_generator.config import GenerateConfig

if TYPE_CHECKING:
    from typing import Any

pytestmark = pytest.mark.skipif(pydantic.VERSION < "2.0.0", reason="generate_dynamic_models requires Pydantic v2")


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    """Clear cache before each test."""
    clear_dynamic_models_cache()


def test_simple_model() -> None:
    """Test generating a simple model."""
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
        },
        "required": ["name"],
    }
    models = generate_dynamic_models(schema)
    assert sorted(models.keys()) == snapshot(["Model"])
    model = models["Model"]
    instance = model(name="John", age=30)
    assert instance.model_dump() == snapshot({"name": "John", "age": 30})


def test_nested_models() -> None:
    """Test generating nested models."""
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "user": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                },
            },
        },
    }
    models = generate_dynamic_models(schema)
    assert sorted(models.keys()) == snapshot(["Model", "User"])


def test_enum_model() -> None:
    """Test generating model with enum."""
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["active", "inactive"],
            },
        },
    }
    models = generate_dynamic_models(schema)
    assert sorted(models.keys()) == snapshot(["Model", "Status"])
    model = models["Model"]
    status_enum = models["Status"]
    instance = model(status=status_enum.active)
    assert instance.status.value == snapshot("active")


def test_circular_reference() -> None:
    """Test generating models with circular references."""
    schema: dict[str, Any] = {
        "$defs": {
            "Node": {
                "type": "object",
                "properties": {
                    "value": {"type": "string"},
                    "children": {
                        "type": "array",
                        "items": {"$ref": "#/$defs/Node"},
                    },
                },
            },
        },
        "$ref": "#/$defs/Node",
    }
    models = generate_dynamic_models(schema)
    assert sorted(models.keys()) == snapshot(["Model", "Node", "RootModel"])
    node_class = models["Node"]
    node = node_class(value="root", children=[node_class(value="child", children=[])])
    assert node.model_dump() == snapshot({"value": "root", "children": [{"value": "child", "children": []}]})


def test_allof_inheritance() -> None:
    """Test generating models with allOf inheritance."""
    schema: dict[str, Any] = {
        "$defs": {
            "Base": {
                "type": "object",
                "properties": {"id": {"type": "integer"}},
            },
            "Extended": {
                "allOf": [
                    {"$ref": "#/$defs/Base"},
                    {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                    },
                ],
            },
        },
        "$ref": "#/$defs/Extended",
    }
    models = generate_dynamic_models(schema)
    assert sorted(models.keys()) == snapshot(["Base", "Extended", "Model", "RootModel"])
    extended = models["Extended"]
    instance = extended(id=1, name="test")
    assert instance.model_dump() == snapshot({"id": 1, "name": "test"})


def test_cache_hit() -> None:
    """Test that cached models are returned."""
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
    }
    models1 = generate_dynamic_models(schema)
    models2 = generate_dynamic_models(schema)
    assert models1 is models2


def test_cache_miss_different_schema() -> None:
    """Test that different schemas create different models."""
    schema1: dict[str, Any] = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
    }
    schema2: dict[str, Any] = {
        "type": "object",
        "properties": {"age": {"type": "integer"}},
    }
    models1 = generate_dynamic_models(schema1)
    models2 = generate_dynamic_models(schema2)
    assert models1 is not models2


def test_cache_miss_different_config() -> None:
    """Test that different configs create different cache entries."""
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
    }
    config1 = GenerateConfig(
        input_file_type=InputFileType.JsonSchema,
        output_model_type=DataModelType.PydanticV2BaseModel,
        class_name="User",
    )
    config2 = GenerateConfig(
        input_file_type=InputFileType.JsonSchema,
        output_model_type=DataModelType.PydanticV2BaseModel,
        class_name="Person",
    )
    models1 = generate_dynamic_models(schema, config=config1)
    models2 = generate_dynamic_models(schema, config=config2)
    assert models1 is not models2
    assert sorted(models1.keys()) == snapshot(["User"])
    assert sorted(models2.keys()) == snapshot(["Person"])


def test_cache_disabled() -> None:
    """Test that caching can be disabled."""
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
    }
    models1 = generate_dynamic_models(schema, cache_size=0)
    models2 = generate_dynamic_models(schema, cache_size=0)
    assert models1 is not models2


def test_cache_eviction() -> None:
    """Test that old entries are evicted when cache is full."""
    schemas = [{"type": "object", "properties": {f"field{i}": {"type": "string"}}} for i in range(5)]
    for schema in schemas:
        generate_dynamic_models(schema, cache_size=3)

    count = clear_dynamic_models_cache()
    assert count == snapshot(3)


def test_cache_shrinks_when_smaller_size_requested() -> None:
    """Test that cache shrinks when a smaller cache_size is used."""
    schemas = [{"type": "object", "properties": {f"field{i}": {"type": "string"}}} for i in range(5)]
    for schema in schemas:
        generate_dynamic_models(schema, cache_size=10)

    count = clear_dynamic_models_cache()
    assert count == snapshot(5)

    for schema in schemas:
        generate_dynamic_models(schema, cache_size=10)

    new_schema: dict[str, Any] = {
        "type": "object",
        "properties": {"new_field": {"type": "string"}},
    }
    generate_dynamic_models(new_schema, cache_size=2)

    count = clear_dynamic_models_cache()
    assert count == snapshot(2)


def test_clear_cache() -> None:
    """Test clearing the cache."""
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
    }
    generate_dynamic_models(schema)
    count = clear_dynamic_models_cache()
    assert count == snapshot(1)

    count = clear_dynamic_models_cache()
    assert count == snapshot(0)


def test_concurrent_same_schema() -> None:
    """Test concurrent access with the same schema."""
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
    }
    results: list[dict[str, type]] = []
    errors: list[Exception] = []

    def worker() -> None:
        try:
            models = generate_dynamic_models(schema)
            results.append(models)
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert len(results) == snapshot(10)
    assert all(r is results[0] for r in results)


def test_concurrent_different_schemas() -> None:
    """Test concurrent access with different schemas."""
    schemas = [{"type": "object", "properties": {f"field{i}": {"type": "string"}}} for i in range(5)]
    results: list[dict[str, type]] = []
    errors: list[Exception] = []

    def worker(schema: dict[str, Any]) -> None:
        try:
            models = generate_dynamic_models(schema)
            results.append(models)
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(worker, schemas)

    assert not errors
    assert len(results) == snapshot(5)


def test_numeric_constraints() -> None:
    """Test models with numeric constraints."""
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "age": {
                "type": "integer",
                "minimum": 0,
                "maximum": 150,
            },
        },
    }
    models = generate_dynamic_models(schema)
    model = models["Model"]
    instance = model(age=30)
    assert instance.model_dump() == snapshot({"age": 30})


def test_string_constraints() -> None:
    """Test models with string constraints."""
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "pattern": r"^[\w\.-]+@[\w\.-]+\.\w+$",
            },
        },
    }
    models = generate_dynamic_models(schema)
    assert sorted(models.keys()) == snapshot(["Model"])


def test_explicit_input_file_type() -> None:
    """Test passing explicit input_file_type via config."""
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
    }
    config = GenerateConfig(
        input_file_type=InputFileType.JsonSchema,
        output_model_type=DataModelType.PydanticV2BaseModel,
    )
    models = generate_dynamic_models(schema, config=config)
    assert sorted(models.keys()) == snapshot(["Model"])


def test_openapi_auto_detection() -> None:
    """Test that OpenAPI schemas are auto-detected."""
    openapi_schema: dict[str, Any] = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {},
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                }
            }
        },
    }
    models = generate_dynamic_models(openapi_schema)
    assert sorted(models.keys()) == snapshot(["User"])


def test_config_with_auto_input_type() -> None:
    """Test that input_file_type=Auto in config is auto-detected."""
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
    }
    config = GenerateConfig(class_name="User")
    models = generate_dynamic_models(schema, config=config)
    assert sorted(models.keys()) == snapshot(["User"])


def test_non_serializable_schema_skips_cache() -> None:
    """Test that non-JSON-serializable schemas skip caching."""
    from datamodel_code_generator.dynamic import _make_cache_key

    config = GenerateConfig(
        input_file_type=InputFileType.JsonSchema,
        output_model_type=DataModelType.PydanticV2BaseModel,
    )
    schema_with_non_serializable: dict[str, Any] = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "custom": object(),
    }
    cache_key = _make_cache_key(schema_with_non_serializable, config)
    assert cache_key is None


def test_cache_hit_inside_lock() -> None:
    """Test cache hit after acquiring lock (double-checked locking)."""
    from datamodel_code_generator import dynamic as dcg

    schema: dict[str, Any] = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
    }
    dcg._get_dynamic_models_lock()
    original_lock = dcg._dynamic_models_lock
    cached_models: dict[str, type] = {"Model": type("Model", (), {})}
    cache_populated = threading.Event()
    lock_acquired = threading.Event()
    result_holder: list[dict[str, type]] = []
    cache_key: str | None = None

    class InstrumentedLock:
        def __enter__(self) -> None:
            lock_acquired.set()
            cache_populated.wait(timeout=5)
            original_lock.__enter__()

        def __exit__(self, *args: object) -> None:
            original_lock.__exit__(*args)

    dcg._dynamic_models_lock = InstrumentedLock()

    try:

        def worker() -> None:
            result_holder.append(generate_dynamic_models(schema))

        thread = threading.Thread(target=worker)
        thread.start()

        lock_acquired.wait(timeout=5)

        from datamodel_code_generator.dynamic import _make_cache_key

        config = GenerateConfig(
            input_file_type=InputFileType.JsonSchema,
            output_model_type=DataModelType.PydanticV2BaseModel,
        )
        cache_key = _make_cache_key(schema, config)
        assert cache_key is not None
        dcg._dynamic_models_cache[cache_key] = cached_models

        cache_populated.set()
        thread.join(timeout=10)

        assert len(result_holder) == snapshot(1)
        assert result_holder[0] is cached_models
    finally:
        cache_populated.set()
        dcg._dynamic_models_lock = original_lock
        if cache_key and cache_key in dcg._dynamic_models_cache:
            del dcg._dynamic_models_cache[cache_key]
