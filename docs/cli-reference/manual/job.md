## `--job` {#job}

Run one or more named generation jobs declared in `pyproject.toml`. Jobs are
executed sequentially in TOML declaration order, even when `--job` is supplied
in a different order.

**Related:** [pyproject.toml Configuration](../../pyproject_toml.md), [`--all-jobs`](#all-jobs)

!!! tip "Usage"

    ```bash
    datamodel-codegen --job api
    datamodel-codegen --job api --job events --check
    ```

??? example "Configuration (pyproject.toml)"

    ```toml
    [tool.datamodel-codegen.profiles.strict]
    use-annotated = true

    [tool.datamodel-codegen.jobs.api]
    profile = "strict"
    input = "schemas/openapi.yaml"
    output = "src/models/api.py"

    [tool.datamodel-codegen.jobs.events]
    input = "schemas/events.json"
    output = "src/models/events.py"
    ```

Jobs require their own `input` and `output`. A job can select one reusable
profile using `profile = "name"`. Settings are resolved as base configuration,
job profile, job settings, then safe batch-wide CLI overrides. `--input`,
`--url`, `--input-model`, `--output`, `--profile`, and `--watch` cannot be
combined with job selection. The forthcoming batch watch mode will rerun the
entire selected batch for a dependency change; it does not use partial job
rebuilds.
