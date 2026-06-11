## `--output-format-json-schema` {#output-format-json-schema}

Output JSON Schema for a structured command output format and exit.

Use this when an LLM agent, tool call definition, or validation layer needs the
contract before consuming JSON output. The schema is emitted separately from the
JSON payload so tools can fetch the contract once and validate later command
output independently.

Currently supported schema targets:

- `generate-prompt`: schema for `--generate-prompt --output-format json`
- `generation`: schema for normal generation with `--output-format json`
- `structured-output`: tagged union schema for all structured command outputs,
  discriminated by `kind`

!!! tip "Usage"

    ```bash
    datamodel-codegen --output-format-json-schema generate-prompt # (1)!
    datamodel-codegen --output-format-json-schema generation # (2)!
    datamodel-codegen --output-format-json-schema structured-output # (3)!
    datamodel-codegen --generate-prompt --output-format json # (4)!
    datamodel-codegen --input schema.json --output-format json # (5)!
    ```

    1. :material-arrow-left: Emit the JSON Schema for structured prompt output
    2. :material-arrow-left: Emit the JSON Schema for generated-file output
    3. :material-arrow-left: Emit the JSON Schema for all structured command outputs
    4. :material-arrow-left: Emit prompt payloads that match the prompt schema
    5. :material-arrow-left: Emit generation payloads that match the generation schema
