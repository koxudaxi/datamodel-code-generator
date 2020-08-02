datamodel-code-generator has a lot of command-line options.

The options are supported on `pyproject.toml`.

Example `pyproject.toml`:
```toml 
[tool.datamodel-codegen]
field-constraints = true
snake-case-field = true
strip-default-none = false
target-python-version = "3.7"
```
