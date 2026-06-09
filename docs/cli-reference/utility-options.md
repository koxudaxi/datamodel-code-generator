# 📝 Utility Options

## 📋 Options

| Option | Description |
|--------|-------------|
| [`--debug`](#debug) | Show debug messages during code generation |
| [`--generate-prompt`](#generate-prompt) | Generate a prompt for consulting LLMs about CLI options |
| [`--help`](#help) | Show help message and exit |
| [`--list-deprecations`](#list-deprecations) | List registered deprecations and scheduled breaking changes |
| [`--list-experimental`](#list-experimental) | List registered experimental features |
| [`--no-color`](#no-color) | Disable colorized output |
| [`--output-format`](#output-format) | Choose the command output format |
| [`--output-format-json-schema`](#output-format-json-schema) | Output JSON Schema for structured command output |
| [`--profile`](#profile) | Use a named profile from pyproject.toml |
| [`--version`](#version) | Show program version and exit |

---

## `--debug` {#debug}

Show debug messages during code generation.

Enables verbose debug output to help troubleshoot issues with schema parsing
or code generation. Requires the `debug` extra to be installed.

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --debug # (1)!
    ```

    1. :material-arrow-left: `--debug` - the option documented here

!!! warning "Requires extra dependency"

    The debug feature requires the `debug` extra:

    ```bash
    pip install 'datamodel-code-generator[debug]'
    ```

---

## `--generate-prompt` {#generate-prompt}

Generate a prompt for consulting LLMs about CLI options.

Outputs a formatted prompt containing your current options, all available
options by category, and full help text. Pipe to CLI LLM tools or copy
to clipboard for web-based LLM chats.

Use `--output-format json` when an LLM agent or tool should consume structured
option metadata instead of Markdown.
Use `--output-format-json-schema generate-prompt` when the agent needs the JSON
Schema for that structured payload, such as when defining a tool contract.

**See also:** [LLM Integration](../llm-integration.md) for detailed usage examples

!!! tip "Usage"

    ```bash
    datamodel-codegen --generate-prompt # (1)!
    datamodel-codegen --generate-prompt "How do I generate strict types?" # (2)!
    datamodel-codegen --generate-prompt --output-format json # (3)!
    datamodel-codegen --output-format-json-schema generate-prompt # (4)!
    ```

    1. :material-arrow-left: `--generate-prompt` - generate prompt without a question
    2. :material-arrow-left: Include a specific question in the prompt
    3. :material-arrow-left: Emit structured JSON for LLM/tool ingestion
    4. :material-arrow-left: Emit JSON Schema for structured prompt JSON

??? example "Quick Examples"

    **Pipe to CLI tools:**
    ```bash
    datamodel-codegen --generate-prompt | claude -p    # Claude Code
    datamodel-codegen --generate-prompt | codex exec   # OpenAI Codex
    datamodel-codegen --generate-prompt --output-format json | codex exec
    ```

    **Copy to clipboard:**
    ```bash
    datamodel-codegen --generate-prompt | pbcopy      # macOS
    datamodel-codegen --generate-prompt | xclip -selection clipboard  # Linux
    datamodel-codegen --generate-prompt | clip.exe    # WSL2
    ```

---

## `--help` {#help}

Show help message and exit.

Displays all available command-line options with their descriptions and default values.

**Aliases:** `-h`

!!! tip "Usage"

    ```bash
    datamodel-codegen --help # (1)!
    ```

    1. :material-arrow-left: `--help` - the option documented here

??? example "Output"

    ```text
    usage: datamodel-codegen [-h] [--input INPUT] [--url URL] ...

    Generate Python data models from schema files.

    options:
      -h, --help            show this help message and exit
      --input INPUT         Input file path (default: stdin)
      ...
    ```

---

## `--list-deprecations` {#list-deprecations}

List registered deprecations and scheduled breaking changes, then exit.

The option reads from the central deprecation registry used by runtime warnings,
generated documentation, and release-note snippets.

    datamodel-codegen --list-deprecations
    datamodel-codegen --list-deprecations json
    datamodel-codegen --list-deprecations markdown

---

## `--list-experimental` {#list-experimental}

List registered experimental features, then exit.

The optional format argument can be `table`, `json`, or `markdown`. The default is `table`.

The option reads from the central experimental feature registry used by
generated documentation and release-note snippets.

    datamodel-codegen --list-experimental
    datamodel-codegen --list-experimental json
    datamodel-codegen --list-experimental markdown

---

## `--no-color` {#no-color}

Disable colorized output.

By default, datamodel-codegen uses colored output for better readability.
Use this option to disable colors, which is useful for CI/CD pipelines
or when redirecting output to files.

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --no-color # (1)!
    ```

    1. :material-arrow-left: `--no-color` - the option documented here

!!! note "Environment variable"

    You can also disable colors by setting the `NO_COLOR` environment variable:

    ```bash
    NO_COLOR=1 datamodel-codegen --input schema.json
    ```

---

## `--output-format` {#output-format}

Choose the command output format.

The default output format is `text`. Use `json` when another program or LLM
agent should inspect structured output.

In normal generation mode, `--output-format json` wraps generated modules in a
structured payload on stdout. If `--output` is also supplied, files are still
written to disk and the JSON payload mirrors the generated files. `--check` and
`--watch` keep their existing text output contracts and do not support
`--output-format json`.

Use `--output-format json` with `--generate-prompt` to emit structured option
metadata instead of Markdown. Use `--output-format-json-schema` when an LLM
agent or tool needs the schema for a structured output payload.

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --output-format text # (1)!
    datamodel-codegen --input schema.json --output-format json # (2)!
    datamodel-codegen --generate-prompt --output-format json # (3)!
    datamodel-codegen --output-format-json-schema generation # (4)!
    datamodel-codegen --output-format-json-schema generate-prompt # (5)!
    ```

    1. :material-arrow-left: Emit the default generated Python text
    2. :material-arrow-left: Emit structured JSON containing generated files
    3. :material-arrow-left: Emit structured JSON with current options and argparse metadata
    4. :material-arrow-left: Emit JSON Schema for generated-file JSON output
    5. :material-arrow-left: Emit JSON Schema for structured prompt JSON

??? example "Generation JSON output"

    ```json
    {
      "version": 1,
      "format": "json",
      "files": [
        {
          "path": null,
          "content": "# generated by datamodel-codegen:\n..."
        }
      ]
    }
    ```

??? example "Prompt JSON output"

    ```bash
    datamodel-codegen \
        --input schema.json \
        --output-model-type pydantic_v2.BaseModel \
        --generate-prompt "Choose strict model options." \
        --output-format json
    ```

---

## `--output-format-json-schema` {#output-format-json-schema}

Output JSON Schema for a structured command output format and exit.

Use this when an LLM agent, tool call definition, or validation layer needs the
contract before consuming JSON output. The schema is emitted separately from the
JSON payload so tools can fetch the contract once and validate later command
output independently.

Currently supported schema targets:

- `generate-prompt`: schema for `--generate-prompt --output-format json`
- `generation`: schema for normal generation with `--output-format json`

!!! tip "Usage"

    ```bash
    datamodel-codegen --output-format-json-schema generate-prompt # (1)!
    datamodel-codegen --output-format-json-schema generation # (2)!
    datamodel-codegen --generate-prompt --output-format json # (3)!
    datamodel-codegen --input schema.json --output-format json # (4)!
    ```

    1. :material-arrow-left: Emit the JSON Schema for structured prompt output
    2. :material-arrow-left: Emit the JSON Schema for generated-file output
    3. :material-arrow-left: Emit prompt payloads that match the prompt schema
    4. :material-arrow-left: Emit generation payloads that match the generation schema

---

## `--profile` {#profile}

Use a named profile from pyproject.toml configuration.

Profiles allow you to define multiple named configurations in your pyproject.toml
file. Each profile can override the default settings with its own set of options.

**Related:** [pyproject.toml Configuration](../pyproject_toml.md)

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --profile strict # (1)!
    ```

    1. :material-arrow-left: `--profile` - the option documented here

??? example "Configuration (pyproject.toml)"

    ```toml
    [tool.datamodel-codegen]
    # Default configuration
    output-model-type = "pydantic_v2.BaseModel"

    [tool.datamodel-codegen.profiles.strict]
    # Strict profile with additional options
    strict-types = ["str", "int", "float", "bool"]
    strict-nullable = true

    [tool.datamodel-codegen.profiles.dataclass]
    # Dataclass profile
    output-model-type = "dataclasses.dataclass"
    ```

    Use profiles:

    ```bash
    # Use the strict profile
    datamodel-codegen --input schema.json --profile strict

    # Use the dataclass profile
    datamodel-codegen --input schema.json --profile dataclass
    ```

---

## `--version` {#version}

Show program version and exit.

Displays the installed version of datamodel-code-generator.

!!! tip "Usage"

    ```bash
    datamodel-codegen --version # (1)!
    ```

    1. :material-arrow-left: `--version` - the option documented here

??? example "Output"

    ```text
    datamodel-codegen version: 0.x.x
    ```

---
