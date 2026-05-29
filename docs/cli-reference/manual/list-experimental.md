## `--list-experimental` {#list-experimental}

List registered experimental features, then exit.

The optional format argument can be `table`, `json`, or `markdown`. The default is `table`.

The option reads from the central experimental feature registry used by
generated documentation and release-note snippets.

    datamodel-codegen --list-experimental
    datamodel-codegen --list-experimental json
    datamodel-codegen --list-experimental markdown
