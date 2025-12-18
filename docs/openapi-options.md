<!-- related-cli-options: --openapi-scopes, --include-path-parameters, --use-operation-id-as-name, --read-only-write-only-model-type, --validation -->

# OpenAPI-Specific Options

When working with OpenAPI specifications, datamodel-code-generator provides several options to control how schemas, operations, and special properties are handled. This page explains when and how to use each option.

## Quick Overview

| Option | Description |
|--------|-------------|
| `--openapi-scopes` | Select which parts of the spec to generate models from |
| `--include-path-parameters` | Include path parameters in generated models |
| `--use-operation-id-as-name` | Name models using operation IDs |
| `--read-only-write-only-model-type` | Generate separate models for read/write contexts |
| `--validation` | Enable OpenAPI validation constraints (deprecated) |

---

## `--openapi-scopes`

Controls which sections of the OpenAPI specification to generate models from.

| Scope | Description |
|-------|-------------|
| `schemas` | Generate from `#/components/schemas` (default) |
| `parameters` | Generate from `#/components/parameters` |
| `paths` | Generate from path operation parameters |

### Default behavior (schemas only)

```bash
datamodel-codegen --input openapi.yaml --output models.py
```

Generates models only from `#/components/schemas`.

### Include parameters

```bash
datamodel-codegen --input openapi.yaml --output models.py \
  --openapi-scopes schemas parameters
```

Also generates models from `#/components/parameters`.

### Include path-level definitions

```bash
datamodel-codegen --input openapi.yaml --output models.py \
  --openapi-scopes schemas parameters paths
```

Generates models from all sources, including inline path operation parameters.

### When to use each scope

| Use Case | Recommended Scopes |
|----------|-------------------|
| Basic model generation | `schemas` (default) |
| Reusable parameter types | `schemas parameters` |
| Complete API coverage | `schemas parameters paths` |

---

## `--include-path-parameters`

Includes path parameters as fields in generated models.

### OpenAPI Example

```yaml
paths:
  /users/{user_id}/orders/{order_id}:
    get:
      operationId: getOrder
      parameters:
        - name: user_id
          in: path
          schema:
            type: string
        - name: order_id
          in: path
          schema:
            type: integer
```

### Without `--include-path-parameters`

```python
class GetOrderResponse(BaseModel):
    # Only response body fields
    items: list[Item]
    total: float
```

### With `--include-path-parameters`

```bash
datamodel-codegen --input openapi.yaml --output models.py --include-path-parameters
```

```python
class GetOrderResponse(BaseModel):
    user_id: str
    order_id: int
    items: list[Item]
    total: float
```

### When to use

- Building request validation models that include URL parameters
- Creating unified request/response types for API clients
- Generating models for frameworks that expect all parameters in one object

---

## `--use-operation-id-as-name`

Uses the `operationId` from OpenAPI operations to name generated models instead of deriving names from paths.

### OpenAPI Example

```yaml
paths:
  /users/{id}:
    get:
      operationId: getUserById
      responses:
        '200':
          content:
            application/json:
              schema:
                type: object
                properties:
                  id: { type: integer }
                  name: { type: string }
```

### Without `--use-operation-id-as-name`

```python
class UsersIdGetResponse(BaseModel):  # Derived from path
    id: int
    name: str
```

### With `--use-operation-id-as-name`

```bash
datamodel-codegen --input openapi.yaml --output models.py --use-operation-id-as-name
```

```python
class GetUserByIdResponse(BaseModel):  # Uses operationId
    id: int
    name: str
```

### When to use

- When `operationId` values are well-designed and descriptive
- For consistency with generated API clients (e.g., OpenAPI Generator)
- When path-derived names are too verbose or unclear

---

## `--read-only-write-only-model-type`

Generates separate model variants for properties marked as `readOnly` or `writeOnly` in OpenAPI.

### OpenAPI Example

```yaml
components:
  schemas:
    User:
      type: object
      properties:
        id:
          type: integer
          readOnly: true        # Only in responses
        password:
          type: string
          writeOnly: true       # Only in requests
        name:
          type: string          # In both
```

### Without `--read-only-write-only-model-type`

```python
class User(BaseModel):
    id: Optional[int] = None      # Both included
    password: Optional[str] = None
    name: Optional[str] = None
```

### With `--read-only-write-only-model-type`

```bash
datamodel-codegen --input openapi.yaml --output models.py \
  --read-only-write-only-model-type all
```

```python
class User(BaseModel):
    """Base model with all fields."""
    id: Optional[int] = None
    password: Optional[str] = None
    name: Optional[str] = None

class UserRead(BaseModel):
    """For responses - excludes writeOnly fields."""
    id: Optional[int] = None
    name: Optional[str] = None

class UserWrite(BaseModel):
    """For requests - excludes readOnly fields."""
    password: Optional[str] = None
    name: Optional[str] = None
```

### Values

| Value | Description |
|-------|-------------|
| `all` | Generate both Read and Write variants |
| `read` | Generate only Read variants |
| `write` | Generate only Write variants |

### When to use

- APIs with distinct request/response schemas
- Strict type checking for API clients
- When `readOnly`/`writeOnly` properties are heavily used

---

## `--validation` (Deprecated)

!!! warning "Deprecated"
    Use `--field-constraints` instead. The `--validation` option is maintained for backward compatibility.

Enables validation constraints from OpenAPI schemas.

```bash
# Deprecated
datamodel-codegen --input openapi.yaml --output models.py --validation

# Recommended
datamodel-codegen --input openapi.yaml --output models.py --field-constraints
```

See [Field Constraints](field-constraints.md) for details.

---

## Common Patterns

### Pattern 1: Basic API models

For simple APIs where you only need schema models:

```bash
datamodel-codegen --input openapi.yaml --output models.py
```

### Pattern 2: Full API client models

For generating complete models for an API client:

```bash
datamodel-codegen --input openapi.yaml --output models/ \
  --openapi-scopes schemas parameters paths \
  --use-operation-id-as-name \
  --include-path-parameters
```

### Pattern 3: Strict request/response separation

For APIs with distinct input/output shapes:

```bash
datamodel-codegen --input openapi.yaml --output models/ \
  --read-only-write-only-model-type all \
  --field-constraints
```

### Pattern 4: Versioned API structure

For large APIs with versioned endpoints:

```bash
datamodel-codegen --input openapi.yaml --output models/ \
  --treat-dot-as-module \
  --use-operation-id-as-name \
  --all-exports-scope recursive
```

---

## OpenAPI Version Support

| OpenAPI Version | Support |
|-----------------|---------|
| 3.0.x | Full support |
| 3.1.x | Full support |
| 2.0 (Swagger) | Partial support |

---

## See Also

- [CLI Reference: OpenAPI-only Options](cli-reference/openapi-only-options.md)
- [Field Constraints](field-constraints.md)
- [Module Structure and Exports](module-exports.md)
- [OpenAPI Input Format](openapi.md)
