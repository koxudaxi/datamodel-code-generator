"""Regression tests for the release draft workflow."""

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


@pytest.mark.allow_direct_assert
def test_analysis_fast_path_only_skips_claude_and_validation() -> None:
    """Trusted analysis and Claude analysis must converge on the same artifact."""
    workflow_path = Path(__file__).parents[1] / ".github" / "workflows" / "release-draft.yaml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["analyze"]["steps"]
    steps_by_name = {step["name"]: step for step in steps}
    prepare_diff_script = steps_by_name["Prepare exact PR diff"]["run"]

    assert "gh api --paginate" in prepare_diff_script
    assert 'previous_path: (if .status == "renamed" then .previous_filename else null end)' in prepare_diff_script
    assert steps_by_name["Prepare release analysis route"]["id"] == "analysis-route"
    assert (
        '--expected-changed-files "${{ github.event.pull_request.changed_files }}"'
        in steps_by_name["Prepare release analysis route"]["run"]
    )
    assert steps_by_name["Run Claude Code Analysis"]["if"] == ("steps.analysis-route.outputs.requires_claude == 'true'")
    assert steps_by_name["Parse Claude output"]["if"] == "steps.analysis-route.outputs.requires_claude == 'true'"
    assert "if" not in steps_by_name["Upload analysis artifact"]
    assert steps_by_name["Upload analysis artifact"]["with"]["path"] == "${{ steps.pr-diff.outputs.analysis_path }}"
