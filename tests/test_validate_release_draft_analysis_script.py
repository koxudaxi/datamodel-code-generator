"""Tests for release draft analysis validation."""

from __future__ import annotations

import argparse
import json
from typing import TYPE_CHECKING

import pytest

from scripts import validate_release_draft_analysis as validator

if TYPE_CHECKING:
    from pathlib import Path


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


@pytest.mark.allow_direct_assert
def test_script_writes_normalized_analysis(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The script writes normalized JSON for downstream workflow steps."""
    analysis_path = tmp_path / "analysis.json"
    deleted_lines = tmp_path / "deleted-lines.txt"
    deleted_lines.write_text("", encoding="utf-8")
    breaking_changes_content = "### Code Generation Changes\n* Output changed without removing `required`."
    monkeypatch.setenv(
        "CLAUDE_OUTPUT",
        json.dumps({
            "has_breaking_changes": "true",
            "breaking_changes_content": breaking_changes_content,
            "reasoning": "Prepared diff was read.",
        }),
    )

    def parse_args() -> argparse.Namespace:
        return argparse.Namespace(analysis_path=analysis_path, deleted_lines_path=deleted_lines)

    monkeypatch.setattr(validator, "_parse_args", parse_args)

    assert validator.main() == 0
    assert json.loads(analysis_path.read_text(encoding="utf-8")) == {
        "has_breaking_changes": True,
        "breaking_changes_content": breaking_changes_content,
        "reasoning": "Prepared diff was read.",
    }
