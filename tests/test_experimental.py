"""Tests for the central experimental feature registry."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from datamodel_code_generator.experimental import (
    EXPERIMENTAL_FEATURES,
    ExperimentalFeature,
    render_experimental_features,
    render_experimental_features_markdown,
    render_release_note_experimental_features,
)

if TYPE_CHECKING:
    import pytest


def test_experimental_registry_has_stable_required_metadata() -> None:
    """Every registry entry has enough data for docs, CLI output, and release notes."""
    ids = set(EXPERIMENTAL_FEATURES)

    for feature_id, feature in EXPERIMENTAL_FEATURES.items():
        assert feature.id == feature_id
        assert feature.target
        assert feature.message
        assert feature.since_version

    assert len(ids) == len(EXPERIMENTAL_FEATURES)


def test_experimental_json_output_is_machine_readable() -> None:
    """JSON output is suitable for downstream release tooling."""
    payload = json.loads(render_experimental_features("json"))

    assert isinstance(payload, list)
    assert {entry["id"] for entry in payload} == set(EXPERIMENTAL_FEATURES)
    assert all("since_version" in entry for entry in payload)


def test_experimental_table_output_includes_registered_features() -> None:
    """Table output contains registered feature targets."""
    output = render_experimental_features("table")

    assert "ID" in output
    assert "input-format.avro" in output
    assert "--input-file-type xmlschema" in output


def test_experimental_markdown_output_includes_details() -> None:
    """Markdown output contains both summary and detail sections."""
    output = render_experimental_features("markdown")

    assert "| ID | Kind | Target | Since | Tracking |" in output
    assert "## Details" in output
    assert "input-format.asyncapi" in output
    assert "input-format.avro" in output
    assert "input-format.protobuf" in output
    assert "input-format.xmlschema" in output
    assert "formatter.builtin" in output


def test_experimental_markdown_output_can_omit_header() -> None:
    """Generated snippets can omit the page-level heading."""
    output = render_experimental_features_markdown(include_header=False)

    assert not output.startswith("# Experimental Features")
    assert output.startswith("| ID | Kind | Target | Since | Tracking |")


def test_release_note_output_filters_by_version() -> None:
    """Release-note snippets include entries introduced in the requested version."""
    output = render_release_note_experimental_features("0.59.0")

    assert "## Experimental Features" in output
    assert "--input-file-type asyncapi" in output
    assert "--input-file-type avro" in output
    assert "--input-file-type protobuf" in output
    assert "--input-file-type xmlschema" in output
    assert "--formatters builtin" in output


def test_experimental_markdown_includes_tracking_issue(monkeypatch: pytest.MonkeyPatch) -> None:
    """Markdown details include optional tracking metadata when it is registered."""
    monkeypatch.setitem(
        EXPERIMENTAL_FEATURES,
        "test.tracked-feature",
        ExperimentalFeature(
            id="test.tracked-feature",
            kind="behavior",
            target="Tracked behavior",
            message="Tracked behavior is experimental.",
            since_version="9.0.0",
            tracking_issue="https://github.com/koxudaxi/datamodel-code-generator/issues/9999",
        ),
    )

    output = render_experimental_features_markdown()

    assert "test.tracked-feature" in output
    assert "https://github.com/koxudaxi/datamodel-code-generator/issues/9999" in output


def test_release_note_output_omits_unmatched_versions() -> None:
    """Release-note snippets are empty when no experimental feature was introduced."""
    assert not render_release_note_experimental_features("9.9.9")
