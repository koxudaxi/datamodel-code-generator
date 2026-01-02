"""Tests for generate_dynamic_models function."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING

import pydantic
import pytest

from datamodel_code_generator import (
    DataModelType,
    InputFileType,
    clear_dynamic_models_cache,
    generate_dynamic_models,
)
from datamodel_code_generator.config import GenerateConfig
from datamodel_code_generator.enums import ModuleSplitMode
from datamodel_code_generator.model.pydantic_v2 import UnionMode
from datamodel_code_generator.types import StrictTypes

if TYPE_CHECKING:
    from typing import Any

pytestmark = pytest.mark.skipif(pydantic.VERSION < "2.0.0", reason="generate_dynamic_models requires Pydantic v2")

EXPECTED_PATH = Path(__file__).parent / "expected" / "dynamic_models"


def assert_model_keys(models: dict[str, type], expected_keys: list[str]) -> None:
    """Assert that models dict contains exactly the expected keys."""
    assert sorted(models.keys()) == sorted(expected_keys)


def assert_model_dump(instance: object, expected: dict[str, Any]) -> None:
    """Assert that model instance dumps to expected dict."""
    assert instance.model_dump() == expected  # type: ignore[union-attr]


def assert_has_models(models: dict[str, type], *keys: str) -> None:
    """Assert that models dict contains all specified keys."""
    for key in keys:
        assert key in models, f"Expected model '{key}' not found in {list(models.keys())}"


def make_object_schema(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    """Create a simple object schema."""
    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def make_config(
    class_name: str | None = None,
    module_split_mode: ModuleSplitMode | None = None,
) -> GenerateConfig:
    """Create a GenerateConfig with common defaults."""
    return GenerateConfig(
        input_file_type=InputFileType.JsonSchema,
        output_model_type=DataModelType.PydanticV2BaseModel,
        class_name=class_name,
        module_split_mode=module_split_mode,
    )


@pytest.fixture(autouse=True)
def _setup_and_clear_cache() -> None:
    """Rebuild GenerateConfig and clear cache before each test."""
    GenerateConfig.model_rebuild(_types_namespace={"StrictTypes": StrictTypes, "UnionMode": UnionMode})
    clear_dynamic_models_cache()


def test_simple_model() -> None:
    """Test generating a simple model."""
    schema = make_object_schema({"name": {"type": "string"}, "age": {"type": "integer"}}, required=["name"])
    models = generate_dynamic_models(schema)
    assert_model_keys(models, ["Model"])
    instance = models["Model"](name="John", age=30)
    assert_model_dump(instance, {"name": "John", "age": 30})


def test_nested_models() -> None:
    """Test generating nested models."""
    schema = make_object_schema({"user": {"type": "object", "properties": {"name": {"type": "string"}}}})
    models = generate_dynamic_models(schema)
    assert_model_keys(models, ["Model", "User"])


def test_enum_model() -> None:
    """Test generating model with enum."""
    schema = make_object_schema({"status": {"type": "string", "enum": ["active", "inactive"]}})
    models = generate_dynamic_models(schema)
    assert_model_keys(models, ["Model", "Status"])
    instance = models["Model"](status=models["Status"].active)
    assert instance.status.value == "active"


def test_circular_reference() -> None:
    """Test generating models with circular references."""
    schema: dict[str, Any] = {
        "$defs": {
            "Node": {
                "type": "object",
                "properties": {
                    "value": {"type": "string"},
                    "children": {"type": "array", "items": {"$ref": "#/$defs/Node"}},
                },
            },
        },
        "$ref": "#/$defs/Node",
    }
    models = generate_dynamic_models(schema)
    assert_model_keys(models, ["Model", "Node", "RootModel"])
    node = models["Node"](value="root", children=[models["Node"](value="child", children=[])])
    assert_model_dump(node, {"value": "root", "children": [{"value": "child", "children": []}]})


def test_allof_inheritance() -> None:
    """Test generating models with allOf inheritance."""
    schema: dict[str, Any] = {
        "$defs": {
            "Base": {"type": "object", "properties": {"id": {"type": "integer"}}},
            "Extended": {
                "allOf": [{"$ref": "#/$defs/Base"}, {"type": "object", "properties": {"name": {"type": "string"}}}]
            },
        },
        "$ref": "#/$defs/Extended",
    }
    models = generate_dynamic_models(schema)
    assert_model_keys(models, ["Base", "Extended", "Model", "RootModel"])
    instance = models["Extended"](id=1, name="test")
    assert_model_dump(instance, {"id": 1, "name": "test"})


def test_cache_hit() -> None:
    """Test that cached models are returned."""
    schema = make_object_schema({"name": {"type": "string"}})
    models1 = generate_dynamic_models(schema)
    models2 = generate_dynamic_models(schema)
    assert models1 is models2


def test_cache_miss_different_schema() -> None:
    """Test that different schemas create different models."""
    models1 = generate_dynamic_models(make_object_schema({"name": {"type": "string"}}))
    models2 = generate_dynamic_models(make_object_schema({"age": {"type": "integer"}}))
    assert models1 is not models2


def test_cache_miss_different_config() -> None:
    """Test that different configs create different cache entries."""
    schema = make_object_schema({"name": {"type": "string"}})
    models1 = generate_dynamic_models(schema, config=make_config(class_name="User"))
    models2 = generate_dynamic_models(schema, config=make_config(class_name="Person"))
    assert models1 is not models2
    assert_model_keys(models1, ["User"])
    assert_model_keys(models2, ["Person"])


def test_cache_disabled() -> None:
    """Test that caching can be disabled."""
    schema = make_object_schema({"name": {"type": "string"}})
    models1 = generate_dynamic_models(schema, cache_size=0)
    models2 = generate_dynamic_models(schema, cache_size=0)
    assert models1 is not models2


def test_cache_eviction() -> None:
    """Test that old entries are evicted when cache is full."""
    for i in range(5):
        generate_dynamic_models(make_object_schema({f"field{i}": {"type": "string"}}), cache_size=3)
    assert clear_dynamic_models_cache() == 3


def test_cache_shrinks_when_smaller_size_requested() -> None:
    """Test that cache shrinks when a smaller cache_size is used."""
    schemas = [make_object_schema({f"field{i}": {"type": "string"}}) for i in range(5)]
    for schema in schemas:
        generate_dynamic_models(schema, cache_size=10)
    assert clear_dynamic_models_cache() == 5

    for schema in schemas:
        generate_dynamic_models(schema, cache_size=10)
    generate_dynamic_models(make_object_schema({"new_field": {"type": "string"}}), cache_size=2)
    assert clear_dynamic_models_cache() == 2


def test_clear_cache() -> None:
    """Test clearing the cache."""
    generate_dynamic_models(make_object_schema({"name": {"type": "string"}}))
    assert clear_dynamic_models_cache() == 1
    assert clear_dynamic_models_cache() == 0


def test_concurrent_same_schema() -> None:
    """Test concurrent access with the same schema."""
    schema = make_object_schema({"name": {"type": "string"}})
    results: list[dict[str, type]] = []
    errors: list[Exception] = []

    def worker() -> None:
        try:
            results.append(generate_dynamic_models(schema))
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert len(results) == 10
    assert all(r is results[0] for r in results)


def test_concurrent_different_schemas() -> None:
    """Test concurrent access with different schemas."""
    schemas = [make_object_schema({f"field{i}": {"type": "string"}}) for i in range(5)]
    results: list[dict[str, type]] = []
    errors: list[Exception] = []

    def worker(schema: dict[str, Any]) -> None:
        try:
            results.append(generate_dynamic_models(schema))
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(worker, schemas)

    assert not errors
    assert len(results) == 5


def test_numeric_constraints() -> None:
    """Test models with numeric constraints."""
    schema = make_object_schema({"age": {"type": "integer", "minimum": 0, "maximum": 150}})
    models = generate_dynamic_models(schema)
    instance = models["Model"](age=30)
    assert_model_dump(instance, {"age": 30})


def test_string_constraints() -> None:
    """Test models with string constraints."""
    schema = make_object_schema({"email": {"type": "string", "pattern": r"^[\w\.-]+@[\w\.-]+\.\w+$"}})
    models = generate_dynamic_models(schema)
    assert_model_keys(models, ["Model"])


def test_explicit_input_file_type() -> None:
    """Test passing explicit input_file_type via config."""
    schema = make_object_schema({"name": {"type": "string"}})
    models = generate_dynamic_models(schema, config=make_config())
    assert_model_keys(models, ["Model"])


def test_openapi_auto_detection() -> None:
    """Test that OpenAPI schemas are auto-detected."""
    openapi_schema: dict[str, Any] = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {},
        "components": {"schemas": {"User": {"type": "object", "properties": {"name": {"type": "string"}}}}},
    }
    models = generate_dynamic_models(openapi_schema)
    assert_model_keys(models, ["User"])


def test_config_with_auto_input_type() -> None:
    """Test that input_file_type=Auto in config is auto-detected."""
    schema = make_object_schema({"name": {"type": "string"}})
    models = generate_dynamic_models(schema, config=GenerateConfig(class_name="User"))
    assert_model_keys(models, ["User"])


def test_non_serializable_schema_skips_cache() -> None:
    """Test that non-JSON-serializable schemas skip caching."""
    from datamodel_code_generator.dynamic import _make_cache_key

    schema: dict[str, Any] = {"type": "object", "properties": {"name": {"type": "string"}}, "custom": object()}
    assert _make_cache_key(schema, make_config()) is None


def test_cache_hit_inside_lock() -> None:
    """Test cache hit after acquiring lock (double-checked locking)."""
    from datamodel_code_generator import dynamic as dcg
    from datamodel_code_generator.dynamic import _make_cache_key

    schema = make_object_schema({"name": {"type": "string"}})
    original_lock = dcg._dynamic_models_lock
    cached_models: dict[str, type] = {"Model": type("Model", (), {})}
    cache_populated, lock_acquired = threading.Event(), threading.Event()
    result_holder: list[dict[str, type]] = []
    cache_key: str | None = None

    class InstrumentedLock:
        def __enter__(self) -> None:
            lock_acquired.set()
            cache_populated.wait(timeout=5)
            original_lock.__enter__()

        def __exit__(self, *args: object) -> None:
            original_lock.__exit__(*args)

    dcg._dynamic_models_lock = InstrumentedLock()  # type: ignore[assignment]

    try:
        thread = threading.Thread(target=lambda: result_holder.append(generate_dynamic_models(schema)))
        thread.start()
        lock_acquired.wait(timeout=5)

        cache_key = _make_cache_key(schema, make_config())
        assert cache_key is not None
        dcg._dynamic_models_cache[cache_key] = cached_models

        cache_populated.set()
        thread.join(timeout=10)

        assert len(result_holder) == 1
        assert result_holder[0] is cached_models
    finally:
        cache_populated.set()
        dcg._dynamic_models_lock = original_lock
        if cache_key and cache_key in dcg._dynamic_models_cache:
            del dcg._dynamic_models_cache[cache_key]


def test_multi_module_output() -> None:
    """Test generating models with multi-module output (module_split_mode=Single)."""
    schema: dict[str, Any] = {
        "$defs": {
            "User": {
                "type": "object",
                "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
                "required": ["name"],
            },
            "Order": {
                "type": "object",
                "properties": {"id": {"type": "integer"}, "user": {"$ref": "#/$defs/User"}},
                "required": ["id"],
            },
        },
        "$ref": "#/$defs/Order",
    }
    models = generate_dynamic_models(schema, config=make_config(module_split_mode=ModuleSplitMode.Single))
    assert_has_models(models, "User", "Order")
    user = models["User"](name="Alice", age=25)
    assert_model_dump(user, {"name": "Alice", "age": 25})
    order = models["Order"](id=1, user=user)
    assert_model_dump(order, {"id": 1, "user": {"name": "Alice", "age": 25}})
