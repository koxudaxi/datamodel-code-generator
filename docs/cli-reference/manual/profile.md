## `--profile` {#profile}

Use a named profile from pyproject.toml configuration.

Profiles allow you to define multiple named configurations in your pyproject.toml
file. Each profile can override the default settings with its own set of options.

**Related:** [pyproject.toml Configuration](../../pyproject_toml.md)

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
