## `--format` {#format}

Choose the output format for `--generate-prompt`.

The option is only valid together with `--generate-prompt`. The default output
is Markdown. Use `json` when another program or LLM agent should inspect
structured option metadata.

!!! tip "Usage"

    ```bash
    datamodel-codegen --generate-prompt --format markdown # (1)!
    datamodel-codegen --generate-prompt --format json # (2)!
    ```

    1. :material-arrow-left: Emit the default Markdown consultation prompt
    2. :material-arrow-left: Emit structured JSON with current options and argparse metadata

??? example "JSON output"

    ```bash
    datamodel-codegen \
        --input schema.json \
        --output-model-type pydantic_v2.BaseModel \
        --generate-prompt "Choose strict model options." \
        --format json
    ```
