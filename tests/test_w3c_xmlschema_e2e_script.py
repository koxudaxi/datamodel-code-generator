"""Run pinned W3C collision expectations without accepting unrelated generation failures."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import assert_output

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_w3c_xmlschema_e2e.py"


@pytest.mark.parametrize(
    "case", ["expected", "unexpected_success", "unexpected_error", "changed_schema", "wrong_error"]
)
def test_w3c_xmlschema_collision_diagnostics(case: str) -> None:
    """Check source identity, exact error, missing diagnostics and successful imports through real generation."""
    suite = ROOT / "tests/data/parser/xmlschema/w3c_e2e" / case
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(suite), "--progress-interval", "0"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    stdout = re.sub(r"in [0-9.]+s", "in <elapsed>s", result.stdout)
    assert_output(
        f"exit={result.returncode}\n{stdout}{result.stderr}",
        ROOT / "tests/data/payloads/w3c_xmlschema" / f"{case}.txt",
    )
