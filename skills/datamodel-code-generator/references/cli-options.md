# CLI options cheat sheet

This is a curated guide. The source of truth is `datamodel-codegen --help` and the official CLI reference.

## Input and fetching

- `--input`: Read a local input file or directory.
- `--input-file-type`: Set the input type when auto detection is ambiguous or wrong.
- `--input-model`: Generate from an existing Python model or schema object.
- `--input-model-ref-strategy`: Control whether referenced Python types are regenerated or reused.
- `--url`: Read input from a remote URL.
- `--http-headers`: Add HTTP headers for remote input.
- `--http-query-parameters`: Add query parameters for remote input.
- `--http-timeout`: Set the timeout for remote HTTP requests.
- `--http-local-ref-path`: Resolve HTTP refs from a local directory.
- `--allow-remote-refs`: Opt in to fetching remote refs.
- `--external-ref-mapping`: Map external refs to Python packages instead of regenerating classes.
- `--encoding`: Set input and output encoding.

## Output model type

- `--output`: Write generated code to a file or package directory.
- `--output-model-type`: Choose Pydantic v2, Pydantic dataclass, dataclass, TypedDict, or msgspec output.
- `--target-pydantic-version`: Choose the generated Pydantic v2 compatibility target.

## Python version and typing syntax

- `--target-python-version`: Set the minimum Python version for generated type syntax. Use the project's declared Python version.
- `--use-union-operator`: Use `|` union syntax when supported.
- `--use-standard-collections`: Use built-in `list` and `dict` style collections.
- `--use-annotated`: Use `typing.Annotated` for field metadata.
- `--use-generic-container-types`: Use generic container abstractions such as `Sequence` and `Mapping`.
- `--disable-future-imports`: Omit `from __future__ import annotations`.

## Names and aliases

- `--class-name`: Set the root class name.
- `--use-title-as-name`: Use schema titles as generated class names.
- `--snake-case-field`: Convert field names to snake case.
- `--no-alias`: Do not add aliases for changed field names.
- `--special-field-name-prefix`: Prefix invalid Python field names.
- `--remove-special-field-name-prefix`: Remove special prefixes when possible.
- `--capitalise-enum-members`: Capitalize enum member names.

## Optionality and validation behavior

- `--strict-nullable`: Treat defaulted fields as non-nullable.
- `--field-constraints`: Generate field constraints rather than constrained types.
- `--force-optional`: Force required fields to be optional.
- `--use-default`: Use default values even when a field is required.
- `--strip-default-none`: Remove explicit `None` defaults.
- `--union-mode`: Set Pydantic v2 union behavior.

## OpenAPI behavior

- `--openapi-scopes`: Choose which OpenAPI sections to generate from.
- `--include-path-parameters`: Include path parameters in generated parameter models.
- `--use-operation-id-as-name`: Use OpenAPI operation IDs as model names.
- `--use-status-code-in-response-name`: Include HTTP status codes in response model names.
- `--read-only-write-only-model-type`: Generate request and response variants for readOnly or writeOnly fields.

## Reuse and module structure

- `--reuse-model`: Reuse identical generated models.
- `--reuse-scope`: Set whether reuse is per module or across a tree.
- `--shared-module-name`: Set the shared module name for tree reuse.
- `--collapse-root-models`: Merge root models into referencing models.
- `--all-exports-scope`: Generate package exports.
- `--all-exports-collision-strategy`: Resolve recursive export name collisions.
- `--treat-dot-as-module`: Treat dotted schema names as module paths.

## Formatting and reproducibility

- `--formatters`: Choose output formatters.
- `--custom-formatters`: Run custom formatter modules.
- `--disable-timestamp`: Remove timestamp headers.
- `--enable-version-header`: Include the package version in headers.
- `--enable-command-header`: Include the generation command in headers.
- `--check`: Verify generated files are up to date without modifying them.
