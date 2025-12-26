# 🐍 Generate from Python Models {#python-model}

Generate code from existing Python types: Pydantic models, dataclasses, TypedDict, or dict schemas. This is useful for converting between model types or generating from programmatically-defined schemas.

## 🚀 Quick Start {#quick-start}

```bash
datamodel-codegen --input-model ./mymodule.py:User --output model.py
```

## Format {#format}

```
--input-model <path/to/file.py>:<ObjectName>
```

Simply specify the **file path** and **object name** separated by `:`.

### Example {#format-example}

```
myproject/
├── src/
│   └── models/
│       └── user.py      # class User(BaseModel): ...
└── schemas.py           # USER_SCHEMA = {...}
```

```bash
# From file path (recommended - easy to copy-paste)
datamodel-codegen --input-model src/models/user.py:User --output model.py
datamodel-codegen --input-model ./schemas.py:USER_SCHEMA --input-file-type jsonschema

# Windows paths also work
datamodel-codegen --input-model src\models\user.py:User
```

!!! tip "Copy-paste friendly"
    Just copy the file path from your editor or file explorer, add `:ClassName`, and you're done!

### Module format (alternative) {#module-format}

You can also use Python module notation with dots:

```bash
datamodel-codegen --input-model src.models.user:User
datamodel-codegen --input-model schemas:USER_SCHEMA --input-file-type jsonschema
```

!!! note "Current directory is auto-added to `sys.path`"
    No `PYTHONPATH` configuration needed.

!!! tip "File and package name conflict"
    If both `mymodule.py` and `mymodule/` directory exist, use `./` prefix:
    ```bash
    datamodel-codegen --input-model ./mymodule.py:Model
    ```

---

## Supported Input Types {#supported-input-types}

| Type | Description | Requires |
|------|-------------|----------|
| Pydantic BaseModel | Pydantic v2 models with `model_json_schema()` | Pydantic v2 |
| dataclass | Standard library `@dataclass` | Pydantic v2 (for TypeAdapter) |
| Pydantic dataclass | `@pydantic.dataclasses.dataclass` | Pydantic v2 |
| TypedDict | `typing.TypedDict` subclasses | Pydantic v2 (for TypeAdapter) |
| dict | Dict containing JSON Schema or OpenAPI spec | - |

!!! note "Pydantic v2 Required"
    All Python type inputs (except raw dict) require Pydantic v2 runtime to convert to JSON Schema.

---

## 📝 Examples {#examples}

### Pydantic BaseModel {#pydantic-basemodel}

**mymodule.py**
```python
from pydantic import BaseModel

class User(BaseModel):
    name: str
    age: int
```

```bash
datamodel-codegen --input-model ./mymodule.py:User --output model.py
```

**✨ Generated model.py**
```python
from __future__ import annotations

from pydantic import BaseModel


class User(BaseModel):
    name: str
    age: int
```

### Convert Pydantic to TypedDict {#convert-pydantic-to-typeddict}

```bash
datamodel-codegen --input-model ./mymodule.py:User --output-model-type typing.TypedDict --output model.py
```

**✨ Generated model.py**
```python
from __future__ import annotations

from typing import TypedDict


class User(TypedDict):
    name: str
    age: int
```

### Standard dataclass {#dataclass}

**mymodule.py**
```python
from dataclasses import dataclass

@dataclass
class User:
    name: str
    age: int
```

```bash
datamodel-codegen --input-model ./mymodule.py:User --output model.py
```

### TypedDict {#typeddict}

**mymodule.py**
```python
from typing import TypedDict

class User(TypedDict):
    name: str
    age: int
```

```bash
datamodel-codegen --input-model ./mymodule.py:User --output model.py
```

### Dict Schema (JSON Schema) {#dict-jsonschema}

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
datamodel-codegen --input-model ./mymodule.py:USER_SCHEMA --input-file-type jsonschema --output model.py
```

!!! warning "Dict requires --input-file-type"
    When using a dict schema, you must specify `--input-file-type` (e.g., `jsonschema`, `openapi`).

### Dict Schema (OpenAPI) {#dict-openapi}

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
datamodel-codegen --input-model ./mymodule.py:OPENAPI_SPEC --input-file-type openapi --output model.py
```

---

## Mutual Exclusion {#mutual-exclusion}

`--input-model` cannot be used with:

- `--input` (file input)
- `--url` (URL input)
- `--watch` (file watching)

---

## 📖 See Also

- 🖥️ [CLI Reference](cli-reference/index.md) - Complete CLI options reference
- 📁 [CLI Reference: Base Options](cli-reference/base-options.md#input-model) - `--input-model` option details
- 📋 [Generate from JSON Schema](jsonschema.md) - JSON Schema input documentation
