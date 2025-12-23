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

### Claude Code

[Claude Code](https://docs.anthropic.com/en/docs/claude-code) is Anthropic's official CLI tool.
Use `-p` flag for non-interactive (pipe) mode:

```bash
datamodel-codegen --generate-prompt "Best options for API response models?" | claude -p
```

### OpenAI Codex CLI

[Codex CLI](https://github.com/openai/codex) is OpenAI's CLI tool.
Use `exec` subcommand for non-interactive mode:

```bash
datamodel-codegen --generate-prompt "How to handle nullable fields?" | codex exec
```

### Other CLI Tools

Other popular LLM CLI tools that accept stdin:

| Tool | Command | Repository |
|------|---------|------------|
| llm | `\| llm` | [simonw/llm](https://github.com/simonw/llm) |
| aichat | `\| aichat` | [sigoden/aichat](https://github.com/sigoden/aichat) |
| sgpt | `\| sgpt` | [TheR1D/shell_gpt](https://github.com/TheR1D/shell_gpt) |
| mods | `\| mods` | [charmbracelet/mods](https://github.com/charmbracelet/mods) |

Check each tool's documentation for specific usage and options.

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
    | claude -p
```

## Tips

1. **Be specific** - Include a clear question to get more relevant recommendations
2. **Show context** - Add your current options so the LLM understands your setup
3. **Iterate** - Use the suggestions, then ask follow-up questions if needed
