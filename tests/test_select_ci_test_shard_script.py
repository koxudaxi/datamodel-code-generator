"""Tests for CI test shard selection."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "select_ci_test_shard.py"
PAYLOAD_VALIDATION_FILE = "tests/main/test_payload_validation.py"


def _run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def test_recipe_discovers_split_nodeids(tmp_path: Path) -> None:
    """Split-file nodeids are generated from source instead of hand-written lists."""
    recipe_path = tmp_path / "recipe.json"
    _run_script("--write-recipe", str(recipe_path))

    recipe = json.loads(recipe_path.read_text())
    nodeids = {item["nodeid"] for item in recipe["items"]}
    payload_nodeids = {nodeid for nodeid in nodeids if nodeid.startswith(f"{PAYLOAD_VALIDATION_FILE}::")}

    assert PAYLOAD_VALIDATION_FILE not in nodeids
    assert f"{PAYLOAD_VALIDATION_FILE}::test_generated_pydantic_v2_model_accepts_schema_derived_payloads" in nodeids
    assert f"{PAYLOAD_VALIDATION_FILE}::test_payload_validation_cases_cover_discovered_schema_files" in nodeids
    assert len(payload_nodeids) >= 10


def test_recipe_round_trip_selects_disjoint_shards(tmp_path: Path) -> None:
    """Generated recipes can be read back to select shards without duplicate items."""
    recipe_path = tmp_path / "recipe.json"
    _run_script("--write-recipe", str(recipe_path))

    recipe = json.loads(recipe_path.read_text())
    expected_nodeids = {item["nodeid"] for item in recipe["items"]}
    selected_nodeids: list[str] = []

    for shard_index in range(1, 4):
        result = _run_script(str(shard_index), "3", "--recipe", str(recipe_path))
        selected_nodeids.extend(result.stdout.splitlines())

    assert set(selected_nodeids) == expected_nodeids
    assert len(selected_nodeids) == len(expected_nodeids)
