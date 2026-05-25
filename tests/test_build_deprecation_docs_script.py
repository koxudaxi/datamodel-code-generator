"""Tests for deprecation documentation generation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_deprecation_docs.py"


def test_build_deprecation_docs_check_is_up_to_date() -> None:
    """Generated deprecation docs are committed."""
    subprocess.run([sys.executable, str(SCRIPT), "--check"], check=True)


def test_build_deprecation_docs_release_notes() -> None:
    """The docs script can print release-note snippets from the registry."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--release-notes", "0.56.0"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "## Deprecations" in result.stdout
    assert "Remote $ref fetching" in result.stdout
