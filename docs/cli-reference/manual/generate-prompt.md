## `--generate-prompt` {#generate-prompt}

Generate a prompt for consulting LLMs about CLI options.

Outputs a formatted prompt containing your current options, all available
options by category, and full help text. Pipe to CLI LLM tools or copy
to clipboard for web-based LLM chats.

**See also:** [LLM Integration](../../llm-integration.md) for detailed usage examples

!!! note "For LLM agents"

    Inspect the user's goal and schema, then run
    `datamodel-codegen [known options] --generate-prompt "<goal>"` before
    choosing options. Preserve current options unless they conflict, and return
    the final command, reasons for non-obvious options, rejected alternatives,
    and a verification command.

!!! tip "Usage"

    ```bash
    datamodel-codegen --generate-prompt # (1)!
    datamodel-codegen --generate-prompt "How do I generate strict types?" # (2)!
    ```

    1. :material-arrow-left: `--generate-prompt` - generate prompt without a question
    2. :material-arrow-left: Include a specific question in the prompt

??? example "Quick Examples"

    **Pipe to CLI tools:**
    ```bash
    datamodel-codegen --generate-prompt | claude -p    # Claude Code
    datamodel-codegen --generate-prompt | codex exec   # OpenAI Codex
    ```

    **Copy to clipboard:**
    ```bash
    datamodel-codegen --generate-prompt | pbcopy      # macOS
    datamodel-codegen --generate-prompt | xclip -selection clipboard  # Linux
    datamodel-codegen --generate-prompt | clip.exe    # WSL2
    ```

    **Ask about an existing OpenAPI command:**
    ```bash
    datamodel-codegen \
        --input openapi.yaml \
        --input-file-type openapi \
        --output models.py \
        --output-model-type pydantic_v2.BaseModel \
        --target-python-version 3.12 \
        --generate-prompt "Find the minimal options for strict API response models." \
        | claude -p
    ```

    **Review a command with current options:**
    ```bash
    datamodel-codegen \
        --input schema.json \
        --output models.py \
        --output-model-type pydantic_v2.BaseModel \
        --generate-prompt "Review this command for stable generated output in CI."
    ```
