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
