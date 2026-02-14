"""Tests for generate_dynamic_models function."""

from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING

import pydantic
import pytest
from inline_snapshot import external_file

from datamodel_code_generator import (
    DataModelType,
    InputFileType,
    clear_dynamic_models_cache,
    generate,
    generate_dynamic_models,
)
from datamodel_code_generator.config import GenerateConfig
from datamodel_code_generator.enums import ModuleSplitMode
from datamodel_code_generator.model.pydantic_v2 import UnionMode
from datamodel_code_generator.types import StrictTypes
from tests.conftest import assert_output

if TYPE_CHECKING:
    from typing import Any


pytestmark = pytest.mark.skipif(pydantic.VERSION < "2.0.0", reason="generate_dynamic_models requires Pydantic v2")

DATA_PATH = Path(__file__).parent.parent / "data" / "dynamic_models"
EXPECTED_PATH = Path(__file__).parent.parent / "data" / "expected" / "dynamic_models"


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


def assert_dynamic_models(
    schema: dict[str, Any],
    validations: dict[str, dict[str, Any]],
    expected_path: Path,
    *,
    config: GenerateConfig | None = None,
) -> None:
    """Generate dynamic models, validate data, and assert with external file."""
    models = generate_dynamic_models(schema, config=config)
    assert {
        name: models[name].model_validate(data).model_dump(mode="json") for name, data in validations.items()
    } == external_file(expected_path)


@pytest.fixture(autouse=True)
def _setup_and_clear_cache() -> None:
    """Rebuild GenerateConfig and clear cache before each test."""
    GenerateConfig.model_rebuild(_types_namespace={"StrictTypes": StrictTypes, "UnionMode": UnionMode})
    clear_dynamic_models_cache()


def test_simple_model() -> None:
    """Test generating a simple model and validating data."""
    schema = make_object_schema({"name": {"type": "string"}, "age": {"type": "integer"}}, required=["name"])
    assert_dynamic_models(schema, {"Model": {"name": "John", "age": 30}}, EXPECTED_PATH / "simple_model.json")
    assert_dynamic_models(schema, {"Model": {"name": "Jane"}}, EXPECTED_PATH / "simple_model_optional.json")


def test_nested_models() -> None:
    """Test generating nested models and validating nested data."""
    schema = make_object_schema({"user": {"type": "object", "properties": {"name": {"type": "string"}}}})
    assert_dynamic_models(schema, {"Model": {"user": {"name": "Alice"}}}, EXPECTED_PATH / "nested_models.json")


def test_enum_model() -> None:
    """Test generating model with enum and validating enum values."""
    schema = make_object_schema({"status": {"type": "string", "enum": ["active", "inactive"]}})
    assert_dynamic_models(schema, {"Model": {"status": "active"}}, EXPECTED_PATH / "enum_model.json")

    models = generate_dynamic_models(schema)
    with pytest.raises(pydantic.ValidationError):
        models["Model"].model_validate({"status": "invalid"})


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
    assert_dynamic_models(
        schema,
        {
            "Node": {
                "value": "root",
                "children": [{"value": "child1", "children": []}, {"value": "child2", "children": []}],
            }
        },
        EXPECTED_PATH / "circular_reference.json",
    )


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
    assert_dynamic_models(schema, {"Extended": {"id": 42, "name": "test"}}, EXPECTED_PATH / "allof_inheritance.json")


def test_validation_error() -> None:
    """Test that validation errors are raised for invalid data."""
    schema = make_object_schema({"count": {"type": "integer"}}, required=["count"])
    models = generate_dynamic_models(schema)
    Model = models["Model"]

    with pytest.raises(pydantic.ValidationError):
        Model.model_validate({"count": "not_an_integer"})

    with pytest.raises(pydantic.ValidationError):
        Model.model_validate({})


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
    assert sorted(models1.keys()) == ["User"]
    assert sorted(models2.keys()) == ["Person"]


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

    def worker() -> None:
        results.append(generate_dynamic_models(schema))

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == 10
    assert all(r is results[0] for r in results)


def test_concurrent_different_schemas() -> None:
    """Test concurrent access with different schemas."""
    schemas = [make_object_schema({f"field{i}": {"type": "string"}}) for i in range(5)]
    results: list[dict[str, type]] = []

    def worker(schema: dict[str, Any]) -> None:
        results.append(generate_dynamic_models(schema))

    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(worker, schemas)

    assert len(results) == 5


def test_numeric_constraints() -> None:
    """Test models with numeric constraints validate properly."""
    schema = make_object_schema({"age": {"type": "integer", "minimum": 0, "maximum": 150}})
    assert_dynamic_models(schema, {"Model": {"age": 30}}, EXPECTED_PATH / "numeric_constraints.json")

    models = generate_dynamic_models(schema)
    with pytest.raises(pydantic.ValidationError):
        models["Model"].model_validate({"age": -1})
    with pytest.raises(pydantic.ValidationError):
        models["Model"].model_validate({"age": 200})


def test_string_constraints() -> None:
    """Test models with string constraints validate properly."""
    schema = make_object_schema({"email": {"type": "string", "pattern": r"^[\w\.-]+@[\w\.-]+\.\w+$"}})
    assert_dynamic_models(schema, {"Model": {"email": "test@example.com"}}, EXPECTED_PATH / "string_constraints.json")

    models = generate_dynamic_models(schema)
    with pytest.raises(pydantic.ValidationError):
        models["Model"].model_validate({"email": "invalid-email"})


def test_explicit_input_file_type() -> None:
    """Test passing explicit input_file_type via config."""
    schema = make_object_schema({"name": {"type": "string"}})
    models = generate_dynamic_models(schema, config=make_config())
    assert sorted(models.keys()) == ["Model"]


