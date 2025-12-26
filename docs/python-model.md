# 🐍 Generate from Python Models

Generate code from existing Python types: Pydantic models, dataclasses, TypedDict, or dict schemas. This is useful for converting between model types or generating from programmatically-defined schemas.

## 🚀 Quick Start

```bash
datamodel-codegen --input-model mymodule:MyModel --output model.py
```

## Supported Input Types

| Type | Description | Requires |
|------|-------------|----------|
| Pydantic BaseModel | Pydantic v2 models with `model_json_schema()` | Pydantic v2 |
| dataclass | Standard library `@dataclass` | Pydantic v2 (for TypeAdapter) |
| Pydantic dataclass | `@pydantic.dataclasses.dataclass` | Pydantic v2 |
| TypedDict | `typing.TypedDict` subclasses | Pydantic v2 (for TypeAdapter) |
| dict | Dict containing JSON Schema or OpenAPI spec | - |

!!! note "Pydantic v2 Required"
    All Python type inputs (except raw dict) require Pydantic v2 runtime to convert to JSON Schema.

## 📝 Examples

### Pydantic BaseModel

**mymodule.py**
```python
from pydantic import BaseModel

class User(BaseModel):
    name: str
    age: int
```

```bash
datamodel-codegen --input-model mymodule:User --output model.py
```

**✨ Generated model.py**
```python
from __future__ import annotations

from pydantic import BaseModel


class User(BaseModel):
    name: str
    age: int
```

### Convert Pydantic to TypedDict

```bash
datamodel-codegen --input-model mymodule:User --output-model-type typing.TypedDict --output model.py
```

**✨ Generated model.py**
```python
from __future__ import annotations

from typing import TypedDict


class User(TypedDict):
    name: str
    age: int
```

### Standard dataclass

**mymodule.py**
```python
from dataclasses import dataclass

@dataclass
class User:
    name: str
    age: int
```

```bash
datamodel-codegen --input-model mymodule:User --output model.py
```

### TypedDict

**mymodule.py**
```python
from typing import TypedDict

class User(TypedDict):
    name: str
    age: int
```

```bash
datamodel-codegen --input-model mymodule:User --output model.py
```

### Dict Schema (JSON Schema)

**mymodule.py**
```python
USER_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer"},
    },
    "required": ["name", "age"],
}
```

```bash
datamodel-codegen --input-model mymodule:USER_SCHEMA --input-file-type jsonschema --output model.py
```

!!! warning "Dict requires --input-file-type"
    When using a dict schema, you must specify `--input-file-type` (e.g., `jsonschema`, `openapi`).

### Dict Schema (OpenAPI)

**mymodule.py**
```python
OPENAPI_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "API", "version": "1.0.0"},
    "paths": {},
    "components": {
        "schemas": {
            "User": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"},
                },
            }
        }
    },
}
```

```bash
datamodel-codegen --input-model mymodule:OPENAPI_SPEC --input-file-type openapi --output model.py
```

## Format

The `--input-model` option supports two formats:

### Module format
`module.path:ObjectName`

```bash
datamodel-codegen --input-model mypackage.models:User --output model.py
```

### Path format
`path/to/file.py:ObjectName`

```bash
datamodel-codegen --input-model src/models/user.py:User --output model.py
```

The current directory is automatically added to `sys.path`, so relative paths work without additional configuration.

!!! tip "File and package name conflict"
    If both `mymodule.py` (file) and `mymodule/` (directory) exist, use the path format to explicitly load the file:
    ```bash
    datamodel-codegen --input-model ./mymodule.py:Model --output model.py
    ```

## Mutual Exclusion

`--input-model` cannot be used with:

- `--input` (file input)
- `--url` (URL input)
- `--watch` (file watching)

---

## 📖 See Also

- 🖥️ [CLI Reference](cli-reference/index.md) - Complete CLI options reference
- 📁 [CLI Reference: Base Options](cli-reference/base-options.md#input-model) - `--input-model` option details
- 📋 [Generate from JSON Schema](jsonschema.md) - JSON Schema input documentation
