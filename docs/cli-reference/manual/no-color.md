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
