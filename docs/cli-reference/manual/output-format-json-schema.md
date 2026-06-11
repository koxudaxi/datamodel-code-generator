## `--output-format-json-schema` {#output-format-json-schema}

Output JSON Schema for a structured command output format and exit.

Use this when an LLM agent, tool call definition, or validation layer needs the
contract before consuming JSON output. The schema is emitted separately from the
JSON payload so tools can fetch the contract once and validate later command
output independently.

Currently supported schema targets:

- `generate-prompt`: schema for `--generate-prompt --output-format json`

!!! tip "Usage"

    ```bash
    datamodel-codegen --output-format-json-schema generate-prompt # (1)!
    datamodel-codegen --generate-prompt --output-format json # (2)!
    ```

    1. :material-arrow-left: Emit the JSON Schema for structured prompt output
    2. :material-arrow-left: Emit payloads that match that schema
