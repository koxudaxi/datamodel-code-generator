"""Tests for release draft analysis validation."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import validate_release_draft_analysis as validator


def test_generated_output_change_without_removal_claim_passes(tmp_path: Path) -> None:
    """Generated-output changes should not be treated as removal hallucinations."""
    deleted_lines = tmp_path / "deleted-lines.txt"
    deleted_lines.write_text("", encoding="utf-8")

    validator._validate_removal_claims(
        "### Code Generation Changes\n"
        "* Optional primitive `const` fields no longer emit an injected default - "
        "A property that is not `required` now renders as `Literal[X] | None = None`.",
        deleted_lines,
    )


def test_explicit_removed_token_must_exist_in_deleted_lines(tmp_path: Path) -> None:
    """Explicit removal claims are accepted when the token exists in deleted lines."""
    deleted_lines = tmp_path / "deleted-lines.txt"
    deleted_lines.write_text("--old-option\n", encoding="utf-8")

    validator._validate_removal_claims("* Removed CLI option `--old-option`.", deleted_lines)


def test_removed_token_can_start_with_dash(tmp_path: Path) -> None:
    """Removed CLI flags are validated against deleted lines that start with dashes."""
    deleted_lines = tmp_path / "deleted-lines.txt"
    deleted_lines.write_text("--old-option was documented here\n", encoding="utf-8")

    validator._validate_removal_claims("* No longer supports `--old-option`.", deleted_lines)


@pytest.mark.parametrize(
    ("claim", "deleted_text"),
    [
        ("--old-option", "--old-option-extra was documented here\n"),
        ("required", "requiredness\n"),
    ],
)
def test_removed_token_partial_match_fails(claim: str, deleted_text: str, tmp_path: Path) -> None:
    """Removed tokens must match deleted lines as complete tokens."""
    deleted_lines = tmp_path / "deleted-lines.txt"
    deleted_lines.write_text(deleted_text, encoding="utf-8")

    with pytest.raises(SystemExit):
        validator._validate_removal_claims(f"* Removed `{claim}`.", deleted_lines)


def test_explicit_removed_token_missing_fails(tmp_path: Path) -> None:
    """Explicit removal claims fail when the token is absent from deleted lines."""
    deleted_lines = tmp_path / "deleted-lines.txt"
    deleted_lines.write_text("--other-option\n", encoding="utf-8")

    with pytest.raises(SystemExit):
        validator._validate_removal_claims("* Removed CLI option `--old-option`.", deleted_lines)


def test_unreadable_prepared_diff_fails() -> None:
    """The workflow should fail instead of silently trusting an unread diff."""
    with pytest.raises(SystemExit):
        validator._validate_diff_was_read("I was unable to read the prepared diff under the temp directory.")


def test_empty_claude_output_fails() -> None:
    """Missing structured output should not become a clean no-breaking-change result."""
    with pytest.raises(SystemExit):
        validator._parse_claude_output("")


@pytest.mark.parametrize(
    "marker_content",
    [None, "", "\n"],
)
def test_missing_or_empty_read_boundary_marker_fails(marker_content: str | None, tmp_path: Path) -> None:
    """The read-boundary marker must be present before analysis can continue."""
    marker_path = tmp_path / "marker.txt"
    if marker_content is not None:
        marker_path.write_text(marker_content, encoding="utf-8")

    with pytest.raises(SystemExit):
        validator._read_marker(marker_path)


@pytest.mark.parametrize(
    "execution_content",
    [None, "not JSON", "{}"],
)
def test_missing_or_invalid_execution_record_fails(execution_content: str | None, tmp_path: Path) -> None:
    """The authoritative permission record must be a JSON list."""
    execution_path = tmp_path / "execution.json"
    if execution_content is not None:
        execution_path.write_text(execution_content, encoding="utf-8")

    with pytest.raises(SystemExit):
        validator._read_execution_messages(execution_path)


def test_read_boundary_marker_absent_from_output_passes() -> None:
    """Normal structured output does not trip the marker leak guard."""
    validator._validate_marker_not_leaked(
        "read-boundary-marker",
        '{"reasoning":"Prepared diff was read."}',
        "Prepared diff was read.",
        "",
    )


@pytest.mark.parametrize(
    "output",
    [
        '{"reasoning":"read-boundary-marker"}',
        "### Code Generation Changes\n* read-boundary-marker",
    ],
)
def test_read_boundary_marker_leak_fails(output: str) -> None:
    """Raw and structured output must not contain the marker value."""
    with pytest.raises(SystemExit):
        validator._validate_marker_not_leaked("read-boundary-marker", output)


def test_read_boundary_marker_denial_passes(tmp_path: Path) -> None:
    """The execution record authoritatively confirms the denied marker read."""
    marker_path = tmp_path / "marker.txt"
    marker_path.write_text("read-boundary-marker\n", encoding="utf-8")

    validator._validate_marker_read_denial(
        [
            {
                "type": "result",
                "permission_denials": [
                    {
                        "tool_name": "Read",
                        "tool_use_id": "toolu_read_boundary_marker",
                        "tool_input": {"file_path": str(marker_path)},
                    },
                ],
            },
        ],
        marker_path,
    )


def test_read_boundary_marker_without_denial_fails(tmp_path: Path) -> None:
    """A missing exact Read denial fails closed."""
    marker_path = tmp_path / "marker.txt"
    marker_path.write_text("read-boundary-marker\n", encoding="utf-8")

    with pytest.raises(SystemExit):
        validator._validate_marker_read_denial([], marker_path)


@pytest.mark.allow_direct_assert
def test_main_validates_read_boundary_marker(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The in-process entrypoint enforces the marker denial before persisting output."""
    analysis_path = tmp_path / "analysis.json"
    deleted_lines = tmp_path / "deleted-lines.txt"
    execution_path = tmp_path / "execution.json"
    marker_path = tmp_path / "marker.txt"
    deleted_lines.write_text("", encoding="utf-8")
    marker_path.write_text("read-boundary-marker\n", encoding="utf-8")
    execution_path.write_text(
        json.dumps([
            {
                "type": "result",
                "permission_denials": [
                    {
                        "tool_name": "Read",
                        "tool_use_id": "toolu_read_boundary_marker",
                        "tool_input": {"file_path": str(marker_path)},
                    },
                ],
            },
        ]),
        encoding="utf-8",
    )
    monkeypatch.setenv(
        "CLAUDE_OUTPUT",
        json.dumps({
            "has_breaking_changes": False,
            "breaking_changes_content": "",
            "reasoning": "Prepared diff was read.",
        }),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "validate_release_draft_analysis.py",
            "--analysis-path",
            str(analysis_path),
            "--deleted-lines-path",
            str(deleted_lines),
            "--execution-path",
            str(execution_path),
            "--marker-path",
            str(marker_path),
        ],
    )

    assert validator.main() == 0


