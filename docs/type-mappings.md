<!-- related-cli-options: --type-mappings, --strict-types, --output-datetime-class, --use-pendulum, --use-decimal-for-multiple-of -->

# Type Mappings and Custom Types

datamodel-code-generator allows you to customize how schema types are mapped to Python types. This is essential for projects with specific type requirements, datetime handling preferences, or third-party library integrations.

## Quick Overview

| Option | Description |
|--------|-------------|
| `--type-mappings` | Map schema types to custom Python types |
| `--strict-types` | Use Pydantic strict types for validation |
| `--output-datetime-class` | Choose datetime output type |
| `--use-pendulum` | Use Pendulum library for datetime types |
| `--use-decimal-for-multiple-of` | Use Decimal for multipleOf constraints |

---

## `--type-mappings`

Maps schema types to custom Python types. This is the most flexible way to customize type output.

### Format

```bash
--type-mappings <schema_type>=<python_type> [<schema_type>=<python_type> ...]
```

### Basic Examples

```bash
# Map string format to custom type
datamodel-codegen --input schema.json --output models.py \
  --type-mappings "string+uri=pydantic.HttpUrl"

# Map integer to custom ID type
datamodel-codegen --input schema.json --output models.py \
  --type-mappings "integer=myproject.types.ID"

# Multiple mappings
datamodel-codegen --input schema.json --output models.py \
  --type-mappings "string+date-time=datetime.datetime" "string+uri=str"
```

### Mapping Syntax

| Syntax | Description | Example |
|--------|-------------|---------|
| `type` | Map base type | `integer=int` |
| `type+format` | Map type with format | `string+uuid=uuid.UUID` |
| `type+format+pattern` | Map with pattern | `string++^[A-Z]{2}$=CountryCode` |

### Common Mappings

```bash
# Use AwareDatetime for timezone-aware datetimes
--type-mappings "string+date-time=pydantic.AwareDatetime"

# Use custom Email type
--type-mappings "string+email=myapp.types.Email"

# Use pathlib.Path for file paths
--type-mappings "string+uri-reference=pathlib.Path"

# Use Decimal for money
--type-mappings "number=decimal.Decimal"
```

### pyproject.toml Configuration

```toml
[tool.datamodel-codegen]
type-mappings = [
    "string+date-time=datetime.datetime",
    "string+uuid=uuid.UUID",
    "number=decimal.Decimal",
]
```

---

## `--strict-types`

Generates Pydantic strict types that don't perform type coercion during validation.

### Available Strict Types

| Value | Strict Type | Rejects |
|-------|-------------|---------|
| `str` | `StrictStr` | Integers, floats |
| `int` | `StrictInt` | Strings, floats |
| `float` | `StrictFloat` | Strings, integers |
| `bool` | `StrictBool` | Strings, integers |
| `bytes` | `StrictBytes` | Strings |

### Without `--strict-types`

```python
class User(BaseModel):
    id: int        # Accepts "123" and converts to 123
    name: str      # Accepts 123 and converts to "123"
    active: bool   # Accepts 1 and converts to True
```

### With `--strict-types`

```bash
datamodel-codegen --input schema.json --output models.py \
  --strict-types str int bool
```

```python
from pydantic import StrictBool, StrictInt, StrictStr

class User(BaseModel):
    id: StrictInt      # Rejects "123", requires integer
    name: StrictStr    # Rejects 123, requires string
    active: StrictBool # Rejects 1, requires boolean
```

### When to use

- API validation where type coercion is undesirable
- Data pipelines requiring exact types
- Security-sensitive applications
- Testing environments requiring strict type checking

---

## `--output-datetime-class`

Controls the Python type used for `date-time` formatted strings.

| Value | Output Type | Description |
|-------|-------------|-------------|
| `datetime` | `datetime.datetime` | Standard library datetime (default) |
| `AwareDatetime` | `pydantic.AwareDatetime` | Requires timezone info |
| `NaiveDatetime` | `pydantic.NaiveDatetime` | Rejects timezone info |

### Default behavior

```python
from datetime import datetime

class Event(BaseModel):
    created_at: datetime  # Accepts both aware and naive
```

### AwareDatetime (recommended for APIs)

```bash
datamodel-codegen --input schema.json --output models.py \
  --output-datetime-class AwareDatetime
```