def test_openapi_auto_detection() -> None:
    """Test that OpenAPI schemas are auto-detected and models work."""
    with (DATA_PATH / "openapi_schema.json").open() as f:
        openapi_schema = json.load(f)
    assert_dynamic_models(
        openapi_schema, {"User": {"id": 1, "name": "Alice"}}, EXPECTED_PATH / "openapi_auto_detection.json"
    )


def test_config_with_auto_input_type() -> None:
    """Test that input_file_type=Auto in config is auto-detected."""
    schema = make_object_schema({"name": {"type": "string"}})
    models = generate_dynamic_models(schema, config=GenerateConfig(class_name="User"))
    assert sorted(models.keys()) == ["User"]


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
        dcg._dynamic_models_cache.pop(cache_key, None)  # type: ignore[arg-type]


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
    assert_dynamic_models(
        schema,
        {"User": {"name": "Alice", "age": 25}, "Order": {"id": 1, "user": {"name": "Bob", "age": 30}}},
        EXPECTED_PATH / "multi_module_output.json",
        config=make_config(module_split_mode=ModuleSplitMode.Single),
    )


def test_generated_code_matches_expected() -> None:
    """Test that generate() produces expected code for a complex schema."""
    schema: dict[str, Any] = {
        "$defs": {
            "Address": {
                "type": "object",
                "properties": {"street": {"type": "string"}, "city": {"type": "string"}},
                "required": ["street", "city"],
            },
            "Person": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "address": {"$ref": "#/$defs/Address"},
                },
                "required": ["name"],
            },
        },
        "$ref": "#/$defs/Person",
    }
    config = GenerateConfig(
        input_file_type=InputFileType.JsonSchema,
        output_model_type=DataModelType.PydanticV2BaseModel,
    )
    result = generate(input_=schema, config=config)
    assert isinstance(result, str)
    assert_output(result, EXPECTED_PATH / "complex_schema.py")

    assert_dynamic_models(
        schema,
        {
            "Person": {"name": "John", "address": {"street": "123 Main St", "city": "NYC"}},
            "Address": {"street": "456 Oak Ave", "city": "LA"},
        },
        EXPECTED_PATH / "generated_code_validation.json",
    )


def test_get_relative_imports_with_module_path() -> None:
    """Test _get_relative_imports with 'from .module import X' style imports."""
    from datamodel_code_generator.dynamic import _get_relative_imports

    code = "from .user import User\nfrom .order import Order"
    imports = _get_relative_imports(code)
    assert imports == {"user", "order"}


def test_get_relative_imports_with_dotted_module() -> None:
    """Test _get_relative_imports with dotted module path."""
    from datamodel_code_generator.dynamic import _get_relative_imports

    code = "from .models.user import User"
    imports = _get_relative_imports(code)
    assert imports == {"models"}


def test_build_module_edges_no_matching_import() -> None:
    """Test _build_module_edges when import doesn't match any module."""
    from datamodel_code_generator.dynamic import _build_module_edges

    modules = {
        ("user.py",): "class User: pass",
        ("order.py",): "from .nonexistent import Something\nclass Order: pass",
    }
    edges = _build_module_edges(modules)
    assert edges["user.py",] == set()
    assert edges["order.py",] == set()


def test_execute_multi_module_without_init() -> None:
    """Test _execute_multi_module without __init__.py to cover package registration branch."""
    from datamodel_code_generator.dynamic import _execute_multi_module

    modules = {
        ("user.py",): "from pydantic import BaseModel\n\nclass User(BaseModel):\n    name: str",
    }
    models = _execute_multi_module(modules)
    assert "User" in models
    user = models["User"](name="Alice")
    assert user.name == "Alice"


def test_execute_multi_module_no_models() -> None:
    """Test _execute_multi_module with code that has no models."""
    from datamodel_code_generator.dynamic import _execute_multi_module

    modules = {
        ("utils.py",): "def helper(): pass",
    }
    models = _execute_multi_module(modules)
    assert models == {}


def test_multiple_aliases_required_field() -> None:
    """Test dynamic models with multiple aliases on required fields. (#2989)."""
    schema = make_object_schema({"name": {"type": "string"}}, required=["name"])
    config = GenerateConfig(
        input_file_type=InputFileType.JsonSchema,
        output_model_type=DataModelType.PydanticV2BaseModel,
        aliases={"name": ["full_name", "customer_name"]},
        class_name="Customer",
    )
    assert_dynamic_models(
        schema,
        {"Customer": {"name": "John"}},
        EXPECTED_PATH / "multiple_aliases_required.json",
        config=config,
    )


def test_multiple_aliases_required_field_code_output() -> None:
    """Test generated code includes Field import with multiple aliases on required fields. (#2989)."""
    schema = make_object_schema({"name": {"type": "string"}}, required=["name"])
    config = GenerateConfig(
        input_file_type=InputFileType.JsonSchema,
        output_model_type=DataModelType.PydanticV2BaseModel,
        aliases={"name": ["full_name", "customer_name"]},
        class_name="Customer",
    )
    result = generate(input_=schema, config=config)
    assert isinstance(result, str)
    assert_output(result, EXPECTED_PATH / "multiple_aliases_required_code.py")


def test_execute_multi_module_enum_only() -> None:
    """Test _execute_multi_module with enum only to cover non-BaseModel branch."""
    from datamodel_code_generator.dynamic import _execute_multi_module

    modules = {
        (
            "status.py",
        ): "from enum import Enum\n\nclass Status(Enum):\n    ACTIVE = 'active'\n    INACTIVE = 'inactive'",
    }
    models = _execute_multi_module(modules)
    assert "Status" in models
    assert models["Status"].ACTIVE.value == "active"
