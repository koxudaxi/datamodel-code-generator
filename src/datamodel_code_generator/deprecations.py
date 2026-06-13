"""Central registry for deprecated and scheduled-breaking behavior."""

from __future__ import annotations

import warnings
from dataclasses import asdict, dataclass
from typing import Literal

from datamodel_code_generator._registry_render import _render_registry_json, _render_registry_table

DeprecationKind = Literal["cli-option", "python-api", "config", "behavior", "schema"]
DeprecationStatus = Literal["active", "scheduled"]
DeprecationFormat = Literal["table", "json", "markdown"]
DeprecationId = Literal[
    "behavior.pydantic-v2-use-annotated-default",
    "behavior.remote-ref-default",
    "cli.allow-extra-fields",
    "cli.parent-scoped-naming",
    "cli.validation",
    "config.yaml-non-lowercase-bool",
    "format.default-formatters",
    "python-api.python-version-has-type-alias",
    "schema.jsonschema-items-array",
    "schema.openapi-nullable",
]


@dataclass(frozen=True)
class Deprecation:
    """Structured metadata for a deprecation entry."""

    id: DeprecationId
    kind: DeprecationKind
    target: str
    message: str
    warning_since: str
    removal_version: str | None
    replacement: str | None = None
    status: DeprecationStatus = "active"
    warning_category: str = "DeprecationWarning"
    note: str | None = None


DEPRECATIONS: dict[DeprecationId, Deprecation] = {
    "cli.allow-extra-fields": Deprecation(
        id="cli.allow-extra-fields",
        kind="cli-option",
        target="--allow-extra-fields",
        message="--allow-extra-fields is deprecated. Use --extra-fields=allow instead.",
        warning_since="0.31.0",
        removal_version=None,
        replacement="--extra-fields=allow",
        note="The replacement supports allow, forbid, and ignore modes.",
    ),
    "cli.parent-scoped-naming": Deprecation(
        id="cli.parent-scoped-naming",
        kind="cli-option",
        target="--parent-scoped-naming",
        message="--parent-scoped-naming is deprecated. Use --naming-strategy parent-prefixed instead.",
        warning_since="0.48.0",
        removal_version=None,
        replacement="--naming-strategy parent-prefixed",
    ),
    "cli.validation": Deprecation(
        id="cli.validation",
        kind="cli-option",
        target="--validation",
        message=(
            "The `--validation` option is deprecated and will be removed in a future release. "
            "Use --field-constraints instead."
        ),
        warning_since="0.24.0",
        removal_version=None,
        replacement="--field-constraints",
    ),
    "behavior.pydantic-v2-use-annotated-default": Deprecation(
        id="behavior.pydantic-v2-use-annotated-default",
        kind="behavior",
        target="Pydantic v2 default for --use-annotated",
        message=(
            "Pydantic v2 with --use-annotated is recommended for correct type annotations. "
            "In a future version, --use-annotated will be enabled by default for Pydantic v2."
        ),
        warning_since="0.52.1",
        removal_version=None,
        replacement="Explicitly pass --use-annotated or --no-use-annotated.",
    ),
    "behavior.remote-ref-default": Deprecation(
        id="behavior.remote-ref-default",
        kind="behavior",
        target="Remote $ref fetching without --allow-remote-refs",
        message="Remote $ref fetching without --allow-remote-refs is deprecated.",
        warning_since="0.56.0",
        removal_version=None,
        replacement=(
            "Pass --allow-remote-refs for trusted remote schemas, or --no-allow-remote-refs to block HTTP(S) "
            "$ref fetching."
        ),
        warning_category="FutureWarning",
        note=(
            "The current default allows remote fetching for compatibility; the scheduled default is disabled. "
            "Private, loopback, link-local, and otherwise non-public network targets require --allow-private-network."
        ),
    ),
    "format.default-formatters": Deprecation(
        id="format.default-formatters",
        kind="behavior",
        target="Default formatters",
        message="The default external formatters (black, isort) will become opt-in in a future version.",
        warning_since="0.52.0",
        removal_version=None,
        replacement="Set formatters explicitly, for example black and isort or builtin.",
        warning_category="FutureWarning",
    ),
    "config.yaml-non-lowercase-bool": Deprecation(
        id="config.yaml-non-lowercase-bool",
        kind="config",
        target="YAML bool values True, False, TRUE, FALSE",
        message="Non-lowercase YAML bool values are deprecated. Use lowercase true or false instead.",
        warning_since="0.48.0",
        removal_version=None,
        replacement="Use lowercase true or false.",
    ),
    "python-api.python-version-has-type-alias": Deprecation(
        id="python-api.python-version-has-type-alias",
        kind="python-api",
        target="PythonVersion.has_type_alias",
        message="has_type_alias is deprecated and will be removed in a future version.",
        warning_since="0.52.1",
        removal_version=None,
        replacement=None,
        note="The project minimum Python version already supports TypeAlias.",
    ),
    "schema.openapi-nullable": Deprecation(
        id="schema.openapi-nullable",
        kind="schema",
        target="OpenAPI 3.1 nullable keyword",
        message='nullable keyword is deprecated in OpenAPI 3.1, use type: ["string", "null"] instead.',
        warning_since="0.53.0",
        removal_version=None,
        replacement='Use type arrays such as type: ["string", "null"].',
    ),
    "schema.jsonschema-items-array": Deprecation(
        id="schema.jsonschema-items-array",
        kind="schema",
        target="JSON Schema Draft 2020-12 items array tuple validation",
        message="items as array tuple validation is deprecated in Draft 2020-12. Use prefixItems instead.",
        warning_since="0.53.0",
        removal_version=None,
        replacement="Use prefixItems.",
        warning_category="UserWarning",
    ),
}

