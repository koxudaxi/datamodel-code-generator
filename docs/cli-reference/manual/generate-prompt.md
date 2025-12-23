## `--generate-prompt` {#generate-prompt}

Generate a prompt for consulting LLMs about CLI options.

Outputs a formatted prompt containing your current options, all available
options by category, and full help text. Pipe to CLI LLM tools or copy
to clipboard for web-based LLM chats.

**See also:** [LLM Integration](../../llm-integration.md) for detailed usage examples

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
