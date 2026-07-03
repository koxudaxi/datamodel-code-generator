"""Tests for llms.txt documentation generation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_llms_txt.py"


def test_build_llms_txt_check_is_up_to_date() -> None:
    """Generated llms.txt files are committed."""
    subprocess.run([sys.executable, str(SCRIPT), "--check"], check=True)
