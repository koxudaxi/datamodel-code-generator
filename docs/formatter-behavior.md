<!-- related-cli-options: --formatters -->

# Formatter behavior

`datamodel-codegen` formats generated Python code after model generation. The default formatter list is currently `black` and `isort`.

This default will change in a future release. External formatters will become opt-in so that generated output can be produced without installing formatter packages.

## Formatter selection

Use `--formatters` to select the formatter pipeline.

```bash
datamodel-codegen \
    --input schema.yaml \
    --output model.py \
    --formatters builtin
```

Available formatter names are:

| Name | Behavior |
| ---- | -------- |
| `builtin` | Internal formatter for generated model modules. No external package is required. |
| `black` | Runs Black against generated code. |
| `isort` | Runs isort against generated imports. |
| `ruff-check` | Runs `ruff check --fix`. |
| `ruff-format` | Runs `ruff format`. |

Formatters run in the order passed to `--formatters`.

## Built-in formatter scope

The built-in formatter is intentionally small. It is not a general Python formatter and is not expected to produce byte-for-byte identical output to the latest Black, isort, or Ruff for arbitrary Python files.

It covers the generated-code patterns that matter for model modules:

- Removes trailing whitespace and writes a final newline.
- Parses the module with `ast`.
- Sorts only the leading import block. It stops at the first non-import statement.
- Splits `import a, b` into separate `import` lines.
- Groups imports in this order: `__future__`, standard library, third-party, relative imports.
- Sorts `from ... import ...` names and merges imports from the same module.
- Wraps long `from ... import ...` statements with parentheses when they exceed the configured line length.
- Keeps two blank lines before a top-level `class`, `def`, or `async def` after the import block.

If the generated code cannot be parsed as Python, the built-in formatter only applies whitespace cleanup and returns the code.

The built-in formatter does not currently format:

- Expressions inside classes or functions.
- `Field(...)`, `Annotated[...]`, list, dict, tuple, or call argument layout.
- Quote style.
- String wrapping.
- Comments.
- Import section rules beyond the simple groups listed above.

For exact Black, isort, or Ruff behavior, continue to pass those formatters explicitly.

## Line length

The built-in formatter uses line length only for wrapping `from ... import ...` statements.

Set it in `pyproject.toml`:

```toml
[tool.datamodel-codegen]
formatters = ["builtin"]
builtin-format-line-length = 100
```

When `builtin-format-line-length` is not set, the built-in formatter reuses existing formatter configuration in this order:

1. `[tool.ruff].line-length`
2. `[tool.black].line-length`
3. `[tool.isort].line_length`
4. `88`

This fallback only reads configuration values. It does not require Ruff, Black, or isort to be installed.

An explicit API value always wins over `pyproject.toml`.

## API usage

Library users can pass the same setting through `generate()` or `GenerateConfig`.

```python
from pathlib import Path

from datamodel_code_generator import generate
from datamodel_code_generator.format import Formatter

generate(
    input_=Path("schema.yaml"),
    output=Path("model.py"),
    formatters=[Formatter.BUILTIN],
    builtin_format_line_length=100,
)
```

## Migration notes

To keep current output behavior, set the external formatters explicitly:

```bash
datamodel-codegen \
    --input schema.yaml \
    --output model.py \
    --formatters black isort
```

To test the dependency-free path, use:

```bash
datamodel-codegen \
    --input schema.yaml \
    --output model.py \
    --formatters builtin
```

Generated output may differ from Black or isort output in places outside the built-in formatter scope. Treat those differences as expected unless they change Python semantics or produce invalid code.
