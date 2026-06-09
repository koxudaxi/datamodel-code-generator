## `--output-format` {#output-format}

Choose the command output format.

The default output format is `text`. Use `json` when another program or LLM
agent should inspect structured output.

JSON output is currently supported for `--generate-prompt`. In normal generation
mode, `--output-format text` preserves the existing generated-code output.

!!! tip "Usage"

    ```bash
    datamodel-codegen --generate-prompt --output-format text # (1)!
    datamodel-codegen --generate-prompt --output-format json # (2)!
    ```

    1. :material-arrow-left: Emit the default text consultation prompt
    2. :material-arrow-left: Emit structured JSON with current options and argparse metadata

??? example "JSON output"

    ```bash
    datamodel-codegen \
        --input schema.json \
        --output-model-type pydantic_v2.BaseModel \
        --generate-prompt "Choose strict model options." \
        --output-format json
    ```
