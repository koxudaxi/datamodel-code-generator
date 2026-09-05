"""Regression tests for the release draft workflow."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from tests.conftest import assert_output


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


def test_maintenance_exclusion_is_wired_before_note_generation() -> None:
    """The native label filter receives the independent routing result before notes are generated."""
    root = Path(__file__).parents[1]
    workflow = yaml.safe_load((root / ".github/workflows/release-draft.yaml").read_text(encoding="utf-8"))
    release_config = yaml.safe_load((root / ".github/release.yml").read_text(encoding="utf-8"))
    steps = workflow["jobs"]["update-draft"]["steps"]
    step_names = [step["name"] for step in steps]
    label_index = step_names.index("Exclude maintenance changes from release notes")
    label_step = steps[label_index]

    assert_output(
        json.dumps(
            {
                "analysis_output": workflow["jobs"]["analyze"]["outputs"],
                "concurrency": workflow["concurrency"],
                "label_before_note_generation": label_index
                < step_names.index("Calculate version and update draft release"),
                "label_condition": label_step["if"],
                "label_request": label_step["run"],
                "release_config": release_config,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        root / "tests/data/expected/release_draft_workflow/maintenance_exclusion.txt",
    )
