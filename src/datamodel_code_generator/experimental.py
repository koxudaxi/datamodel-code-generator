"""Central registry for experimental features."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from datamodel_code_generator._registry_render import _render_registry_json, _render_registry_table

ExperimentalFeatureKind = Literal["input-format", "formatter", "cli-option", "python-api", "behavior"]
ExperimentalFeatureFormat = Literal["table", "json", "markdown"]
ExperimentalFeatureId = Literal[
    "input-format.asyncapi",
    "input-format.avro",
    "input-format.mcp-tools",
    "input-format.protobuf",
    "input-format.xmlschema",
    "formatter.builtin",
]


@dataclass(frozen=True)
class ExperimentalFeature:
    """Structured metadata for an experimental feature entry."""

    id: ExperimentalFeatureId
    kind: ExperimentalFeatureKind
    target: str
    message: str
    since_version: str
    tracking_issue: str | None = None
    note: str | None = None


EXPERIMENTAL_FEATURES: dict[ExperimentalFeatureId, ExperimentalFeature] = {
    "input-format.asyncapi": ExperimentalFeature(
        id="input-format.asyncapi",
        kind="input-format",
        target="--input-file-type asyncapi",
        message="AsyncAPI input support is experimental and may change as real-world usage is validated.",
        since_version="0.59.0",
        note="The parser focuses on message payload model generation from AsyncAPI documents.",
    ),
    "input-format.avro": ExperimentalFeature(
        id="input-format.avro",
        kind="input-format",
        target="--input-file-type avro",
        message="Apache Avro schema input support is experimental and may change as real-world usage is validated.",
        since_version="0.59.0",
        note="The parser generates Python models from Avro schemas; it does not provide Avro runtime validation.",
    ),
    "input-format.mcp-tools": ExperimentalFeature(
        id="input-format.mcp-tools",
        kind="input-format",
        target="--input-file-type mcp-tools",
        message="MCP tool schema profile input support is experimental and may change as MCP schemas evolve.",
        since_version="0.60.0",
        note=(
            "The input is converted from MCP tool inputSchema/outputSchema entries into JSON Schema definitions before "
            "model generation."
        ),
    ),
    "input-format.protobuf": ExperimentalFeature(
        id="input-format.protobuf",
        kind="input-format",
        target="--input-file-type protobuf",
        message="Protocol Buffers input support is experimental and may change as real-world usage is validated.",
        since_version="0.59.0",
        note=(
            "The parser generates Python models from .proto schemas; it does not provide protobuf runtime validation "
            "or gRPC code generation."
        ),
    ),
    "input-format.xmlschema": ExperimentalFeature(
        id="input-format.xmlschema",
        kind="input-format",
        target="--input-file-type xmlschema",
        message="XML Schema input support is experimental and may change as real-world usage is validated.",
        since_version="0.59.0",
        note="The parser focuses on model generation from XSD documents, not full XML instance validation.",
    ),
    "formatter.builtin": ExperimentalFeature(
        id="formatter.builtin",
        kind="formatter",
        target="--formatters builtin",
        message="The internal formatter is experimental and may change as generated-output coverage is expanded.",
        since_version="0.59.0",
        note="The formatter is designed for generated model modules and is not a general-purpose Python formatter.",
    ),
}


def iter_experimental_features() -> tuple[ExperimentalFeature, ...]:
    """Return all experimental features in stable display order."""
    return tuple(sorted(EXPERIMENTAL_FEATURES.values(), key=lambda item: (item.kind, item.target)))


def experimental_feature_as_dict(feature: ExperimentalFeature) -> dict[str, str | None]:
    """Serialize an experimental feature entry to primitive values."""
    return asdict(feature)


def render_experimental_features_json() -> str:
    """Render all experimental features as JSON."""
    return _render_registry_json(experimental_feature_as_dict(feature) for feature in iter_experimental_features())


def render_experimental_features_table() -> str:
    """Render all experimental features as a plain text table."""
    return _render_registry_table([
        [
            "ID",
            "Kind",
            "Target",
            "Since",
            "Tracking",
        ],
        *[
            [
                feature.id,
                feature.kind,
                feature.target,
                feature.since_version,
                feature.tracking_issue or "-",
            ]
            for feature in iter_experimental_features()
        ],
    ])


def render_experimental_features_markdown(*, include_header: bool = True) -> str:
    """Render all experimental features as Markdown."""
    lines: list[str] = []
    if include_header:
        lines.extend([
            "# Experimental Features",
            "",
            "<!-- Generated by scripts/build_experimental_docs.py. Do not edit manually. -->",
            "",
            "This page lists features that are available but still experimental.",
            "",
        ])
    lines.extend([
        "| ID | Kind | Target | Since | Tracking |",
        "|----|------|--------|-------|----------|",
    ])
    for feature in iter_experimental_features():
        tracking = feature.tracking_issue or "-"
        lines.append(f"| `{feature.id}` | {feature.kind} | `{feature.target}` | {feature.since_version} | {tracking} |")
    lines.extend(("", "## Details", ""))
    for feature in iter_experimental_features():
        lines.extend([
            f"### `{feature.id}`",
            "",
            f"- **Kind:** {feature.kind}",
            f"- **Target:** `{feature.target}`",
            f"- **Since:** {feature.since_version}",
        ])
        if feature.tracking_issue:
            lines.append(f"- **Tracking:** {feature.tracking_issue}")
        lines.extend([
            "",
            feature.message,
            "",
        ])
        if feature.note:
            lines.extend([feature.note, ""])
    return "\n".join(lines).rstrip() + "\n"


def render_experimental_features(format_: ExperimentalFeatureFormat) -> str:
    """Render experimental features in the requested format."""
    if format_ == "json":
        return render_experimental_features_json() + "\n"
    if format_ == "markdown":
        return render_experimental_features_markdown()
    return render_experimental_features_table()


def render_release_note_experimental_features(version: str) -> str:
    """Render release-note text for experimental features introduced in a version."""
    introduced = [item for item in iter_experimental_features() if item.since_version == version]

    lines: list[str] = []
    if introduced:
        lines.extend(["## Experimental Features", ""])
        lines.extend(f"- `{item.target}` is experimental. {item.message}" for item in introduced)
        lines.append("")

    return "\n".join(lines)
