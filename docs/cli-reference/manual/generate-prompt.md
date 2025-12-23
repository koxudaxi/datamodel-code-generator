## `--generate-prompt` {#generate-prompt}

Generate a prompt for consulting LLMs about CLI options.

The `--generate-prompt` flag outputs a formatted prompt containing:

- Current CLI options you've specified
- Options organized by category with descriptions
- Full help text for reference

This prompt can be piped to CLI-based LLM tools or copied to clipboard
for use with web-based LLM chat services.

!!! tip "Usage"

    ```bash
    datamodel-codegen --generate-prompt # (1)!
    datamodel-codegen --generate-prompt "How do I generate strict types?" # (2)!
    ```

    1. :material-arrow-left: `--generate-prompt` - generate prompt without a question
    2. :material-arrow-left: Include a specific question in the prompt

!!! info "Piping to CLI LLM Tools"

    Pipe the generated prompt directly to CLI-based LLM tools:

    ```bash
    # Claude Code (Anthropic)
    datamodel-codegen --generate-prompt "Best options for Pydantic v2?" | claude

    # Codex (OpenAI)
    datamodel-codegen --generate-prompt | codex

    # llm (Simon Willison's LLM CLI)
    datamodel-codegen --generate-prompt | llm

    # aichat
    datamodel-codegen --generate-prompt | aichat

    # ShellGPT
    datamodel-codegen --generate-prompt | sgpt

    # Charmbracelet mods
    datamodel-codegen --generate-prompt | mods
    ```

!!! info "Copying to Clipboard"

    Copy the prompt to clipboard for use with web-based LLM chats:

    **macOS:**
    ```bash
    datamodel-codegen --generate-prompt | pbcopy
    ```

    **Linux (X11):**
    ```bash
    datamodel-codegen --generate-prompt | xclip -selection clipboard
    ```

    **Linux (Wayland):**
    ```bash
    datamodel-codegen --generate-prompt | wl-copy
    ```

    **Windows (PowerShell):**
    ```powershell
    datamodel-codegen --generate-prompt | Set-Clipboard
    ```

    **WSL2:**
    ```bash
    datamodel-codegen --generate-prompt | clip.exe
    ```

    After copying, paste into your preferred web LLM chat service
    (e.g., ChatGPT, Claude, Gemini, Perplexity, etc.).

??? example "Example Output"

    ```text
    # datamodel-code-generator CLI Options Consultation

    ## User Question

    How do I generate strict types?

    ## Current CLI Options

    (No options specified)

    ## Options by Category

    ### Base Options
    - `--input`: Specify the input schema file path.
    - `--output`: Specify the destination path for generated Python code.
    ...

    ### Typing Customization
    - `--strict-types`: Enable strict type validation for specified Python types.
    ...

    ## Instructions

    Based on the above information, please help with the question or suggest
    appropriate CLI options for the use case.
    ```
