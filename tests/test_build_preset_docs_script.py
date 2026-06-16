"""Tests for preset documentation generation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import black
import pytest
from packaging import version

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_preset_docs.py"
BLACK_LT_233 = version.parse("23.3.0") > version.parse(black.__version__)


@pytest.mark.skipif(BLACK_LT_233, reason="Installed black doesn't support the Python 3.12 quick-start target")
def test_build_preset_docs_check_is_up_to_date() -> None:
    """Generated preset docs and quick-start examples are committed."""
    subprocess.run([sys.executable, str(SCRIPT), "--check"], check=True)


def test_build_preset_docs_json_format() -> None:
    """The docs script can print preset metadata as JSON."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--format", "json"],
        check=True,
        capture_output=True,
        text=True,
    )

    presets = json.loads(result.stdout)
    assert presets[0]["name"] == "standard-20260617"
    assert presets[0]["requires_target_python_version"] is True
