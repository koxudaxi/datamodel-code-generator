# Using datamodel-code-generator with coding agents

This repository includes an experimental Agent Skill for skills-compatible coding agents. The skill teaches an agent to run `datamodel-codegen` when a user asks for Python models from OpenAPI, AsyncAPI, JSON Schema, GraphQL, JSON/YAML/CSV sample data, MCP tool schemas, Protocol Buffers, XML Schema, Apache Avro, or existing Python model objects.

The skill is a directory, not a package-manager install. The required entrypoint is `SKILL.md`, and supporting files live under `references/`.

Treat this skill as experimental. The workflow, trigger wording, and client-specific install guidance can change as Codex, Claude Code, and other skills-compatible agents evolve.

## Why agents should run the CLI

Agents should run `datamodel-codegen` instead of hand-writing generated models when a usable input artifact exists.

The CLI handles refs, enums, nested models, unions, `allOf`, `oneOf`, `anyOf`, and model reuse. It also produces output that can be imported and checked after generation.

## Install for Claude Code

Claude Code project skills load from `.claude/skills/` in the starting directory and parent directories up to the repository root. Personal skills can be placed under `~/.claude/skills/`.

For a project skill, run:

```bash
mkdir -p .claude/skills
cp -R skills/datamodel-code-generator .claude/skills/datamodel-code-generator
```

For a personal skill, run:

```bash
mkdir -p ~/.claude/skills
cp -R skills/datamodel-code-generator ~/.claude/skills/datamodel-code-generator
```

Claude Code can invoke a skill directly with `/datamodel-code-generator`, or load it automatically when the description matches the task. Existing top-level skill directories are watched for changes. If the top-level skills directory did not exist when the session started, restart Claude Code.

## Install for Codex

Codex reads project skills from `.agents/skills` in the current directory, parent directories, and the repository root. It reads personal skills from `$HOME/.agents/skills`.

For a project skill, run:

```bash
mkdir -p .agents/skills
cp -R skills/datamodel-code-generator .agents/skills/datamodel-code-generator
```

For a personal skill, run:

```bash
mkdir -p ~/.agents/skills
cp -R skills/datamodel-code-generator ~/.agents/skills/datamodel-code-generator
```

Codex can invoke skills explicitly through `/skills` or `$` mention, or load them automatically when the description matches the task.

## Other agents

Other skills-compatible agents may support this directory format. Check the client documentation for its skill search path.

## Distribution paths

| Form | Install method | Best use |
| --- | --- | --- |
| Repository skill | Copy to `.agents/skills/` or `.claude/skills/` | OSS and internal repositories |
| Personal skill | Copy to `~/.agents/skills/` or `~/.claude/skills/` | Reuse across a user's projects |
| Codex local install | Use `$skill-installer` when appropriate | Codex local experiments |
| Codex plugin | Package separately as a plugin | Reusable Codex distribution |
| Claude plugin | Package separately as a plugin | Bundle skills with hooks, MCP, or agents |

Start with the repository skill. Consider Codex or Claude plugin packaging only as a separate distribution task.

## Example prompt

```text
Create Pydantic v2 models from openapi.yaml.
```

Expected agent behavior:

1. Runs `datamodel-codegen`.
2. Writes the generated file.
3. Imports the generated file.
4. Summarizes generated classes.

## Troubleshooting

- The CLI command is `datamodel-codegen`.
- The package name is `datamodel-code-generator`.
- Use extras for HTTP, GraphQL, msgspec, and protobuf when needed.
- If a JSON or YAML file is a schema, choose `openapi`, `asyncapi`, or `jsonschema` input type instead of raw sample data mode.

## References

- [Agent Skills specification](https://agentskills.io/specification)
- [Codex Agent Skills](https://developers.openai.com/codex/skills)
- [Claude Code skills](https://docs.anthropic.com/en/docs/claude-code/skills)