_WARNING_CATEGORIES: dict[str, type[Warning]] = {
    "DeprecationWarning": DeprecationWarning,
    "FutureWarning": FutureWarning,
    "UserWarning": UserWarning,
}


def iter_deprecations() -> tuple[Deprecation, ...]:
    """Return all deprecations in stable display order."""
    return tuple(sorted(DEPRECATIONS.values(), key=lambda item: (item.removal_version or "", item.kind, item.target)))


def get_deprecation(deprecation_id: DeprecationId) -> Deprecation:
    """Return a registered deprecation by id."""
    return DEPRECATIONS[deprecation_id]


def warn_deprecated(deprecation_id: DeprecationId, *, stacklevel: int = 2, details: str | None = None) -> None:
    """Emit a warning from the central registry."""
    deprecation = get_deprecation(deprecation_id)
    message = deprecation.message if details is None else f"{deprecation.message} {details}"
    warnings.warn(
        message,
        _WARNING_CATEGORIES[deprecation.warning_category],
        stacklevel=stacklevel,
    )


def deprecation_message(deprecation_id: DeprecationId) -> str:
    """Return the user-facing message for a deprecation."""
    return get_deprecation(deprecation_id).message


def _format_removal_version(deprecation: Deprecation) -> str:
    """Return the display value for a removal version."""
    return deprecation.removal_version or "TBD"


def deprecation_as_dict(deprecation: Deprecation) -> dict[str, str | None]:
    """Serialize a deprecation entry to primitive values."""
    return asdict(deprecation)


def render_deprecations_json() -> str:
    """Render all deprecations as JSON."""
    return _render_registry_json(deprecation_as_dict(deprecation) for deprecation in iter_deprecations())


def render_deprecations_table() -> str:
    """Render all deprecations as a plain text table."""
    return _render_registry_table([
        [
            "ID",
            "Kind",
            "Target",
            "Warning since",
            "Removal",
            "Replacement",
        ],
        *[
            [
                deprecation.id,
                deprecation.kind,
                deprecation.target,
                deprecation.warning_since,
                _format_removal_version(deprecation),
                deprecation.replacement or "-",
            ]
            for deprecation in iter_deprecations()
        ],
    ])


def render_deprecations_markdown(*, include_header: bool = True) -> str:
    """Render all deprecations as Markdown."""
    lines: list[str] = []
    if include_header:
        lines.extend([
            "# Deprecations",
            "",
            "<!-- Generated by scripts/build_deprecation_docs.py. Do not edit manually. -->",
            "",
            "This page lists deprecations and scheduled breaking changes.",
            "",
        ])
    lines.extend([
        "| ID | Kind | Target | Warning since | Removal | Replacement |",
        "|----|------|--------|---------------|---------|-------------|",
    ])
    for deprecation in iter_deprecations():
        replacement = deprecation.replacement or "-"
        lines.append(
            f"| `{deprecation.id}` | {deprecation.kind} | `{deprecation.target}` | "
            f"{deprecation.warning_since} | {_format_removal_version(deprecation)} | {replacement} |"
        )
    lines.extend(("", "## Details", ""))
    for deprecation in iter_deprecations():
        lines.extend([
            f"### `{deprecation.id}`",
            "",
            f"- **Kind:** {deprecation.kind}",
            f"- **Target:** `{deprecation.target}`",
            f"- **Warning since:** {deprecation.warning_since}",
            f"- **Planned removal:** {_format_removal_version(deprecation)}",
            f"- **Warning category:** `{deprecation.warning_category}`",
        ])
        if deprecation.replacement:
            lines.append(f"- **Replacement:** {deprecation.replacement}")
        lines.extend([
            "",
            deprecation.message,
            "",
        ])
        if deprecation.note:
            lines.extend([deprecation.note, ""])
    return "\n".join(lines).rstrip() + "\n"


def render_deprecations(format_: DeprecationFormat) -> str:
    """Render deprecations in the requested format."""
    if format_ == "json":
        return render_deprecations_json() + "\n"
    if format_ == "markdown":
        return render_deprecations_markdown()
    return render_deprecations_table()


def render_release_note_deprecations(version: str) -> str:
    """Render release-note text for deprecations that start or end in a version."""
    warning_started = [item for item in iter_deprecations() if item.warning_since == version]
    removals = [item for item in iter_deprecations() if item.removal_version == version]

    lines: list[str] = []
    if warning_started:
        lines.extend(["## Deprecations", ""])
        lines.extend(
            f"- `{item.target}` now emits `{item.warning_category}`. Planned removal: {_format_removal_version(item)}. "
            f"{item.message}"
            for item in warning_started
        )
        lines.append("")

    if removals:
        lines.extend(["## Removed Deprecated Features", ""])
        lines.extend(f"- `{item.target}` was scheduled for removal in {version}. {item.message}" for item in removals)
        lines.append("")

    return "\n".join(lines)
