# 📝 Utility Options

## 📋 Options

| Option | Description |
|--------|-------------|
| [`--debug`](#debug) | Show debug messages during code generation |
| [`--generate-prompt`](#generate-prompt) | Generate a prompt for consulting LLMs about CLI options |
| [`--help`](#help) | Show help message and exit |
| [`--no-color`](#no-color) | Disable colorized output |
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

**See also:** [LLM Integration](../llm-integration.md) for detailed usage examples

!!! tip "Usage"

    ```bash
    datamodel-codegen --generate-prompt # (1)!
    datamodel-codegen --generate-prompt "How do I generate strict types?" # (2)!
    ```

    1. :material-arrow-left: `--generate-prompt` - generate prompt without a question
    2. :material-arrow-left: Include a specific question in the prompt

??? example "Quick Examples"

    **Pipe to CLI tools:**
    ```bash
    datamodel-codegen --generate-prompt | claude -p    # Claude Code
    datamodel-codegen --generate-prompt | codex exec   # OpenAI Codex
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

    [tool.datamodel-codegen.profiles.legacy]
    # Legacy profile for Pydantic v1
    output-model-type = "pydantic.BaseModel"
    ```

    Use profiles:

    ```bash
    # Use the strict profile
    datamodel-codegen --input schema.json --profile strict

    # Use the legacy profile
    datamodel-codegen --input schema.json --profile legacy
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

