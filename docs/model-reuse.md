<!-- related-cli-options: --reuse-model, --reuse-scope, --shared-module-name, --collapse-root-models, --disable-warnings -->

# Model Reuse and Deduplication

When generating models from schemas, you may encounter duplicate model definitions. datamodel-code-generator provides options to deduplicate models and share them across multiple files, improving output structure, reducing diff sizes, and enhancing performance.

## Quick Overview

| Option | Description |
|--------|-------------|
| `--reuse-model` | Deduplicate identical model/enum definitions |
| `--reuse-scope` | Control scope of deduplication (`root` or `tree`) |
| `--shared-module-name` | Name for shared module in multi-file output |
| `--collapse-root-models` | Inline root models instead of creating wrappers |

---

## `--reuse-model`

The `--reuse-model` flag detects identical enum or model definitions and generates a single shared definition instead of duplicates.

### Without `--reuse-model`

```bash
datamodel-codegen --input schema.json --output model.py
```

```python
# Duplicate enums for animal and pet fields
class Animal(Enum):
    dog = 'dog'
    cat = 'cat'

class Pet(Enum):  # Duplicate!
    dog = 'dog'
    cat = 'cat'

class User(BaseModel):
    animal: Optional[Animal] = None
    pet: Optional[Pet] = None
```

### With `--reuse-model`

```bash
datamodel-codegen --input schema.json --output model.py --reuse-model
```

```python
# Single shared enum
class Animal(Enum):
    dog = 'dog'
    cat = 'cat'

class User(BaseModel):
    animal: Optional[Animal] = None
    pet: Optional[Animal] = None  # Reuses Animal
```

### Benefits

- **Smaller output** - Less generated code
- **Cleaner diffs** - Changes to shared types only appear once
- **Better performance** - Faster generation for large schemas
- **Type consistency** - Same types are truly the same

---

## `--reuse-scope`

Controls the scope for model reuse detection when processing multiple input files.

| Value | Description |
|-------|-------------|
| `root` | Detect duplicates only within each input file (default) |
| `tree` | Detect duplicates across all input files |

### Single-file input

For single-file input, `--reuse-scope` has no effect. Use `--reuse-model` alone.

### Multi-file input with `tree` scope

When generating from multiple schema files to a directory:

```bash
datamodel-codegen --input schemas/ --output models/ --reuse-model --reuse-scope tree
```

**Input files:**
```text
schemas/
├── user.json      # defines SharedModel
└── order.json     # also defines identical SharedModel
```

**Output with `--reuse-scope tree`:**
```text
models/
├── __init__.py
├── user.py        # imports from shared
├── order.py       # imports from shared
└── shared.py      # SharedModel defined once
```

```python
# models/user.py
from .shared import SharedModel

class User(BaseModel):
    data: Optional[SharedModel] = None

# models/shared.py
class SharedModel(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
```

---

## `--shared-module-name`

Customize the name of the shared module when using `--reuse-scope tree`.

```bash
datamodel-codegen --input schemas/ --output models/ \
  --reuse-model --reuse-scope tree --shared-module-name common
```

**Output:**
```text
models/
├── __init__.py
├── user.py
├── order.py
└── common.py      # Instead of shared.py
```

---

## `--collapse-root-models`

Inline root model definitions instead of creating separate wrapper classes.

### Without `--collapse-root-models`

```python
class UserId(BaseModel):
    __root__: str

class User(BaseModel):
    id: UserId
```

### With `--collapse-root-models`

```python
class User(BaseModel):
    id: str  # Inlined
```

### When to use

- Simpler output when wrapper classes aren't needed
- Reducing the number of generated classes
- When root models are just type aliases

---

## Combining Options

### Recommended for large multi-file projects

```bash
datamodel-codegen \
  --input schemas/ \
  --output models/ \
  --reuse-model \
  --reuse-scope tree \
  --shared-module-name common \
  --collapse-root-models
```

This produces:
- Deduplicated models across all files
- Shared types in a `common.py` module
- Inlined simple root models
- Minimal, clean output

### Recommended for single-file projects

```bash
datamodel-codegen \
  --input schema.json \
  --output model.py \
  --reuse-model \
  --collapse-root-models
```

---

## Performance Impact

For large schemas with many models:

| Scenario | Without reuse | With reuse |
|----------|---------------|------------|
| 100 schemas, 50% duplicates | 100 models | ~50 models |
| Generation time | Baseline | Faster (less to generate) |
| Output size | Large | Smaller |
| Git diff on type change | Multiple files | Single location |

!!! tip "Performance tip"
    For very large schemas, combine `--reuse-model` with `--disable-warnings` to speed up generation:

    ```bash
    datamodel-codegen --reuse-model --disable-warnings --input large-schema.json
    ```

---

## Output Structure Comparison

### Without deduplication

```text
models/
├── user.py         # UserStatus enum
├── order.py        # OrderStatus enum (duplicate of UserStatus!)
└── product.py      # ProductStatus enum (duplicate!)
```

### With `--reuse-model --reuse-scope tree`

```text
models/
├── __init__.py
├── user.py         # imports Status from shared
├── order.py        # imports Status from shared
├── product.py      # imports Status from shared
└── shared.py       # Status enum defined once
```

---

## See Also

- [CLI Reference: `--reuse-model`](cli-reference/model-customization.md#reuse-model)
- [CLI Reference: `--reuse-scope`](cli-reference/model-customization.md#reuse-scope)
- [CLI Reference: `--collapse-root-models`](cli-reference/model-customization.md#collapse-root-models)
- [Root Models and Type Aliases](root-model-and-type-alias.md)
- [FAQ: Performance](faq.md#-performance)
