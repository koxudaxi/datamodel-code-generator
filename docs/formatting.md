<!-- related-cli-options: --formatters -->

# 🖌️ Code Formatting

Generated code is automatically formatted using code formatters. By default, `black` and `isort` are used to produce consistent, well-formatted output.

## 🎯 Default Behavior

!!! warning "Future Change"
    In a future version, the default formatters will change from `black` and `isort` to `ruff`.
    To prepare for this change, consider switching to ruff now using `--formatters ruff-format ruff-check`.

    **CLI users**: To suppress this warning, use `--disable-warnings` or explicitly specify `--formatters black isort`.

    **Library users**: Explicitly pass `formatters=[Formatter.BLACK, Formatter.ISORT]` to suppress this warning.

```bash
datamodel-codegen --input schema.yaml --output model.py
```

This runs the following formatters in order:

1. **isort** - Sorts and organizes imports
2. **black** - Formats code style

## 🛠️ Available Formatters

| Formatter | Description |
|-----------|-------------|
| `black` | Code formatting (PEP 8 style) |
| `isort` | Import sorting |
| `ruff-check` | Linting with auto-fix |
| `ruff-format` | Fast code formatting (black alternative) |

### ⚡ Using ruff instead of black

[Ruff](https://github.com/astral-sh/ruff) is a fast Python linter and formatter. To use it:

!!! note "Installation Required"
    ruff is an optional dependency. Install it with:
    ```bash
    pip install 'datamodel-code-generator[ruff]'
    ```

```bash
# Use ruff for both linting and formatting
datamodel-codegen --formatters ruff-check ruff-format --input schema.yaml --output model.py

# Use ruff-format as a black replacement
datamodel-codegen --formatters isort ruff-format --input schema.yaml --output model.py
```

### 🚫 Disable formatting

`datamodel-codegen` requires at least one formatter when using the CLI `--formatters` option.

To disable built-in formatting entirely, configure it via `pyproject.toml`:

```toml title="pyproject.toml"
[tool.datamodel-codegen]
formatters = []
```

## ⚙️ Configuration via pyproject.toml

Formatters read their configuration from `pyproject.toml`. The tool searches for `pyproject.toml` in:

1. The output file's directory
2. Parent directories (up to the git repository root)

### 📝 Example Configuration

```toml title="pyproject.toml"
[tool.black]
line-length = 100
skip-string-normalization = true

[tool.isort]
profile = "black"
line_length = 100

[tool.ruff]
line-length = 100

[tool.ruff.format]
quote-style = "single"
```

## 💬 String Quotes

By default, string quote style is determined by your formatter configuration. To force double quotes regardless of configuration:

```bash
datamodel-codegen --use-double-quotes --input schema.yaml --output model.py
```

This overrides `skip_string_normalization` in black config.

## 🎨 Custom Formatters

You can create custom formatters for specialized formatting needs. See [Custom Formatters](custom-formatters.md) for details.

---

## 📖 See Also

- 🖥️ [CLI Reference: `--formatters`](cli-reference/template-customization.md#formatters) - Specify code formatters
- 💬 [CLI Reference: `--use-double-quotes`](cli-reference/template-customization.md#use-double-quotes) - Force double quotes
- 🎨 [Custom Formatters](custom-formatters.md) - Create your own formatters
- ⚙️ [pyproject.toml Configuration](pyproject_toml.md) - Configure datamodel-codegen options
