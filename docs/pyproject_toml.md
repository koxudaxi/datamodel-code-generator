<!-- related-cli-options: --ignore-pyproject, --generate-pyproject-config, --generate-cli-command, --profile -->

# ⚙️ pyproject.toml Configuration

datamodel-code-generator can be configured using `pyproject.toml`. The tool automatically searches for `pyproject.toml` in the current directory and parent directories (stopping at the git repository root).

## 🚀 Basic Usage

```toml
[tool.datamodel-codegen]
input = "schema.yaml"
output = "models.py"
target-python-version = "3.11"
snake-case-field = true
field-constraints = true
```

All CLI options can be used in `pyproject.toml` by converting them to kebab-case (e.g., `--snake-case-field` becomes `snake-case-field`).

## 📋 Named Profiles

You can define multiple named profiles for different use cases within a single project:

```toml
[tool.datamodel-codegen]
target-python-version = "3.10"
snake-case-field = true

[tool.datamodel-codegen.profiles.api]
input = "schemas/api.yaml"
output = "src/models/api.py"
target-python-version = "3.11"

[tool.datamodel-codegen.profiles.database]
input = "schemas/db.json"
output = "src/models/db.py"
input-file-type = "jsonschema"
```

Base settings in `[tool.datamodel-codegen]` are used when no profile is specified, and also serve as defaults for profiles.

Use a profile with the `--profile` option:

```bash
datamodel-codegen --profile api
datamodel-codegen --profile database
```

## 🎯 Configuration Priority

Settings are applied in the following priority order (highest to lowest):

1. **🖥️ CLI arguments** - Always take precedence
2. **📋 Profile settings** - From `[tool.datamodel-codegen.profiles.<name>]`
3. **⚙️ Base settings** - From `[tool.datamodel-codegen]`
4. **🔧 Default values** - Built-in defaults

## 🔀 Merge Rules

When using profiles, settings are merged using **shallow merge**:

- Profile values **completely replace** base values (no deep merging)
- Settings not specified in the profile are inherited from the base configuration
- Lists and dictionaries are replaced entirely, not merged

### 📝 Example

```toml
[tool.datamodel-codegen]
strict-types = ["str", "int"]
http-headers = ["Authorization: Bearer token"]

[tool.datamodel-codegen.profiles.api]
strict-types = ["bytes"]
```

When using `--profile api`:

- `strict-types` becomes `["bytes"]` (completely replaces base, not merged)
- `http-headers` is inherited from base as `["Authorization: Bearer token"]`

## 🚫 Ignoring pyproject.toml

To ignore all `pyproject.toml` configuration and use only CLI arguments:

```bash
datamodel-codegen --ignore-pyproject --input schema.yaml --output models.py
```

## 🔧 Generating Configuration

Generate a `pyproject.toml` configuration section from CLI arguments:

```bash
datamodel-codegen --input schema.yaml --output models.py --snake-case-field --generate-pyproject-config
```

**✨ Output:**

```toml
[tool.datamodel-codegen]
input = "schema.yaml"
output = "models.py"
snake-case-field = true
```

Generate CLI command from existing `pyproject.toml`:

```bash
datamodel-codegen --generate-cli-command
```

With a specific profile:

```bash
datamodel-codegen --profile api --generate-cli-command
```

---

## 📖 See Also

- 🖥️ [CLI Reference: `--ignore-pyproject`](cli-reference/general-options.md#ignore-pyproject) - Ignore pyproject.toml configuration
- 🔧 [CLI Reference: `--generate-pyproject-config`](cli-reference/general-options.md#generate-pyproject-config) - Generate pyproject.toml from CLI arguments
- 🖥️ [CLI Reference: `--generate-cli-command`](cli-reference/general-options.md#generate-cli-command) - Generate CLI command from pyproject.toml
