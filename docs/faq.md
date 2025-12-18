# ❓ Frequently Asked Questions

## 📋 Schema Handling

### 🔀 oneOf/anyOf generates unexpected Union types

When using `oneOf` or `anyOf`, the generated models may not match your expectations. Use `--union-mode` to control how unions are generated:

```bash
# Smart union (Pydantic v2 only) - validates against types in order
datamodel-codegen --union-mode smart --output-model-type pydantic_v2.BaseModel ...

# Left-to-right validation
datamodel-codegen --union-mode left_to_right ...
```

See [CLI Reference: `--union-mode`](cli-reference/model-customization.md#union-mode) for details.

### 🔗 allOf doesn't merge properties as expected

Control how `allOf` schemas merge fields:

```bash
# Merge only constraints (minItems, maxItems, pattern, etc.) - default
datamodel-codegen --allof-merge-mode constraints ...

# Merge constraints + annotations (default, examples)
datamodel-codegen --allof-merge-mode all ...

# Don't merge any fields
datamodel-codegen --allof-merge-mode none ...
```

See [CLI Reference: `--allof-merge-mode`](cli-reference/typing-customization.md#allof-merge-mode) for details.

📎 Related: [#399](https://github.com/koxudaxi/datamodel-code-generator/issues/399)

### 📁 How to generate from multiple schema files?

Use a directory as input, or use `$ref` to reference other files:

```bash
# Generate from directory containing multiple schemas
datamodel-codegen --input schemas/ --output models/
```

For schemas with cross-file `$ref`, ensure you have the HTTP extra for remote refs:

```bash
pip install 'datamodel-code-generator[http]'
```

📎 Related: [#215](https://github.com/koxudaxi/datamodel-code-generator/issues/215)

---

## 🔍 Type Checking

### ⚠️ mypy complains about Field constraints

If mypy reports errors about `conint`, `constr`, or other constrained types, use `--field-constraints` or `--use-annotated`:

```bash
# Use Field(..., ge=0) instead of conint(ge=0)
datamodel-codegen --field-constraints ...

# Use Annotated[int, Field(ge=0)]
datamodel-codegen --use-annotated ...
```

See [Field Constraints](field-constraints.md) for more information.

### 🤔 Type checker doesn't understand generated types

Ensure you're using the correct target Python version:

```bash
datamodel-codegen --target-python-version 3.11 ...
```

This affects type syntax generation (e.g., `list[str]` vs `List[str]`, `X | Y` vs `Union[X, Y]`).

---

## 🏷️ Field Naming

### 🚫 Property names conflict with Python reserved words

Properties like `class`, `from`, `import` are automatically renamed with a `field_` prefix. Control this behavior:

```bash
# Custom prefix (default: "field")
datamodel-codegen --special-field-name-prefix my_prefix ...

# Remove special prefix entirely
datamodel-codegen --remove-special-field-name-prefix ...
```

### 🔣 Field names have special characters

JSON/YAML property names with spaces, dashes, or special characters are converted to valid Python identifiers. An alias is automatically generated to preserve the original name:

```python
class Model(BaseModel):
    my_field: str = Field(..., alias='my-field')
```

To disable aliases:

```bash
datamodel-codegen --no-alias ...
```

See [Field Aliases](aliases.md) for custom alias mappings.

### 🐍 Want snake_case field names from camelCase

```bash
datamodel-codegen --snake-case-field ...
```

This generates snake_case field names with camelCase aliases:

```python
class User(BaseModel):
    first_name: str = Field(..., alias='firstName')
```

---

## 🔄 Output Stability

### ⏰ Generated output changes on every run

The timestamp in the header changes on each run. Disable it for reproducible output:

```bash
datamodel-codegen --disable-timestamp ...
```

### 🌍 Output differs between environments

Ensure consistent formatting across environments:

```bash
# Explicitly set formatters
datamodel-codegen --formatters black isort ...

# Or disable formatting entirely for raw output
datamodel-codegen --formatters ...
```

Also ensure the same Python version and formatter configurations (`pyproject.toml`) are used.

### 🤖 CI fails because generated code is different

Use `--check` mode in CI to verify generated files are up-to-date:

```bash
datamodel-codegen --check --input schema.yaml --output models.py
```

This exits with code 1 if the output would differ, without modifying files.

---

## ⚡ Performance

### 🐢 Generation is slow for large schemas

For very large schemas with many models:

1. Use `--reuse-model` to deduplicate identical models
2. Consider splitting schemas into multiple files
3. Use `--disable-warnings` to reduce output

```bash
datamodel-codegen --reuse-model --disable-warnings ...
```

See [Model Reuse and Deduplication](model-reuse.md) for details.

---

## 🔧 Output Model Types

### 🤷 Which output model type should I use?

- **Pydantic v2** (`pydantic_v2.BaseModel`): ✨ Recommended for new projects. Better performance and modern API.
- **Pydantic v1** (`pydantic.BaseModel`): 🔄 Default for backward compatibility with existing codebases.
- **dataclasses**: Simple data containers without validation.
- **TypedDict**: Type hints for dict structures.
- **msgspec**: High-performance serialization.

See [Output Model Types](what_is_the_difference_between_v1_and_v2.md) for a detailed comparison.

```bash
# For new projects
datamodel-codegen --output-model-type pydantic_v2.BaseModel ...
```

See [Pydantic v1 vs v2](what_is_the_difference_between_v1_and_v2.md) for migration details.

📎 Related: [#803](https://github.com/koxudaxi/datamodel-code-generator/issues/803)

### 💥 Generated code doesn't work with my Pydantic version

Ensure the output model type matches your installed Pydantic version:

```bash
# Check your Pydantic version
python -c "import pydantic; print(pydantic.VERSION)"

# Generate for Pydantic v2
datamodel-codegen --output-model-type pydantic_v2.BaseModel ...

# Generate for Pydantic v1
datamodel-codegen --output-model-type pydantic.BaseModel ...
```

---

## 🌐 Remote Schemas

### 📡 Cannot fetch schema from URL

Install the HTTP extra:

```bash
pip install 'datamodel-code-generator[http]'
```

For authenticated endpoints:

```bash
datamodel-codegen --url https://api.example.com/schema.yaml \
    --http-headers "Authorization: Bearer TOKEN" \
    --output model.py
```

### 🔒 SSL certificate errors

For development/testing with self-signed certificates:

```bash
datamodel-codegen --url https://... --http-ignore-tls --output model.py
```

!!! warning "⚠️ Security Notice"
    Only use `--http-ignore-tls` in trusted environments.

---

## 📘 OpenAPI Specific

### 📝 How to handle readOnly/writeOnly properties?

Use `--read-only-write-only-model-type` to generate separate Request/Response models:

```bash
# Generate Request/Response models only
datamodel-codegen --read-only-write-only-model-type request-response ...

# Generate Base + Request + Response models
datamodel-codegen --read-only-write-only-model-type all ...
```

📎 Related: [#727](https://github.com/koxudaxi/datamodel-code-generator/issues/727)

### ❓ Why are nullable fields not Optional?

Use `--strict-nullable` to treat nullable fields as truly optional:

```bash
datamodel-codegen --strict-nullable ...
```

📎 Related: [#327](https://github.com/koxudaxi/datamodel-code-generator/issues/327)

---

## 🔧 Advanced

### 📦 How to use TypeAlias instead of RootModel?

Use `--use-type-alias` (experimental) to generate type aliases instead of root models:

```bash
datamodel-codegen --use-type-alias --output-model-type pydantic_v2.BaseModel ...
```

See [Root Models and Type Aliases](root-model-and-type-alias.md) for details.

📎 Related: [#2505](https://github.com/koxudaxi/datamodel-code-generator/issues/2505)

---

## 📖 See Also

- 🖥️ [CLI Reference](cli-reference/index.md) - Complete option documentation
- ⚙️ [pyproject.toml Configuration](pyproject_toml.md) - Configure options via file
- 🐛 [GitHub Issues](https://github.com/koxudaxi/datamodel-code-generator/issues) - Report bugs or request features
- 💬 [Discussions](https://github.com/koxudaxi/datamodel-code-generator/discussions) - Ask questions and share ideas
