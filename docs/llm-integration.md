# LLM Integration

<!-- related-cli-options: --generate-prompt -->

The `--generate-prompt` option generates a formatted prompt that you can use
to consult Large Language Models (LLMs) about datamodel-code-generator CLI options.

## Overview

When you're unsure which CLI options to use for your specific use case,
you can generate a prompt containing all available options and their descriptions,
then ask an LLM for recommendations.

```bash
datamodel-codegen --generate-prompt "How do I generate strict Pydantic v2 models?"
```

The generated prompt includes:

- Your question (if provided)
- Current CLI options you've specified
- All options organized by category with descriptions
- Full help text for reference

## CLI LLM Tools

Pipe the generated prompt directly to CLI-based LLM tools:

### Claude Code (Anthropic)

```bash
datamodel-codegen --generate-prompt "Best options for API response models?" | claude
```

### Codex (OpenAI)

```bash
datamodel-codegen --generate-prompt "How to handle nullable fields?" | codex
```

### llm (Simon Willison's LLM CLI)

```bash
datamodel-codegen --generate-prompt | llm
```

### aichat

```bash
datamodel-codegen --generate-prompt | aichat
```

### ShellGPT (sgpt)

```bash
datamodel-codegen --generate-prompt | sgpt
```

### Charmbracelet mods

```bash
datamodel-codegen --generate-prompt | mods
```

## Web LLM Chat Services

Copy the prompt to clipboard, then paste into your preferred web-based LLM chat:

### macOS

```bash
datamodel-codegen --generate-prompt | pbcopy
```

### Linux (X11)

```bash
datamodel-codegen --generate-prompt | xclip -selection clipboard
```

### Linux (Wayland)

```bash
datamodel-codegen --generate-prompt | wl-copy
```

### Windows (PowerShell)

```powershell
datamodel-codegen --generate-prompt | Set-Clipboard
```

### WSL2

```bash
datamodel-codegen --generate-prompt | clip.exe
```

After copying, paste into:

- **ChatGPT** - chat.openai.com
- **Claude** - claude.ai
- **Gemini** - gemini.google.com
- **Perplexity** - perplexity.ai
- **Copilot** - copilot.microsoft.com
- And other LLM chat services

## Usage Examples

### Basic Usage

Generate a prompt without a specific question:

```bash
datamodel-codegen --generate-prompt
```

### With a Question

Include your specific question in the prompt:

```bash
datamodel-codegen --generate-prompt "What options should I use for GraphQL schema?"
```

### With Current Options

Show your current configuration and ask for improvements:

```bash
datamodel-codegen \
    --input schema.json \
    --output-model-type pydantic_v2.BaseModel \
    --use-annotated \
    --generate-prompt "Are there any other options I should consider?"
```

### Pipe to Claude with Options

```bash
datamodel-codegen \
    --input openapi.yaml \
    --output-model-type dataclasses.dataclass \
    --generate-prompt "How can I add JSON serialization support?" \
    | claude
```

## Tips

1. **Be specific** - Include a clear question to get more relevant recommendations
2. **Show context** - Add your current options so the LLM understands your setup
3. **Iterate** - Use the suggestions, then ask follow-up questions if needed
