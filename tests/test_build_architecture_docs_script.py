"""Tests for architecture documentation synchronization."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts import build_architecture_docs

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_architecture_docs.py"


def test_build_architecture_docs_check_is_up_to_date() -> None:
    """Check that committed architecture docs match generated source inventory."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_architecture_inventory_contains_core_routes() -> None:
    """Check that the generated inventory includes representative source-derived entries."""
    content = build_architecture_docs.generate_architecture_inventory()

    assert "OpenAPIParser" in content
    assert "JsonSchemaParser" in content
    assert "`pydantic_v2.BaseModel`" in content
    assert "`black`" in content
