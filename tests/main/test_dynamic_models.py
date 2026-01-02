"""Tests for generate_dynamic_models function."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

import pydantic
import pytest

from datamodel_code_generator import (
    DataModelType,
    InputFileType,
    clear_dynamic_models_cache,
    generate_dynamic_models,
)

if TYPE_CHECKING:
    from typing import Any

pytestmark = pytest.mark.skipif(pydantic.VERSION < "2.0.0", reason="generate_dynamic_models requires Pydantic v2")


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    """Clear cache before each test."""
    clear_dynamic_models_cache()


class TestGenerateDynamicModels:
    """Tests for generate_dynamic_models function."""

    def test_simple_model(self) -> None:
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
        assert "Model" in models
        Model = models["Model"]  # noqa: N806
        instance = Model(name="John", age=30)
        assert instance.name == "John"
        assert instance.age == 30

    def test_nested_models(self) -> None:
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
        assert "Model" in models

    def test_enum_model(self) -> None:
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
        assert "Model" in models
        assert "Status" in models

    def test_circular_reference(self) -> None:
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
        assert "Node" in models
        Node = models["Node"]  # noqa: N806
        node = Node(value="root", children=[Node(value="child", children=[])])
        assert node.value == "root"
        assert len(node.children) == 1

    def test_allof_inheritance(self) -> None:
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
        assert "Extended" in models


class TestCache:
    """Tests for caching behavior."""

    def test_cache_hit(self) -> None:
        """Test that cached models are returned."""
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
        }
        models1 = generate_dynamic_models(schema)
        models2 = generate_dynamic_models(schema)
        assert models1 is models2

    def test_cache_miss_different_schema(self) -> None:
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

    def test_cache_miss_different_kwargs(self) -> None:
        """Test that different kwargs create different cache entries."""
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
        }
        models1 = generate_dynamic_models(schema, class_name="User")
        models2 = generate_dynamic_models(schema, class_name="Person")
        assert models1 is not models2
        assert "User" in models1
        assert "Person" in models2

    def test_cache_disabled(self) -> None:
        """Test that caching can be disabled."""
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
        }
        models1 = generate_dynamic_models(schema, cache_size=0)
        models2 = generate_dynamic_models(schema, cache_size=0)
        assert models1 is not models2

    def test_cache_eviction(self) -> None:
        """Test that old entries are evicted when cache is full."""
        schemas = [{"type": "object", "properties": {f"field{i}": {"type": "string"}}} for i in range(5)]
        for schema in schemas:
            generate_dynamic_models(schema, cache_size=3)

        count = clear_dynamic_models_cache()
        assert count == 3

    def test_cache_shrinks_when_smaller_size_requested(self) -> None:
        """Test that cache shrinks when a smaller cache_size is used."""
        schemas = [{"type": "object", "properties": {f"field{i}": {"type": "string"}}} for i in range(5)]
        for schema in schemas:
            generate_dynamic_models(schema, cache_size=10)

        count = clear_dynamic_models_cache()
        assert count == 5

        for schema in schemas:
            generate_dynamic_models(schema, cache_size=10)

        new_schema: dict[str, Any] = {
            "type": "object",
            "properties": {"new_field": {"type": "string"}},
        }
        generate_dynamic_models(new_schema, cache_size=2)

        count = clear_dynamic_models_cache()
        assert count == 2

    def test_clear_cache(self) -> None:
        """Test clearing the cache."""
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
        }
        generate_dynamic_models(schema)
        count = clear_dynamic_models_cache()
        assert count == 1

        count = clear_dynamic_models_cache()
        assert count == 0


class TestThreadSafety:
    """Tests for thread safety."""

    def test_concurrent_same_schema(self) -> None:
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
        assert len(results) == 10
        assert all(r is results[0] for r in results)

    def test_concurrent_different_schemas(self) -> None:
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


class TestConstraints:
    """Tests for model constraints."""

    def test_numeric_constraints(self) -> None:
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
        Model = models["Model"]  # noqa: N806
        instance = Model(age=30)
        assert instance.age == 30

    def test_string_constraints(self) -> None:
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
        assert "Model" in models


class TestExplicitParameters:
    """Tests for explicit parameter passing."""

    def test_explicit_input_file_type(self) -> None:
        """Test passing explicit input_file_type."""
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
        }
        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)
        assert "Model" in models

    def test_explicit_output_model_type(self) -> None:
        """Test passing explicit output_model_type."""
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
        }
        models = generate_dynamic_models(schema, output_model_type=DataModelType.PydanticV2BaseModel)
        assert "Model" in models

    def test_openapi_auto_detection(self) -> None:
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
        assert "User" in models


class TestCacheKeyGeneration:
    """Tests for cache key generation edge cases."""

    def test_non_serializable_schema_skips_cache(self) -> None:
        """Test that non-JSON-serializable schemas skip caching."""
        from datamodel_code_generator import _make_cache_key

        schema_with_non_serializable: dict[str, Any] = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "custom": object(),
        }
        cache_key = _make_cache_key(schema_with_non_serializable, {})
        assert cache_key is None


class TestDoubleCheckedLocking:
    """Tests for double-checked locking pattern."""

    def test_cache_hit_inside_lock(self) -> None:
        """Test cache hit after acquiring lock (double-checked locking)."""
        import datamodel_code_generator as dcg

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

            from datamodel_code_generator import _make_cache_key

            effective_kwargs = {
                "input_file_type": InputFileType.JsonSchema,
                "output_model_type": DataModelType.PydanticV2BaseModel,
            }
            cache_key = _make_cache_key(schema, effective_kwargs)
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
