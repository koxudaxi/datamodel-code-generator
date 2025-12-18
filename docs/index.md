# datamodel-code-generator

🚀 Generate Python data models from schema definitions in seconds.

[![PyPI version](https://badge.fury.io/py/datamodel-code-generator.svg)](https://pypi.python.org/pypi/datamodel-code-generator)
[![Downloads](https://pepy.tech/badge/datamodel-code-generator/month)](https://pepy.tech/project/datamodel-code-generator)
[![Python Version](https://img.shields.io/pypi/pyversions/datamodel-code-generator)](https://pypi.python.org/pypi/datamodel-code-generator)

---

## ✨ What it does

- 📄 Converts **OpenAPI 3**, **JSON Schema**, **GraphQL**, and raw data (JSON/YAML/CSV) into Python models
- 🎯 Generates **Pydantic v1/v2**, **dataclasses**, **TypedDict**, or **msgspec** output
- 🔗 Handles complex schemas: `$ref`, `allOf`, `oneOf`, `anyOf`, enums, and nested types
- ✅ Produces type-safe, validated code ready for your IDE and type checker

---

## 📦 Installation

=== "pip"

    ```bash
    pip install datamodel-code-generator
    ```

=== "uv"

    ```bash
    uv add datamodel-code-generator
    ```

=== "conda"

    ```bash
    conda install -c conda-forge datamodel-code-generator
    ```

=== "pipx (global)"

    ```bash
    pipx install datamodel-code-generator
    ```

=== "uvx (global)"

    ```bash
    uvx datamodel-codegen --help
    ```

---

## 🏃 Quick Start

### 1️⃣ Create a schema file

```json title="pet.json"
--8<-- "tests/data/jsonschema/tutorial_pet.json"
```

### 2️⃣ Run the generator

```bash
datamodel-codegen --input pet.json --input-file-type jsonschema --output-model-type pydantic_v2.BaseModel --output model.py
```

### 3️⃣ Use your models

```python title="model.py"
--8<-- "tests/data/expected/main/jsonschema/tutorial_pet_v2.py"
```

🎉 That's it! Your schema is now a fully-typed Python model.

---

## 📥 Choose Your Input

| Input Type | File Types | Example |
|------------|------------|---------|
| 📘 [OpenAPI 3](openapi.md) | `.yaml`, `.json` | API specifications |
| 📋 [JSON Schema](jsonschema.md) | `.json` | Data validation schemas |
| 🔷 [GraphQL](graphql.md) | `.graphql` | GraphQL type definitions |
| 📊 [JSON/YAML Data](jsondata.md) | `.json`, `.yaml` | Infer schema from data |

---

## 📤 Choose Your Output

```bash
# 🆕 Pydantic v2 (recommended for new projects)
datamodel-codegen --output-model-type pydantic_v2.BaseModel ...

# 🔄 Pydantic v1 (default, for compatibility)
datamodel-codegen --output-model-type pydantic.BaseModel ...

# 🏗️ Python dataclasses
datamodel-codegen --output-model-type dataclasses.dataclass ...

# 📝 TypedDict (for type hints without validation)
datamodel-codegen --output-model-type typing.TypedDict ...

# ⚡ msgspec (high-performance serialization)
datamodel-codegen --output-model-type msgspec.Struct ...
```

See [Supported Data Types](supported-data-types.md) for the full list.

---

## 🍳 Common Recipes

### 🌐 Generate from URL {#http-extra-option}

```bash
pip install 'datamodel-code-generator[http]'
datamodel-codegen --url https://example.com/api/openapi.yaml --output model.py
```

### ⚙️ Use with pyproject.toml

```toml title="pyproject.toml"
[tool.datamodel-codegen]
input = "schema.yaml"
output = "src/models.py"
output-model-type = "pydantic_v2.BaseModel"
snake-case-field = true
```

Then simply run:

```bash
datamodel-codegen
```

See [pyproject.toml Configuration](pyproject_toml.md) for more options.

### 🐍 Snake-case field names

```bash
datamodel-codegen --snake-case-field --input schema.json --output model.py
```

---

## 📚 Next Steps

- 🖥️ **[CLI Reference](cli-reference/index.md)** - All command-line options with examples
- ⚙️ **[pyproject.toml Configuration](pyproject_toml.md)** - Configure via pyproject.toml
- 🎨 **[Custom Templates](custom_template.md)** - Customize generated code with Jinja2
- 🖌️ **[Code Formatting](formatting.md)** - Configure black, isort, and ruff
- ❓ **[FAQ](faq.md)** - Common questions and troubleshooting

---

## 💖 Sponsors

<table>
  <tr>
    <td valign="top" align="center">
      <a href="https://github.com/astral-sh">
        <img src="https://avatars.githubusercontent.com/u/115962839?s=200&v=4" alt="Astral Logo" style="width: 100px;">
        <p>Astral</p>
      </a>
    </td>
  </tr>
</table>

---

## 🏢 Used by

These open-source projects use datamodel-code-generator:

[Apache Iceberg](https://github.com/apache/iceberg) ·
[Netflix](https://github.com/Netflix/consoleme) ·
[DataDog](https://github.com/DataDog/integrations-core) ·
[PostHog](https://github.com/PostHog/posthog) ·
[Airbyte](https://github.com/airbytehq/airbyte) ·
[AWS Lambda Powertools](https://github.com/awslabs/aws-lambda-powertools-python)
· [and more...](https://github.com/koxudaxi/datamodel-code-generator#projects-that-use-datamodel-code-generator)
