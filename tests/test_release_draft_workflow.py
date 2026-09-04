"""Regression tests for release draft workflow permissions."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


@pytest.mark.allow_direct_assert
def test_update_draft_job_uses_exact_least_privilege_permissions() -> None:
    """PR labeling and comments need only pull-request access beside release access."""
    workflow_path = Path(__file__).parents[1] / ".github" / "workflows" / "release-draft.yaml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))

    assert workflow["jobs"]["update-draft"]["permissions"] == {
        "contents": "write",
        "pull-requests": "write",
    }
