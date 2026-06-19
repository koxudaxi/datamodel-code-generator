# datamodel-code-generator

🚀 Generate Python data models from schema definitions in seconds.

[![PyPI version](https://img.shields.io/pypi/v/datamodel-code-generator.svg)](https://pypi.python.org/pypi/datamodel-code-generator)
[![Conda-forge](https://img.shields.io/conda/v/conda-forge/datamodel-code-generator)](https://anaconda.org/conda-forge/datamodel-code-generator)
[![Downloads](https://api.pepy.tech/badge/datamodel-code-generator/month)](https://pepy.tech/projects/datamodel-code-generator)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/datamodel-code-generator)](https://pypi.python.org/pypi/datamodel-code-generator)
[![codecov](https://codecov.io/gh/koxudaxi/datamodel-code-generator/graph/badge.svg?token=plzSSFb9Li)](https://codecov.io/gh/koxudaxi/datamodel-code-generator)
![license](https://img.shields.io/github/license/koxudaxi/datamodel-code-generator.svg)
[![Pydantic v2](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/pydantic/pydantic/main/docs/badge/v2.json)](https://pydantic.dev)

---

## ✨ What it does

<!-- Source of truth: docs/assets/diagrams/hero.mmd — regenerate with `tox run -e diagrams` -->
![Schema files, raw data, and existing Python models flow through datamodel-code-generator into Python model output types](assets/diagrams/hero-light.svg#only-light){ align=center }
![Schema files, raw data, and existing Python models flow through datamodel-code-generator into Python model output types](assets/diagrams/hero-dark.svg#only-dark){ align=center }

Pick any one of the supported inputs and pick the Python model style you want as output.
`--input-model path/to/file.py:ClassName` can even retarget an existing Pydantic, dataclass, or TypedDict class defined
in another Python file to a different output type.

- 📄 Converts **OpenAPI 3**, **AsyncAPI**, **JSON Schema**, **Apache Avro**, **XML Schema**, **Protocol Buffers/gRPC**, **GraphQL**, **MCP tool schemas**, and raw data (JSON/YAML/CSV) into Python models
- 🐍 Generates from **existing Python types** (Pydantic, dataclass, TypedDict) via `--input-model`
- 🎯 Generates **Pydantic v2**, **Pydantic v2 dataclass**, **dataclasses**, **TypedDict**, or **msgspec** output
- 🔗 Handles complex schemas: `$ref`, `allOf`, `oneOf`, `anyOf`, enums, and nested types
- ✅ Produces type-safe, validated code ready for your IDE and type checker

---

## 🧪 Try It In Your Browser

Generate models in your browser without installing anything.

<p>
  <a class="md-button md-button--primary" href="playground.md" target="_self">Open Playground</a>
</p>

!!! note "Playground privacy"
    The playground runs datamodel-code-generator locally in your browser with Pyodide. Your schema and options are not
    sent to a backend for generation. If you copy a repro URL, the schema and options are encoded in the URL fragment
    (`#state=...`), which browsers do not send to the server; the full URL can still be stored in your browser history
    or wherever you share it.

---

## 📦 Installation

=== "uv tool (Recommended for CLI use)"

    ```bash
    uv tool install datamodel-code-generator
    ```

=== "pip"

    ```bash
    pip install datamodel-code-generator
    ```

=== "uv (project)"

    ```bash
    uv add --dev datamodel-code-generator
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

Use `uv tool install` when you want `datamodel-codegen` available as a standalone CLI. Use `uv add --dev` when a project
or CI workflow should pin the generator version in its lockfile.

---

!!! warning "Omitting --output-model-type is deprecated"
    Starting from version 0.53.0, omitting `--output-model-type` is deprecated.

    We recommend using `--output-model-type pydantic_v2.BaseModel` for new projects.

---

## 🏃 Quick Start

<!-- BEGIN AUTO-GENERATED PRESET QUICK START -->
### Command

```bash
datamodel-codegen \
  --input schema.json \
  --input-file-type jsonschema \
  --output-model-type pydantic_v2.BaseModel \
  --preset standard-py312-20260619 \
  --output model.py
```

This quick start uses `standard-py312-20260619` as the modern Python 3.12 baseline.
Preset names include the target Python version: `py312` means Python 3.12.

See [CLI Reference](cli-reference/index.md) for all options. See [Presets](presets.md),
[`--preset`](cli-reference/base-options.md#preset), [`--input-file-type`](cli-reference/base-options.md#input-file-type), and
[`--output-model-type`](cli-reference/model-customization.md#output-model-type) for this command.

For schema-authored names, model reuse, and generated documentation, see
[`practical-py312-20260619`](presets.md#practical-py312-20260619).

### Input

```json title="schema.json"
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Pet",
  "type": "object",
  "required": ["name"],
  "properties": {
    "name": {
      "type": "string",
      "description": "The pet's name"
    },
    "species": {
      "type": "string",
      "enum": ["dog", "cat", "bird", "fish"],
      "default": "dog"
    },
    "age": {
      "type": "integer",
      "minimum": 0,
      "description": "Age in years"
    },
    "vaccinated": {
      "type": "boolean",
      "default": false
    }
  }
}
```

### Output

```python title="model.py"
# generated by datamodel-codegen:
#   filename:  schema.json

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class Species(StrEnum):
    dog = 'dog'
    cat = 'cat'
    bird = 'bird'
    fish = 'fish'


class Pet(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    name: Annotated[str, Field(description="The pet's name")]
    species: Species = Species.dog
    age: Annotated[int | None, Field(description='Age in years', ge=0)] = None
    vaccinated: bool = False
```

🎉 That's it! Your schema is now a fully-typed Python model.
<!-- END AUTO-GENERATED PRESET QUICK START -->

---

## 📥 Choose Your Input

| Input Type | File Types | Example |
|------------|------------|---------|
| 📘 [OpenAPI 3.0/3.1/3.2](openapi.md) | `.yaml`, `.json` | API specifications |
| 📡 [AsyncAPI](asyncapi.md) | `.yaml`, `.json` | Event-driven API specifications |
| 📋 [JSON Schema](jsonschema.md) | `.json`, `.yaml` | Data validation schemas |
| 🪶 [Apache Avro](avro.md) | `.avsc`, `.json` | Avro schemas |
| 🧾 [XML Schema](xmlschema.md) | `.xsd` | XML document schemas |
| 🧩 [Protocol Buffers / gRPC](protobuf.md) | `.proto` | Protobuf messages and service schemas |
| 🔷 [GraphQL](graphql.md) | `.graphql` | GraphQL type definitions |
| 🛠️ [MCP Tool Schemas](mcp-tools.md) | `.json`, `.yaml` | MCP tool input/output schemas |
| 📊 [JSON/YAML/CSV Data](jsondata.md) | `.json`, `.yaml`, `.csv` | Infer schema from data |
| 🐍 [Python Models](python-model.md) | `.py` | Pydantic, dataclass, TypedDict |

---

## ✅ Conformance Signals

CI exercises datamodel-code-generator against pinned external corpora for XML Schema, JSON Schema, AsyncAPI, Apache
Avro, and Protocol Buffers. See the [Conformance Dashboard](conformance.md) for the generated summary of runner scripts,
tox environments, CI jobs, expected corpus counts, and upstream sources.

---

## 📤 Choose Your Output

```bash
# 🆕 Pydantic v2 (recommended for new projects)
datamodel-codegen --output-model-type pydantic_v2.BaseModel ...

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

### 🤖 Get CLI Help from LLMs

Generate a prompt to ask LLMs about CLI options:

```bash
datamodel-codegen --generate-prompt "Best options for Pydantic v2?" | claude -p
```

See [LLM Integration](llm-integration.md) for more examples.

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
```

Then simply run:

```bash
datamodel-codegen
```

See [pyproject.toml Configuration](pyproject_toml.md) for more options.

### 🔄 CI/CD Integration

Validate generated models in your CI pipeline:

```yaml title=".github/workflows/validate-models.yml"
- uses: koxudaxi/datamodel-code-generator@0.44.0
  with:
    input: schemas/api.yaml
    output: src/models/api.py
```

See [CI/CD Integration](ci-cd.md) for more options.

---

## 📚 Next Steps

- 🖥️ **[CLI Reference](cli-reference/index.md)** - All command-line options with examples
- 🧰 **[Presets](presets.md)** - Recommended immutable option bundles
- ⚙️ **[pyproject.toml Configuration](pyproject_toml.md)** - Configure via pyproject.toml
- 🚀 **[One-liner Usage](oneliner.md)** - uvx, pipx, clipboard integration
- 🔄 **[CI/CD Integration](ci-cd.md)** - GitHub Actions and CI validation
- ✅ **[Conformance Dashboard](conformance.md)** - External corpus and CI coverage signals
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
    <td valign="top" align="center">
      <a href="https://github.com/openai">
        <img src="https://avatars.githubusercontent.com/u/14957082?s=200&v=4" alt="OpenAI Logo" style="width: 100px;">
        <p>OpenAI</p>
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
- [openai/codex](https://github.com/openai/codex) - *[Python SDK dev dependency](https://github.com/openai/codex/blob/cca36c5681d16c7dac6e3f385589b8cd4d3e78cd/sdk/python/pyproject.toml#L32-L33)*
- [vllm-project/vllm](https://github.com/vllm-project/vllm) - *[Test dependency for model tests](https://github.com/vllm-project/vllm/blob/main/requirements/test.in)*
- [stanfordnlp/dspy](https://github.com/stanfordnlp/dspy) - *[Generate Pydantic models from JSON Schema for reliability tests](https://github.com/stanfordnlp/dspy/blob/main/tests/reliability/generate/utils.py)*
- [topoteretes/cognee](https://github.com/topoteretes/cognee) - *[Runtime generation of graph data models from JSON Schema](https://github.com/topoteretes/cognee/blob/main/cognee/shared/graph_model_utils.py)*
- [e2b-dev/E2B](https://github.com/e2b-dev/E2B) - *[Generate MCP server TypedDict models via Makefile](https://github.com/e2b-dev/E2B/blob/main/packages/python-sdk/Makefile)*
- [apache/airflow](https://github.com/apache/airflow) - *[Generate OpenAPI datamodels for airflow-ctl and task-sdk via pyproject codegen config](https://github.com/apache/airflow/blob/f1ac27af8b53e7d3ca7ff710c4f4413599bd1535/airflow-ctl/pyproject.toml#L148-L172)*
- [browser-use/browser-use](https://github.com/browser-use/browser-use) - *[Eval dependency](https://github.com/browser-use/browser-use/blob/de14b9aa31d167696a7ea7185d71876dbd7e6c94/pyproject.toml#L74-L79)*
- [firebase/genkit](https://github.com/firebase/genkit) - *[Generate core typing models from JSON Schema](https://github.com/firebase/genkit/blob/main/py/bin/generate_schema_typing)*
- [open-telemetry/opentelemetry-python](https://github.com/open-telemetry/opentelemetry-python) - *[Generate SDK configuration dataclasses from JSON Schema](https://github.com/open-telemetry/opentelemetry-python/blob/main/tox.ini)*
- [DataDog/integrations-core](https://github.com/DataDog/integrations-core) - *[Config models](https://github.com/DataDog/integrations-core/blob/master/docs/developer/meta/config-models.md)*
- [argoproj-labs/hera](https://github.com/argoproj-labs/hera) - *[Makefile](https://github.com/argoproj-labs/hera/blob/c8cbf0c7a676de57469ca3d6aeacde7a5e84f8b7/Makefile#L53-L62)*
- [tensorzero/tensorzero](https://github.com/tensorzero/tensorzero) - *[Generate Python dataclasses from JSON Schema in the schema generation pipeline](https://github.com/tensorzero/tensorzero/blob/26a51c8808f64cc0beaf8db4dfeea646cffbdaaa/crates/tensorzero-python/generate_schema_types.py#L1-L26)*
- [IBM/compliance-trestle](https://github.com/IBM/compliance-trestle) - *[Building models from OSCAL schemas](https://github.com/IBM/compliance-trestle/blob/develop/docs/contributing/website.md#building-the-models-from-the-oscal-schemas)*

[See all dependents →](https://github.com/koxudaxi/datamodel-code-generator/network/dependents)
