# Dynamic Model Generation

Generate real Python model classes from JSON Schema or OpenAPI at runtime without writing files.

## Overview

While `generate()` produces source code as strings, `generate_dynamic_models()` creates actual Python classes that you can use immediately for validation and data processing. This is useful for:

- Runtime schema validation without code generation step
- Dynamic API clients that adapt to schema changes
- Testing and prototyping
- Plugin systems with dynamic schemas

## Quick Start

```python
from datamodel_code_generator import generate_dynamic_models

schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer"}
    },
    "required": ["name"]
}

models = generate_dynamic_models(schema)
User = models["Model"]

# Use the model for validation
user = User(name="Alice", age=30)
print(user.model_dump())  # {'name': 'Alice', 'age': 30}

# Validation errors are raised
try:
    User(age="not a number")  # Missing required 'name', wrong type for 'age'
except Exception as e:
    print(e)
```

## API Reference

### `generate_dynamic_models()`

```python
def generate_dynamic_models(
    input_: Mapping[str, Any],
    *,
    config: GenerateConfig | None = None,
    cache_size: int = 128,
) -> dict[str, type]:
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `input_` | `Mapping[str, Any]` | required | JSON Schema or OpenAPI schema as dict |
| `config` | `GenerateConfig \| None` | `None` | Generation options (same as `generate()`) |
| `cache_size` | `int` | `128` | Maximum cached schemas. Set to `0` to disable |

**Returns:** `dict[str, type]` - Dictionary mapping class names to model classes.

### `clear_dynamic_models_cache()`

```python
def clear_dynamic_models_cache() -> int:
```

Clears the internal cache and returns the number of entries cleared.

## Examples

### JSON Schema with Nested Models

```python
from datamodel_code_generator import generate_dynamic_models

schema = {
    "$defs": {
        "Address": {
            "type": "object",
            "properties": {
                "street": {"type": "string"},
                "city": {"type": "string"}
            },
            "required": ["street", "city"]
        },
        "Person": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "address": {"$ref": "#/$defs/Address"}
            },
            "required": ["name"]
        }
    },
    "$ref": "#/$defs/Person"
}

models = generate_dynamic_models(schema)

# Both models are available
Person = models["Person"]
Address = models["Address"]

person = Person(
    name="Bob",
    address={"street": "123 Main St", "city": "NYC"}
)
print(person.model_dump())
# {'name': 'Bob', 'address': {'street': '123 Main St', 'city': 'NYC'}}
```

### OpenAPI Schema

OpenAPI schemas are auto-detected:

```python
from datamodel_code_generator import generate_dynamic_models

openapi_schema = {
    "openapi": "3.0.0",
    "info": {"title": "User API", "version": "1.0.0"},
    "paths": {},
    "components": {
        "schemas": {
            "User": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "email": {"type": "string", "format": "email"}
                },
                "required": ["id", "email"]
            }
        }
    }
}

models = generate_dynamic_models(openapi_schema)
User = models["User"]

user = User(id=1, email="alice@example.com")
```

### With Custom Configuration

```python
from datamodel_code_generator import generate_dynamic_models, GenerateConfig, DataModelType

schema = {"type": "object", "properties": {"name": {"type": "string"}}}

config = GenerateConfig(
    class_name="Customer",
    output_model_type=DataModelType.PydanticV2BaseModel,
)

models = generate_dynamic_models(schema, config=config)
Customer = models["Customer"]
```

### Enum Models

```python
from datamodel_code_generator import generate_dynamic_models

schema = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["pending", "approved", "rejected"]
        }
    }
}

models = generate_dynamic_models(schema)
Model = models["Model"]
Status = models["Status"]

# Enum validation
item = Model(status="approved")
print(item.status)  # Status.approved
print(item.status.value)  # 'approved'

# Invalid enum value raises error
try:
    Model(status="invalid")
except Exception as e:
    print(e)
```

### Circular References

```python
from datamodel_code_generator import generate_dynamic_models

schema = {
    "$defs": {
        "Node": {
            "type": "object",
            "properties": {
                "value": {"type": "string"},
                "children": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/Node"}
                }
            }
        }
    },
    "$ref": "#/$defs/Node"
}

models = generate_dynamic_models(schema)
Node = models["Node"]

tree = Node(
    value="root",
    children=[
        Node(value="child1", children=[]),
        Node(value="child2", children=[
            Node(value="grandchild", children=[])
        ])
    ]
)
```

## Caching

Models are cached by schema content and configuration to avoid regeneration:

```python
from datamodel_code_generator import generate_dynamic_models, clear_dynamic_models_cache

schema = {"type": "object", "properties": {"x": {"type": "integer"}}}

# First call generates models
models1 = generate_dynamic_models(schema)

# Second call returns cached models (same object)
models2 = generate_dynamic_models(schema)
assert models1 is models2  # True

# Disable caching for specific call
models3 = generate_dynamic_models(schema, cache_size=0)
assert models1 is not models3  # True

# Clear all cached models
cleared = clear_dynamic_models_cache()
print(f"Cleared {cleared} cached schemas")
```

## Thread Safety

`generate_dynamic_models()` is thread-safe. Multiple threads can safely call it concurrently:

```python
import threading
from datamodel_code_generator import generate_dynamic_models

schema = {"type": "object", "properties": {"x": {"type": "integer"}}}
results = []

def worker():
    models = generate_dynamic_models(schema)
    results.append(models)

threads = [threading.Thread(target=worker) for _ in range(10)]
for t in threads:
    t.start()
for t in threads:
    t.join()

# All threads get the same cached models
assert all(r is results[0] for r in results)
```

## Limitations

| Limitation | Details |
|------------|---------|
| Pydantic v2 only | Pydantic v1 is not supported |
| Not pickle-able | Use `model_dump()` to serialize instances |
| Dict input only | Schema must be a `dict`, not a file path or string |

## Comparison with `generate()`

| Feature | `generate()` | `generate_dynamic_models()` |
|---------|-------------|----------------------------|
| Output | Source code string | Actual Python classes |
| Use case | Code generation, file output | Runtime validation |
| Caching | No | Yes (configurable) |
| Thread-safe | Yes | Yes |
| Pydantic v1 | Yes | No |

## See Also

- [Using as Module](using_as_module.md) - `generate()` function reference
- [JSON Schema](jsonschema.md) - JSON Schema examples
- [OpenAPI](openapi.md) - OpenAPI examples
