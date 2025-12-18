# One-liner Usage

This guide covers how to use datamodel-code-generator with pipes and clipboard tools for quick, one-time code generation without permanent installation.

!!! note
    The package name is `datamodel-code-generator`, and the CLI command is `datamodel-codegen`.

---

## One-liner Execution with uvx/pipx

You don't need to install datamodel-code-generator permanently. Use `uvx` or `pipx run` to execute it directly.

### Using uvx (Recommended)

[uvx](https://docs.astral.sh/uv/guides/tools/) runs Python tools without installation:

```bash
# Basic usage
uvx datamodel-codegen --input schema.json --output model.py

# With extras (e.g., HTTP support)
uvx --from 'datamodel-code-generator[http]' datamodel-codegen --url https://example.com/api.yaml --output model.py

# With GraphQL support
uvx --from 'datamodel-code-generator[graphql]' datamodel-codegen --input schema.graphql --output model.py
```

### Using pipx run

[pipx](https://pipx.pypa.io/) also supports one-shot execution:

```bash
pipx run datamodel-code-generator --input schema.json --output model.py
```

---

## Reading from stdin

datamodel-code-generator can read schema input from stdin, enabling powerful pipeline workflows:

```bash
# Pipe JSON directly
echo '{"type": "object", "properties": {"name": {"type": "string"}}}' | \
  uvx datamodel-codegen --input-file-type jsonschema

# Pipe from another command
curl -s https://example.com/schema.json | \
  uvx datamodel-codegen --input-file-type jsonschema --output model.py
```

---

## Clipboard Integration

Combine stdin support with clipboard tools to quickly generate models from copied schema definitions.

### macOS (pbpaste/pbcopy)

```bash
# Generate from clipboard and print to stdout
pbpaste | uvx datamodel-codegen --input-file-type jsonschema

# Generate from clipboard and save to file
pbpaste | uvx datamodel-codegen --input-file-type jsonschema --output model.py

# Generate from clipboard and copy result back to clipboard
pbpaste | uvx datamodel-codegen --input-file-type jsonschema | pbcopy
```

### Linux (xclip/xsel)

=== "xclip"

    ```bash
    # Generate from clipboard and print to stdout
    xclip -selection clipboard -o | uvx datamodel-codegen --input-file-type jsonschema

    # Generate and copy result to clipboard
    xclip -selection clipboard -o | uvx datamodel-codegen --input-file-type jsonschema | xclip -selection clipboard
    ```

=== "xsel"

    ```bash
    # Generate from clipboard and print to stdout
    xsel --clipboard --output | uvx datamodel-codegen --input-file-type jsonschema

    # Generate and copy result to clipboard
    xsel --clipboard --output | uvx datamodel-codegen --input-file-type jsonschema | xsel --clipboard --input
    ```

!!! tip "Installing clipboard tools on Linux"
    ```bash
    # Debian/Ubuntu
    sudo apt install xclip
    # or
    sudo apt install xsel

    # Fedora
    sudo dnf install xclip
    # or
    sudo dnf install xsel
    ```

### Windows (clip/PowerShell)

=== "PowerShell"

    ```powershell
    # Generate from clipboard and print to stdout
    Get-Clipboard | uvx datamodel-codegen --input-file-type jsonschema

    # Generate and copy result to clipboard
    Get-Clipboard | uvx datamodel-codegen --input-file-type jsonschema | Set-Clipboard
    ```

=== "Command Prompt"

    ```batch
    REM Windows Command Prompt doesn't have a built-in paste command
    REM Use PowerShell from cmd:
    powershell -command "Get-Clipboard" | uvx datamodel-codegen --input-file-type jsonschema
    ```

!!! note "Windows clip command"
    The `clip` command on Windows only supports copying **to** the clipboard, not reading from it. Use PowerShell's `Get-Clipboard` and `Set-Clipboard` for full clipboard integration.

---

## Practical Examples

### Quick model generation workflow

1. Copy a JSON Schema from documentation or an API response
2. Run the generator from clipboard:

```bash
# macOS
pbpaste | uvx datamodel-codegen --input-file-type jsonschema --output-model-type pydantic_v2.BaseModel

# Linux
xclip -selection clipboard -o | uvx datamodel-codegen --input-file-type jsonschema --output-model-type pydantic_v2.BaseModel

# Windows PowerShell
Get-Clipboard | uvx datamodel-codegen --input-file-type jsonschema --output-model-type pydantic_v2.BaseModel
```

### Generating from API documentation

```bash
# Fetch OpenAPI spec and generate models
curl -s https://petstore3.swagger.io/api/v3/openapi.json | \
  uvx datamodel-codegen --input-file-type openapi --output-model-type pydantic_v2.BaseModel --output petstore.py
```

### Generating from GitHub raw URLs

You can directly fetch schemas from GitHub repositories using raw URLs:

```bash
# Fetch JSON Schema from GitHub and generate models
curl -s https://raw.githubusercontent.com/OAI/OpenAPI-Specification/main/schemas/v3.0/schema.json | \
  uvx datamodel-codegen --input-file-type jsonschema --output-model-type pydantic_v2.BaseModel

# Fetch OpenAPI spec from a GitHub repository
curl -s https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.json | \
  uvx datamodel-codegen --input-file-type openapi --output-model-type pydantic_v2.BaseModel --output github_api.py
```

!!! tip "Using the --url option"
    If you have the `http` extra installed, you can use `--url` directly without curl:

    ```bash
    uvx --from 'datamodel-code-generator[http]' datamodel-codegen \
      --url https://raw.githubusercontent.com/OAI/OpenAPI-Specification/main/schemas/v3.0/schema.json \
      --input-file-type jsonschema \
      --output-model-type pydantic_v2.BaseModel
    ```

### Using with jq for JSON manipulation

```bash
# Extract a specific schema definition and generate a model
cat openapi.yaml | yq '.components.schemas.User' | \
  uvx datamodel-codegen --input-file-type jsonschema
```

---

## Comparison: Installation Methods

| Method | Command | Use Case |
|--------|---------|----------|
| **uvx** | `uvx datamodel-codegen` | One-liner usage, no installation |
| **pipx run** | `pipx run datamodel-code-generator` | One-liner usage, alternative to uvx |
| **pipx install** | `pipx install datamodel-code-generator` | Global installation, frequent usage |
| **uv add** | `uv add datamodel-code-generator` | Project dependency |
| **pip install** | `pip install datamodel-code-generator` | Traditional installation |

!!! tip "When to use each method"
    - **uvx/pipx run**: Quick one-liner generation, testing different versions
    - **pipx install**: Frequent CLI usage across multiple projects
    - **uv add/pip install**: Project dependency, CI/CD pipelines, programmatic usage
