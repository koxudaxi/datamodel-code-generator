<!-- related-cli-options: --all-exports-scope, --all-exports-collision-strategy, --treat-dot-as-module -->

# Module Structure and Exports

When generating models to a directory structure, datamodel-code-generator can automatically create `__init__.py` files with `__all__` exports. This page explains how to control this behavior.

## Quick Overview

| Option | Description |
|--------|-------------|
| `--all-exports-scope` | Control which modules get `__all__` exports |
| `--all-exports-collision-strategy` | Handle name collisions in recursive exports |
| `--treat-dot-as-module` | Convert dots in names to nested modules |

---

## `--all-exports-scope`

Controls the scope of `__all__` generation in `__init__.py` files.

| Value | Description |
|-------|-------------|
| `none` | No `__all__` generation (default) |
| `local` | Export only the module's own definitions |
| `recursive` | Export all definitions from child modules |

### Example: `none` (default)

```bash
datamodel-codegen --input schemas/ --output models/
```

```python
# models/__init__.py
# (empty or minimal imports)
```

### Example: `local`

```bash
datamodel-codegen --input schemas/ --output models/ --all-exports-scope local
```

```python
# models/__init__.py
from .user import User
from .order import Order

__all__ = ["User", "Order"]
```

### Example: `recursive`

```bash
datamodel-codegen --input schemas/ --output models/ --all-exports-scope recursive
```

```python
# models/__init__.py
from .user import User
from .order import Order
from .common.status import Status
from .common.types import ID, Timestamp

__all__ = ["User", "Order", "Status", "ID", "Timestamp"]
```

---

## `--all-exports-collision-strategy`

When using `--all-exports-scope recursive`, name collisions can occur if multiple modules define the same class name. This option controls how to handle them.

| Value | Description |
|-------|-------------|
| `minimal-prefix` | Add minimum module path prefix to disambiguate |
| `full-prefix` | Use complete module path for all exports |

### The Problem

```text
models/
├── user/
│   └── types.py      # defines `ID`
└── order/
    └── types.py      # also defines `ID`
```

Both modules define `ID`, causing a collision when exporting recursively.

### Solution: `minimal-prefix`

```bash
datamodel-codegen --input schemas/ --output models/ \
  --all-exports-scope recursive \
  --all-exports-collision-strategy minimal-prefix
```

```python
# models/__init__.py
from .user.types import ID as user_ID
from .order.types import ID as order_ID

__all__ = ["user_ID", "order_ID"]
```

Only colliding names get prefixed.

### Solution: `full-prefix`

```bash
datamodel-codegen --input schemas/ --output models/ \
  --all-exports-scope recursive \
  --all-exports-collision-strategy full-prefix
```

```python
# models/__init__.py
from .user.types import ID as user_types_ID
from .order.types import ID as order_types_ID

__all__ = ["user_types_ID", "order_types_ID"]
```

All names use the full module path prefix.

---

## `--treat-dot-as-module`

Converts dots in schema names to nested module directories.

### Without `--treat-dot-as-module`

Schema with `title: "api.v1.User"` generates:

```python
# models.py
class ApiV1User(BaseModel):
    ...
```

### With `--treat-dot-as-module`

```bash
datamodel-codegen --input schema.json --output models/ --treat-dot-as-module
```

Schema with `title: "api.v1.User"` generates:

```text
models/
├── __init__.py
└── api/
    ├── __init__.py
    └── v1/
        ├── __init__.py
        └── user.py      # contains class User
```

This is useful for:
- Organizing large schemas by namespace
- Mirroring API versioning structure
- Keeping related models together

---

## Common Patterns

### Pattern 1: Flat output with local exports

Best for small to medium projects with a single output file or simple structure.

```bash
datamodel-codegen --input schema.yaml --output models/ --all-exports-scope local
```

### Pattern 2: Hierarchical with recursive exports

Best for large projects with many schemas organized by domain.

```bash
datamodel-codegen --input schemas/ --output models/ \
  --all-exports-scope recursive \
  --all-exports-collision-strategy minimal-prefix \
  --treat-dot-as-module
```

### Pattern 3: OpenAPI with module structure

Best for OpenAPI schemas with versioned endpoints.

```bash
datamodel-codegen --input openapi.yaml --output models/ \
  --treat-dot-as-module \
  --all-exports-scope recursive
```

---

## Troubleshooting

### Import errors after generation

If you see `ImportError: cannot import name 'X'`:

1. Check if `__all__` is generated correctly
2. Verify the module structure matches your imports
3. Try `--all-exports-scope local` first, then `recursive`

### Name collisions

If you see duplicate class names:

1. Use `--all-exports-collision-strategy minimal-prefix`
2. Or use `--all-exports-collision-strategy full-prefix` for maximum clarity
3. Consider restructuring your schemas to avoid collisions

### Circular imports

If you encounter circular import errors:

1. Check the generated `__init__.py` files
2. Consider using `--all-exports-scope local` instead of `recursive`
3. Use lazy imports in your application code

---

## See Also

- [CLI Reference: `--all-exports-scope`](cli-reference/general-options.md#all-exports-scope)
- [CLI Reference: `--all-exports-collision-strategy`](cli-reference/general-options.md#all-exports-collision-strategy)
- [CLI Reference: `--treat-dot-as-module`](cli-reference/template-customization.md#treat-dot-as-module)
- [Model Reuse and Deduplication](model-reuse.md)
