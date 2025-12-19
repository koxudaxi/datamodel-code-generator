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

=== "uv tool (Recommended)"

    ```bash
    uv tool install datamodel-code-generator
    ```

=== "pip"

    ```bash
    pip install datamodel-code-generator
    ```

=== "uv (project)"

    ```bash
    uv add datamodel-code-generator
    ```

=== "conda"

    ```bash
    conda install -c conda-forge datamodel-code-generator
    ```

=== "pipx"

    ```bash
    pipx install datamodel-code-generator
    ```

=== "uvx (one-shot)"

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

### 🔄 CI/CD Integration

Verify generated code stays in sync with schemas using `--check`:

```bash
datamodel-codegen --input schema.yaml --output models.py --disable-timestamp --check
```

See [CI/CD Integration](ci-cd.md) for GitHub Actions and more.

---

## 📚 Next Steps

- 🖥️ **[CLI Reference](cli-reference/index.md)** - All command-line options with examples
- ⚙️ **[pyproject.toml Configuration](pyproject_toml.md)** - Configure via pyproject.toml
- 🚀 **[One-liner Usage](oneliner.md)** - uvx, pipx, clipboard integration
- 🔄 **[CI/CD Integration](ci-cd.md)** - GitHub Actions and CI validation
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

These projects use datamodel-code-generator. See the linked examples for real-world usage.

- [PostHog/posthog](https://github.com/PostHog/posthog) - *[Generate models via npm run](https://github.com/PostHog/posthog/blob/e1a55b9cb38d01225224bebf8f0c1e28faa22399/package.json#L41)*
- [airbytehq/airbyte](https://github.com/airbytehq/airbyte) - *[Generate Python, Java/Kotlin, and Typescript protocol models](https://github.com/airbytehq/airbyte-protocol/tree/main/protocol-models/bin)*
- [apache/iceberg](https://github.com/apache/iceberg) - *[Generate Python code](https://github.com/apache/iceberg/blob/d2e1094ee0cc6239d43f63ba5114272f59d605d2/open-api/README.md?plain=1#L39)*
- [open-metadata/OpenMetadata](https://github.com/open-metadata/OpenMetadata) - *[datamodel_generation.py](https://github.com/open-metadata/OpenMetadata/blob/main/scripts/datamodel_generation.py)*
- [awslabs/aws-lambda-powertools-python](https://github.com/awslabs/aws-lambda-powertools-python) - *[Recommended for advanced-use-cases](https://awslabs.github.io/aws-lambda-powertools-python/2.6.0/utilities/parser/#advanced-use-cases)*
- [Netflix/consoleme](https://github.com/Netflix/consoleme) - *[Generate models from Swagger](https://github.com/Netflix/consoleme/blob/master/docs/gitbook/faq.md#how-do-i-generate-models-from-the-swagger-specification)*
- [DataDog/integrations-core](https://github.com/DataDog/integrations-core) - *[Config models](https://github.com/DataDog/integrations-core/blob/master/docs/developer/meta/config-models.md)*
- [argoproj-labs/hera](https://github.com/argoproj-labs/hera) - *[Makefile](https://github.com/argoproj-labs/hera/blob/c8cbf0c7a676de57469ca3d6aeacde7a5e84f8b7/Makefile#L53-L62)*
- [SeldonIO/MLServer](https://github.com/SeldonIO/MLServer) - *[generate-types.sh](https://github.com/SeldonIO/MLServer/blob/master/hack/generate-types.sh)*
- [geojupyter/jupytergis](https://github.com/geojupyter/jupytergis) - *[Python type generation from JSONSchema](https://jupytergis.readthedocs.io/en/latest/contributor_guide/explanation/code-generation.html)*
- [Nike-Inc/brickflow](https://github.com/Nike-Inc/brickflow) - *[Code generate tools](https://github.com/Nike-Inc/brickflow/blob/e3245bf638588867b831820a6675ada76b2010bf/tools/README.md?plain=1#L8)*
- [cloudcoil/cloudcoil](https://github.com/cloudcoil/cloudcoil) - *[Model generation](https://github.com/cloudcoil/cloudcoil#%EF%B8%8F-model-generation)*
- [IBM/compliance-trestle](https://github.com/IBM/compliance-trestle) - *[Building models from OSCAL schemas](https://github.com/IBM/compliance-trestle/blob/develop/docs/contributing/website.md#building-the-models-from-the-oscal-schemas)*
- [hashintel/hash](https://github.com/hashintel/hash) - *[codegen.sh](https://github.com/hashintel/hash/blob/9762b1a1937e14f6b387677e4c7fe4a5f3d4a1e1/libs/%40local/hash-graph-client/python/scripts/codegen.sh#L21-L39)*

[See all dependents →](https://github.com/koxudaxi/datamodel-code-generator/network/dependents)
