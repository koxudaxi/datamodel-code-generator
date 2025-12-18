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
