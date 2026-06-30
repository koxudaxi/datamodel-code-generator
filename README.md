# datamodel-code-generator

🚀 Generate Python data models from schema definitions in seconds.

🧪 Try it in your browser: [Playground](https://datamodel-code-generator.koxudaxi.dev/playground/)

> [!NOTE]
> Playground privacy: generation runs locally in your browser with Pyodide. Schemas and options are not sent to a
> backend. Shared repro URLs encode them in the URL fragment (`#state=...`), which browsers do not send to the server;
> the full URL can still be stored in your browser history or wherever you share it.

[![PyPI version](https://img.shields.io/pypi/v/datamodel-code-generator.svg)](https://pypi.python.org/pypi/datamodel-code-generator)
[![Conda-forge](https://img.shields.io/conda/v/conda-forge/datamodel-code-generator)](https://anaconda.org/conda-forge/datamodel-code-generator)
[![Downloads](https://api.pepy.tech/badge/datamodel-code-generator/month)](https://pepy.tech/projects/datamodel-code-generator)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/datamodel-code-generator)](https://pypi.python.org/pypi/datamodel-code-generator)
[![codecov](https://codecov.io/gh/koxudaxi/datamodel-code-generator/graph/badge.svg?token=plzSSFb9Li)](https://codecov.io/gh/koxudaxi/datamodel-code-generator)
![license](https://img.shields.io/github/license/koxudaxi/datamodel-code-generator.svg)
[![Pydantic v2](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/pydantic/pydantic/main/docs/badge/v2.json)](https://pydantic.dev)

> 📣 💼 Maintainer update: Open to opportunities. 🔗 [koxudaxi.dev](https://koxudaxi.dev/?utm_source=github_readme&utm_medium=top&utm_campaign=open_to_work)

## ✨ What it does

<!-- Source of truth: docs/assets/diagrams/hero.mmd — regenerate with `tox run -e diagrams` -->
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/diagrams/hero-dark.svg">
    <img alt="Schema files, raw data, and existing Python models flow through datamodel-code-generator into Python model output types" src="docs/assets/diagrams/hero-light.svg" width="760">
  </picture>
</p>

Pick any one of the supported inputs and pick the Python model style you want as output.
`--input-model path/to/file.py:ClassName` can even retarget an existing Pydantic, dataclass, or TypedDict class defined
in another Python file to a different output type.

- 📄 Converts **OpenAPI 3**, **AsyncAPI**, **JSON Schema**, **Apache Avro**, **XML Schema**, **Protocol Buffers/gRPC**, **GraphQL**, **MCP tool schemas**, and raw data (JSON/YAML/CSV) into Python models
- 🐍 Generates from **existing Python types** (Pydantic, dataclass, TypedDict) via `--input-model`
- 🎯 Generates **Pydantic v2**, **Pydantic v2 dataclass**, **dataclasses**, **TypedDict**, or **msgspec** output
- 🔗 Handles complex schemas: `$ref`, `allOf`, `oneOf`, `anyOf`, enums, and nested types
- ✅ Produces type-safe, validated code ready for your IDE and type checker

---

## 📦 Installation

Recommended for standalone CLI use:

```bash
uv tool install datamodel-code-generator
```

For projects that should pin the generator version, add it as a development dependency instead:

```bash
uv add --dev datamodel-code-generator
```

<details>
<summary>Other installation methods</summary>

**pip:**
```bash
pip install datamodel-code-generator
```

**uv (run without adding to project):**
```bash
uv run --with datamodel-code-generator datamodel-codegen --help
```

**conda:**
```bash
conda install -c conda-forge datamodel-code-generator
```

**With HTTP support** (for resolving remote `$ref`):
```bash
pip install 'datamodel-code-generator[http]'
```

**With GraphQL support:**
```bash
pip install 'datamodel-code-generator[graphql]'
```

**With Protocol Buffers support:**
```bash
pip install 'datamodel-code-generator[protobuf]'
```

**Docker:**
```bash
docker pull koxudaxi/datamodel-code-generator
```

</details>

---

## 🏃 Quick Start

<!-- BEGIN AUTO-GENERATED PRESET QUICK START -->
**Command**

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

See [CLI Reference](https://datamodel-code-generator.koxudaxi.dev/cli-reference/) for all options. See [Presets](https://datamodel-code-generator.koxudaxi.dev/presets/),
[`--preset`](https://datamodel-code-generator.koxudaxi.dev/cli-reference/base-options/#preset), [`--input-file-type`](https://datamodel-code-generator.koxudaxi.dev/cli-reference/base-options/#input-file-type), and
[`--output-model-type`](https://datamodel-code-generator.koxudaxi.dev/cli-reference/model-customization/#output-model-type) for this command.

For more schema-aware output that preserves schema-authored names, reuses models, and embeds generated
documentation, use [`practical-py312-20260619`](https://datamodel-code-generator.koxudaxi.dev/presets/#practical-py312-20260619).

<details>
<summary>Input (<code>schema.json</code>)</summary>

```json
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

</details>

**Output (`model.py`)**

```python
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

### ⚡ Speed up generation

By default, generated Python is currently formatted with `black` and `isort`. For faster generation without external
formatter dependencies, add `--formatters builtin` for standard generated model modules. In a future version, the
Black/isort dependencies will become opt-in and the default formatter will change to `builtin`.

If you prefer Ruff, install it with `pip install 'datamodel-code-generator[ruff]'` and use
`--formatters ruff-check ruff-format` for a fast external formatter.

Custom templates can emit Python outside the standard generated model patterns covered by `builtin`, so
custom-template output is not exhaustively validated. If `--formatters builtin` produces invalid or poorly formatted
output with a custom template, please open an issue with a small reproducer. See
[Formatter Behavior](https://datamodel-code-generator.koxudaxi.dev/formatter-behavior/) for details.

See [Performance Benchmarks](https://datamodel-code-generator.koxudaxi.dev/performance-benchmarks/) for release benchmark data and interactive charts.
<!-- END AUTO-GENERATED PRESET QUICK START -->

---

## 📖 Documentation

**👉 [datamodel-code-generator.koxudaxi.dev](https://datamodel-code-generator.koxudaxi.dev)**

- 🧰 [Presets](https://datamodel-code-generator.koxudaxi.dev/presets/) - Recommended option bundles for modern output
- 🖥️ [CLI Reference](https://datamodel-code-generator.koxudaxi.dev/cli-reference/) - All command-line options
- 🧪 [Playground](https://datamodel-code-generator.koxudaxi.dev/playground/) - Try generation in your browser
- ⚙️ [pyproject.toml](https://datamodel-code-generator.koxudaxi.dev/pyproject_toml/) - Configuration file
- 🔄 [CI/CD Integration](https://datamodel-code-generator.koxudaxi.dev/ci-cd/) - GitHub Actions, pre-commit hooks
- ✅ [Conformance Dashboard](https://datamodel-code-generator.koxudaxi.dev/conformance/) - External corpus coverage signals
- 📈 [Performance Benchmarks](https://datamodel-code-generator.koxudaxi.dev/performance-benchmarks/) - Release benchmark tables and interactive charts
- 🧭 [Architecture](https://datamodel-code-generator.koxudaxi.dev/architecture/) - Generation pipeline and synchronized component inventory
- 🚀 [One-liner Usage](https://datamodel-code-generator.koxudaxi.dev/oneliner/) - uvx, pipx, clipboard integration
- ❓ [FAQ](https://datamodel-code-generator.koxudaxi.dev/faq/) - Common questions

---

## 📥 Supported Input

- OpenAPI 3 (YAML/JSON)
- AsyncAPI (YAML/JSON)
- JSON Schema
- Apache Avro schema (AVSC)
- XML Schema (XSD)
- Protocol Buffers / gRPC (`.proto`)
- MCP tool schemas
- JSON / YAML / CSV data
- GraphQL schema
- Python types (Pydantic, dataclass, TypedDict) via `--input-model`
- Python dictionary

## 📤 Supported Output

- [pydantic v2](https://docs.pydantic.dev/) BaseModel
- [pydantic v2](https://docs.pydantic.dev/) dataclass
- [dataclasses](https://docs.python.org/3/library/dataclasses.html)
- [TypedDict](https://docs.python.org/3/library/typing.html#typing.TypedDict)
- [msgspec](https://github.com/jcrist/msgspec) Struct

## ✅ Conformance Signals

CI exercises datamodel-code-generator against pinned external corpora for XML Schema, JSON Schema, AsyncAPI, Apache
Avro, and Protocol Buffers. See the [Conformance Dashboard](https://datamodel-code-generator.koxudaxi.dev/conformance/)
for the generated summary of runner scripts, tox environments, CI jobs, expected corpus counts, and upstream sources.

---

## 🍳 Common Recipes

### 🤖 Get CLI Help from LLMs

Generate a prompt to ask LLMs about CLI options:

```bash
datamodel-codegen --generate-prompt "Best options for Pydantic v2?" | claude -p
```

See [LLM Integration](https://datamodel-code-generator.koxudaxi.dev/llm-integration/) for more examples.

### 🌐 Generate from URL

```bash
pip install 'datamodel-code-generator[http]'
datamodel-codegen --url https://example.com/api/openapi.yaml --output model.py
```

### ⚙️ Use with pyproject.toml

```toml
[tool.datamodel-codegen]
input = "schema.yaml"
output = "src/models.py"
output-model-type = "pydantic_v2.BaseModel"
```

Then simply run:

```bash
datamodel-codegen
```

See [pyproject.toml Configuration](https://datamodel-code-generator.koxudaxi.dev/pyproject_toml/) for more options.

### 🔄 CI/CD Integration

Validate generated models in your CI pipeline:

```yaml
- uses: koxudaxi/datamodel-code-generator@0.44.0
  with:
    input: schemas/api.yaml
    output: src/models/api.py
```

See [CI/CD Integration](https://datamodel-code-generator.koxudaxi.dev/ci-cd/) for more options.

---

## Coding agent skill

This repository includes an experimental Agent Skill that teaches compatible coding agents to run `datamodel-codegen` when generating Python models from OpenAPI, AsyncAPI, JSON Schema, GraphQL, JSON/YAML/CSV sample data, MCP tool schemas, Protocol Buffers, XML Schema, Apache Avro, or existing Python model objects.

See [Coding Agent Skill](docs/coding-agent-skill.md) for detailed guidance and troubleshooting.

Install the directory for your agent:

```bash
# Codex, project-local
mkdir -p .agents/skills
cp -R skills/datamodel-code-generator .agents/skills/datamodel-code-generator

# Claude Code, project-local
mkdir -p .claude/skills
cp -R skills/datamodel-code-generator .claude/skills/datamodel-code-generator
```

For a personal install, copy the same directory to `$HOME/.agents/skills/datamodel-code-generator/` for Codex or `~/.claude/skills/datamodel-code-generator/` for Claude Code.

Check your agent's current documentation for exact search paths.

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

## 🏢 Projects that use datamodel-code-generator

These projects use datamodel-code-generator. See the linked examples for real-world usage.

- [openai/codex](https://github.com/openai/codex) - *[Python SDK dev dependency](https://github.com/openai/codex/blob/cca36c5681d16c7dac6e3f385589b8cd4d3e78cd/sdk/python/pyproject.toml#L32-L33)*
- [browser-use/browser-use](https://github.com/browser-use/browser-use) - *[Eval dependency](https://github.com/browser-use/browser-use/blob/de14b9aa31d167696a7ea7185d71876dbd7e6c94/pyproject.toml#L74-L79)*
- [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk) - *[Generate MCP protocol models from vendored JSON Schemas](https://github.com/modelcontextprotocol/python-sdk/blob/main/scripts/gen_surface_types.py)*
- [vllm-project/vllm](https://github.com/vllm-project/vllm) - *[Test dependency for model tests](https://github.com/vllm-project/vllm/blob/main/requirements/test.in)*
- [modular/modular](https://github.com/modular/modular) - *[Generate MAX Serve KServe schemas from OpenAPI with datamodel-codegen](https://github.com/modular/modular/blob/0735fa29762a5c53d65a0456d0b53eac1472180f/max/python/max/serve/schemas/README.md#L20-L33)*
- [apache/airflow](https://github.com/apache/airflow) - *[Generate OpenAPI datamodels for airflow-ctl and task-sdk via pyproject codegen config](https://github.com/apache/airflow/blob/f1ac27af8b53e7d3ca7ff710c4f4413599bd1535/airflow-ctl/pyproject.toml#L148-L172)*
- [stanfordnlp/dspy](https://github.com/stanfordnlp/dspy) - *[Generate Pydantic models from JSON Schema for reliability tests](https://github.com/stanfordnlp/dspy/blob/main/tests/reliability/generate/utils.py)*
- [PostHog/posthog](https://github.com/PostHog/posthog) - *[Generate models via npm run](https://github.com/PostHog/posthog/blob/e1a55b9cb38d01225224bebf8f0c1e28faa22399/package.json#L41)*
- [airbytehq/airbyte](https://github.com/airbytehq/airbyte) - *[Generate Python, Java/Kotlin, and Typescript protocol models](https://github.com/airbytehq/airbyte-protocol/tree/main/protocol-models/bin)*
- [apache/iceberg](https://github.com/apache/iceberg) - *[Generate Python code](https://github.com/apache/iceberg/blob/d2e1094ee0cc6239d43f63ba5114272f59d605d2/open-api/README.md?plain=1#L39)*
- [open-metadata/OpenMetadata](https://github.com/open-metadata/OpenMetadata) - *[datamodel_generation.py](https://github.com/open-metadata/OpenMetadata/blob/main/scripts/datamodel_generation.py)*
- [topoteretes/cognee](https://github.com/topoteretes/cognee) - *[Runtime generation of graph data models from JSON Schema](https://github.com/topoteretes/cognee/blob/main/cognee/shared/graph_model_utils.py)*
- [e2b-dev/E2B](https://github.com/e2b-dev/E2B) - *[Generate MCP server TypedDict models via Makefile](https://github.com/e2b-dev/E2B/blob/main/packages/python-sdk/Makefile)*
- [firebase/genkit](https://github.com/firebase/genkit) - *[Generate core typing models from JSON Schema](https://github.com/firebase/genkit/blob/main/py/bin/generate_schema_typing)*
- [DataDog/integrations-core](https://github.com/DataDog/integrations-core) - *[Config models](https://github.com/DataDog/integrations-core/blob/master/docs/developer/meta/config-models.md)*
- [open-telemetry/opentelemetry-python](https://github.com/open-telemetry/opentelemetry-python) - *[Generate SDK configuration dataclasses from JSON Schema](https://github.com/open-telemetry/opentelemetry-python/blob/main/tox.ini)*

[See all dependents →](https://github.com/koxudaxi/datamodel-code-generator/network/dependents)

---

## 🔗 Related Projects

- **[fastapi-code-generator](https://github.com/koxudaxi/fastapi-code-generator)** - Generate FastAPI app from OpenAPI
- **[pydantic-pycharm-plugin](https://github.com/koxudaxi/pydantic-pycharm-plugin)** - PyCharm plugin for Pydantic

---

## 🤝 Contributing

See [Development & Contributing](https://datamodel-code-generator.koxudaxi.dev/development-contributing/) for how to get started!

---

## 👤 Maintainer

[Koudai Aono](https://koxudaxi.dev/?utm_source=github_readme&utm_medium=maintainer_section&utm_campaign=open_to_work) ([@koxudaxi](https://github.com/koxudaxi))

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.