```python
from pydantic import AwareDatetime

class Event(BaseModel):
    created_at: AwareDatetime  # Requires timezone, e.g., 2024-01-01T00:00:00Z
```

### NaiveDatetime

```bash
datamodel-codegen --input schema.json --output models.py \
  --output-datetime-class NaiveDatetime
```

```python
from pydantic import NaiveDatetime

class Event(BaseModel):
    created_at: NaiveDatetime  # Rejects timezone, e.g., 2024-01-01T00:00:00
```

### When to use each

| Use Case | Recommended Class |
|----------|-------------------|
| REST APIs | `AwareDatetime` |
| Database models | `datetime` or `NaiveDatetime` |
| Logs with UTC timestamps | `AwareDatetime` |
| Local time applications | `NaiveDatetime` |

---

## `--use-pendulum`

Uses [Pendulum](https://pendulum.eustace.io/) library types instead of standard library datetime.

```bash
pip install pendulum
datamodel-codegen --input schema.json --output models.py --use-pendulum
```

### Output

```python
import pendulum

class Event(BaseModel):
    created_at: pendulum.DateTime
    date: pendulum.Date
    time: pendulum.Time
```

### Benefits of Pendulum

- Timezone handling is simpler and more intuitive
- Human-friendly datetime manipulation
- Better serialization defaults
- Immutable by default

### When to use

- Projects already using Pendulum
- Applications requiring complex datetime manipulation
- When timezone handling is a priority

---

## `--use-decimal-for-multiple-of`

Uses `Decimal` type for numbers with `multipleOf` constraints to avoid floating-point precision issues.

### The Problem

```yaml
properties:
  price:
    type: number
    multipleOf: 0.01  # Currency precision
```

Without this option, floating-point arithmetic can cause validation issues:

```python
# 0.1 + 0.2 = 0.30000000000000004 in floating-point
price = 0.30000000000000004  # May fail multipleOf validation
```

### Solution

```bash
datamodel-codegen --input schema.json --output models.py \
  --use-decimal-for-multiple-of
```

```python
from decimal import Decimal

class Product(BaseModel):
    price: Decimal  # Exact decimal arithmetic
```

### When to use

- Financial applications
- Scientific calculations requiring precision
- Any schema with `multipleOf` constraints

---

## Common Patterns

### Pattern 1: Financial application

```bash
datamodel-codegen --input schema.json --output models.py \
  --use-decimal-for-multiple-of \
  --type-mappings "number=decimal.Decimal" \
  --strict-types str int
```

### Pattern 2: Strict API validation

```bash
datamodel-codegen --input schema.json --output models.py \
  --strict-types str int float bool \
  --output-datetime-class AwareDatetime \
  --field-constraints
```

### Pattern 3: Custom type library

```bash
datamodel-codegen --input schema.json --output models.py \
  --type-mappings \
    "string+email=myapp.types.Email" \
    "string+uri=myapp.types.URL" \
    "integer=myapp.types.ID"
```

### Pattern 4: Pendulum datetime handling

```bash
datamodel-codegen --input schema.json --output models.py \
  --use-pendulum \
  --strict-types str int
```

---

## Type Mapping Reference

### Common Format Mappings

| Schema Format | Default Type | Common Custom Mapping |
|---------------|--------------|----------------------|
| `date-time` | `datetime` | `pydantic.AwareDatetime`, `pendulum.DateTime` |
| `date` | `date` | `pendulum.Date` |
| `time` | `time` | `pendulum.Time` |
| `uuid` | `UUID` | `str` |
| `email` | `EmailStr` | `str`, custom Email class |
| `uri` | `AnyUrl` | `str`, `pydantic.HttpUrl` |
| `binary` | `bytes` | `str` (base64-encoded) |

---

## See Also

- [CLI Reference: `--type-mappings`](cli-reference/typing-customization.md#type-mappings)
- [CLI Reference: `--strict-types`](cli-reference/typing-customization.md#strict-types)
- [CLI Reference: `--output-datetime-class`](cli-reference/typing-customization.md#output-datetime-class)
- [CLI Reference: `--use-pendulum`](cli-reference/typing-customization.md#use-pendulum)
- [Field Constraints](field-constraints.md)
- [Python Version Compatibility](python-version-compatibility.md)
