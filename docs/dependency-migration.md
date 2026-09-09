# Dependency migration notices

This release prepares later changes. Black and isort remain the default formatters and required dependencies;
all current dependency ranges, compatibility code and minimum-version tests remain in place. Generation still
continues when formatters are omitted. The built-in formatter remains experimental.

## Choose formatting independently of the default

- Use `--formatters ruff-check ruff-format` when your project uses Ruff and generated code should follow its lint
  and formatting settings. Install `datamodel-code-generator[ruff]` when needed.
- Use `--formatters builtin` when you use no external formatter or prioritize generation speed and avoiding
  external formatter execution.
- Keep `--formatters black isort` to preserve your existing Black/isort policy and generated formatting.

The future builtin default is intended to reduce mandatory installation dependencies and version constraints.
It does not change the recommendation to use Ruff in projects standardized on Ruff. Packages and Ruff configuration
never trigger automatic formatter selection.

Configure the formatter once in `pyproject.toml` to avoid repeating CLI options:

```toml
[tool.datamodel-codegen]
formatters = ["ruff-check", "ruff-format"]
```

The new `standard-py310-20260909` through `standard-py314-20260909` and corresponding `practical` presets include
builtin. Presets also change other generation settings, so explicitly selecting only a formatter is the smallest
migration when you want to preserve those settings. Override a new preset with
`--formatters ruff-check ruff-format` or `--formatters black isort` as appropriate. Earlier dated presets do not
supply a formatter and continue to use the implicit Black/isort default and its warning unless overridden.
An explicit empty formatter list in pyproject or the Python API disables standard formatting.

Explicit formatter selection does not pin formatter versions, configuration or every byte of generated output.
Custom templates can continue using Black/isort or Ruff; builtin does not exhaustively validate custom-template
output. See [Formatter behavior](formatter-behavior.md) for scope and configuration details.

## Separate notices

| Notice | When it is emitted |
| --- | --- |
| Default formatter change | Effective formatters are unspecified, including older presets and custom formatters added to the implicit pipeline. |
| Black/isort optional installation | Black or isort is explicitly selected, including through resolved configuration or a formatter-supplying preset. Not also emitted for an implicit pipeline. |

Each notice is registered separately as an active `FutureWarning`. The default formatter notice retains its
original 0.52.0 history; the new notices are recorded for the planned 0.78.0 release. The registry contains the
[exact short messages](deprecations.md). Migration warnings are deduplicated within one CLI invocation, including
batch and watch regeneration. Non-generation operations such as help, version and listings do not emit them or
load dependency modules just to check versions. The Python API respects standard warning filters, including
`always`, `ignore` and `error`; the CLI continues to support `--disable-warnings`. Warnings do not enter stdout or
generated code.

## Prepare for optional Black/isort installation

The new `[black]` and `[isort]` extras currently repeat the mandatory dependency ranges and Emscripten markers;
`[all]` includes them. They prepare a stable installation spelling for the later optionalization. You do not need
to reinstall these currently mandatory dependencies merely because of this release.

For continued Black/isort use after the future default and installation changes, select both the dependencies and
formatter pipeline:

```bash
uvx --from 'datamodel-code-generator[black,isort]' \
  datamodel-codegen --input schema.json --output models.py \
  --formatters black isort
```

For a Python API or shared environment, declare `datamodel-code-generator[black,isort]` in your environment's
dependencies and pass `formatters=[Formatter.BLACK, Formatter.ISORT]`. Declare only the extras you actually use.
`uvx` can isolate the CLI's dependencies from application dependencies. Shared environments and API use remain
supported migration scenarios; application constraints alone do not imply a fixed long transition period.