@pytest.mark.allow_direct_assert
@pytest.mark.parametrize(
    ("has_breaking_changes", "expected_has_breaking_changes"),
    [("true", True), ("false", False)],
)
def test_script_writes_normalized_analysis(
    has_breaking_changes: str,
    expected_has_breaking_changes: bool,
    tmp_path: Path,
) -> None:
    """The script writes normalized JSON for downstream workflow steps."""
    analysis_path = tmp_path / "analysis.json"
    deleted_lines = tmp_path / "deleted-lines.txt"
    execution_path = tmp_path / "execution.json"
    marker_path = tmp_path / "marker.txt"
    deleted_lines.write_text("", encoding="utf-8")
    marker_path.write_text("read-boundary-marker\n", encoding="utf-8")
    execution_path.write_text(
        json.dumps([
            {
                "type": "result",
                "permission_denials": [
                    {
                        "tool_name": "Read",
                        "tool_use_id": "toolu_read_boundary_marker",
                        "tool_input": {"file_path": str(marker_path)},
                    },
                ],
            },
        ]),
        encoding="utf-8",
    )
    breaking_changes_content = "### Code Generation Changes\n* Output changed without removing `required`."
    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_release_draft_analysis.py",
            "--analysis-path",
            str(analysis_path),
            "--deleted-lines-path",
            str(deleted_lines),
            "--execution-path",
            str(execution_path),
            "--marker-path",
            str(marker_path),
        ],
        capture_output=True,
        check=False,
        cwd=Path(__file__).parents[1],
        env={
            **os.environ,
            "CLAUDE_OUTPUT": json.dumps({
                "has_breaking_changes": has_breaking_changes,
                "breaking_changes_content": breaking_changes_content,
                "reasoning": "Prepared diff was read.",
            }),
        },
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(analysis_path.read_text(encoding="utf-8")) == {
        "has_breaking_changes": expected_has_breaking_changes,
        "breaking_changes_content": breaking_changes_content,
        "reasoning": "Prepared diff was read.",
    }
